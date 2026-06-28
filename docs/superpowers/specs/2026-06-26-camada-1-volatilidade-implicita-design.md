# Camada 1 — Volatilidade Implícita Real (design)

> Escopo completo da Camada 1 do `docs/PLANO_IMPLEMENTACAO_MELHORIAS.md` (Partes 1.1, 1.2, 1.3). Próxima camada depois da Camada 0 (fundação), já mergeada na `main`.

## Contexto / estado atual

O motor já extrai IV implícita do prêmio de tela via Newton-Raphson (`implied_volatility` em [backend/domain/greeks.py:83](../../../backend/domain/greeks.py#L83)) e usa o resultado (`iv_mercado`) para recalcular os Greeks em [backend/services/core_engine.py:245](../../../backend/services/core_engine.py#L245). Isso cobre parte da Parte 1.1. O que falta:

- `iv_hist` está rotulado como "IV" em todo o código/DB/frontend, mas é volatilidade **histórica** (HV 20d) — erro conceitual a corrigir.
- Não há validação de no-arbitrage (prêmio < valor intrínseco) na extração de IV implícita.
- Não há fallback chain documentada quando a IV implícita de tela não está disponível.
- Não há histórico de IV nem IV Rank — não dá pra saber se a vol está "cara" ou "barata".
- Não há filtro de emissão baseado em volatilidade.

## 1. Rename `iv_hist` → `hv_20d`

Toca DB, backend e frontend. Decisão: rename direto (sem coluna paralela), aplicado antes do deploy — mesmo padrão das migrações 002/003 pendentes (ver [[melhorias-motor-sinais-v3]]).

**Migration `supabase/migrations/004_rename_iv_hist.sql`:**
```sql
ALTER TABLE sinais RENAME COLUMN iv_hist TO hv_20d;
ALTER TABLE sinais ADD COLUMN iv_impl numeric;
ALTER TABLE sinais ADD COLUMN iv_source text;
```

**Backend (troca de chave `iv_hist` → `hv_20d`):**
- `backend/services/core_engine.py` (`_montar_estrutura_opcao`, `_montar_sinal`)
- `backend/services/signal_service.py:97`
- `backend/services/outcome_service.py:21`
- `backend/domain/outcome.py:33`
- `backend/services/telegram_service.py:94`

`iv_mercado` continua existindo como está; passa a ser preenchido a partir do resultado de `resolver_iv` (ver seção 2) quando a fonte é `tela` ou `strikes_vizinhos`.

**Frontend:**
- `src/types/signals.ts`: campo `iv_hist` → `hv_20d`.
- `src/components/SignalCard.tsx:137`: label "IV Hist" → "HV 20d".

## 2. Fallback chain de IV (`backend/domain/options_math.py`)

Nova função:

```python
def resolver_iv(preco_tela: float | None, S: float, K: float, T: float, tipo: str,
                 hv_20d: float, ivs_strikes_vizinhos: list[float]) -> tuple[float, str]:
    """Retorna (iv, fonte). fonte em {'tela', 'strikes_vizinhos', 'hv_proxy', 'default'}."""
```

Ordem da chain (primeira que produzir um valor válido vence):

1. **`tela`** — `implied_volatility(S, K, T, preco_tela, tipo, sigma_init=hv_20d)`, só aceito se `0.05 <= iv <= 3.0` **e** `preco_tela` for maior que o valor intrínseco da opção (checagem de no-arbitrage nova — hoje o Newton-Raphson clampa em vez de rejeitar).
2. **`strikes_vizinhos`** — mediana das IVs implícitas (mesmo cálculo acima) dos strikes líquidos vizinhos do mesmo vencimento, já disponíveis na chain buscada por `get_real_options_from_opcoes_net`/`_fetch_chain`.
3. **`hv_proxy`** — `hv_20d × 1.1`.
4. **`default`** — `0.40`.

`iv_source` é persistido no sinal (`s["iv_source"]`) para auditoria — todo sinal carrega a proveniência da sua IV.

## 3. Histórico de IV e IV Rank (Parte 1.2)

**Migration `supabase/migrations/005_iv_history.sql`:**
```sql
CREATE TABLE iv_history (
    id bigserial PRIMARY KEY,
    ticker text NOT NULL,
    data date NOT NULL,
    iv_atm numeric,
    hv_20d numeric,
    iv_premium numeric,
    fonte text,
    created_at timestamptz DEFAULT now(),
    UNIQUE (ticker, data)
);
```

**Novo serviço `backend/services/iv_history_service.py`:**
- `coletar_iv_diaria()`: itera o universo líquido (`carregar_tickers_b3()` — mesmo universo do scan principal, decisão tomada para manter consistência com o que gera sinais).
- Para cada ticker: busca a chain (`_fetch_chain`, já cacheada), acha a opção ATM (strike mais próximo do spot, vencimento de `mes_vencimento_ideal()`), calcula `iv_atm` via `resolver_iv` (fonte `tela` apenas — sem dado real, pula o ticker no dia).
- Calcula `hv_20d` (reaproveita `estimar_iv_historica`) e `iv_premium = iv_atm / hv_20d`.
- Persiste em `iv_history` via upsert (`ticker, data`).
- Falha de fetch por ticker é logada e **não** derruba o job (mesmo padrão de resiliência do scan principal).

**Job no `backend/services/scheduler.py`:**
```python
scheduler.add_job(
    coletar_iv_diaria,
    trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=0, timezone="America/Sao_Paulo"),
    id="iv_history_job",
    name="Coleta diária de IV ATM (pós-fechamento)",
    replace_existing=True,
    max_instances=1,
)
```
Roda pós-fechamento (18h BRT) para evitar qualquer look-ahead — mesma diligência aplicada na Camada 0 para os pivots.

**`iv_rank(ticker)` (em `iv_history_service.py`):**
- Percentil da `iv_atm` mais recente dentro dos últimos 252 dias úteis de `iv_history` (ou todo o histórico disponível).
- Com menos de 60 du de histórico: usa o proxy `iv_premium` direto (>1.3 = vol cara), com flag `iv_rank_confiavel=False` no retorno.

## 4. Filtro de volatilidade na emissão (Parte 1.3) — shadow mode

Novo parâmetro `CONFIG['iv_filter_mode']` (`backend/core/config.py`), default `'shadow'`. Valores: `'shadow'` | `'ativo'`.

Em `backend/domain/scoring.py`, nova função `avaliar_filtro_iv(iv_rank, iv_premium, iv_rank_confiavel, score_tecnico)` que retorna a decisão segundo a tabela do plano:

| Condição | Decisão |
|---|---|
| IV Rank < 50 (ou `iv_premium` < 1.2) | `normal` |
| IV Rank 50–75 (ou premium 1.2–1.5) | `exige_score_7` |
| IV Rank > 75 (ou premium > 1.5) | `bloquear` |

- Em modo `shadow`: a decisão e os campos (`iv_rank`, `iv_premium`, `iv_filter_decisao`) são sempre anexados ao sinal e logados (`logger.info` quando a decisão seria `exige_score_7` ou `bloquear`), mas **nunca** impedem a emissão.
- Em modo `ativo`: a decisão é aplicada de fato em `_montar_sinal` (core_engine.py) — `bloquear` descarta o sinal, `exige_score_7` eleva o threshold mínimo.
- Migração de `shadow` → `ativo` é uma mudança de config, não de código — só deve ocorrer depois que `iv_history` acumular histórico suficiente (≥60 du) para a maioria do universo.

## Testes

- `resolver_iv`: cada nível da chain isoladamente (mock de `implied_volatility`), incluindo rejeição por no-arbitrage (prêmio < intrínseco).
- `iv_history_service.coletar_iv_diaria`: chain mockada, shape da linha persistida, ticker com fetch falho é pulado sem exceção.
- `iv_rank`: percentil correto com histórico ≥60 du; fallback para proxy com histórico curto, com `iv_rank_confiavel=False`.
- `avaliar_filtro_iv`: as três faixas da tabela, incluindo o caso `iv_rank_confiavel=False` usando o proxy.
- Shadow mode: sinal carrega os campos e o log é emitido, mas o sinal não é descartado mesmo quando a decisão seria `bloquear`.
- Modo `ativo` (teste separado, `CONFIG['iv_filter_mode']='ativo'`): sinal é de fato descartado/threshold elevado.
- Guarda anti-look-ahead: job só roda pós-fechamento; nenhuma leitura de `iv_history` do dia corrente antes do fechamento.

## Pendências manuais (antes do deploy)

- Aplicar migrações `004` e `005` no Supabase (mesmo fluxo das pendentes `002`/`003`).
- Confirmar que `iv_filter_mode` permanece `'shadow'` até `iv_history` ter ≥60 du de cobertura para o universo líquido.

## Fora de escopo (fica para depois)

- Página `/signals/sobre` e dashboard de transparência (Camada 6).
- Recalibração de pesos via `iv_rank` como feature de modelo (Camada 5.3, gateado por N≥100).

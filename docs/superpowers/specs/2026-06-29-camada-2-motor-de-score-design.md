# Camada 2 — Redesenho do Motor de Score — Design

**Status:** Aprovado para planejamento
**Roadmap:** `docs/PLANO_IMPLEMENTACAO_MELHORIAS.md`, seção "CAMADA 2 — Redesenho do Motor de Score"
**Pré-requisito:** Camada 1 (volatilidade implícita) concluída e em produção.

## Problema

O motor de score clássico (`backend/services/core_engine.py::_avaliar_gatilhos`) tem três falhas estruturais:

1. **Gatilhos correlacionados contados como independentes** — numa queda de 3 dias, vários gatilhos do mesmo tipo de evidência (osciladores, p.ex.) disparam juntos, inflando o score sem informação nova.
2. **Mistura de regimes** — sinais de reversão (RSI sobrevenda, divergência) e de continuação (EMA9>EMA21, canal de tendência) são tratados com os mesmos parâmetros de estrutura de opção (OTM, DTE, alvos, stop), embora sejam trades de natureza diferente.
3. **Assimetria 11×9 não documentada** — o lado de alta tem 11 gatilhos (máx. 23 pts), o de baixa tem 9 (máx. 21 pts), sem registro formal de que isso é intencional.

## Achado de base: mapeamento canônico dos gatilhos

Hoje os 20 gatilhos vivem como blocos `if/append/+=` soltos em `_avaliar_gatilhos`, identificados apenas por texto livre (ex.: `"📈 RSI sobrevenda: 28.4"`), sem ID nem metadado de família. `docs/ESTRATEGIAS_OPCOES_B3.md` já documenta os 20 gatilhos com IDs canônicos (G1-G11 alta, B1-B9 baixa) e pontuação — confirmado por correspondência 1:1 com o código (somas G=23, B=21 batem exatamente).

Mapeamento gatilho → família (usado em toda a camada):

| Família | Gatilhos de alta | Gatilhos de baixa | Cap sugerido |
|---|---|---|---|
| OSCILADOR | G1(+3) Estocástico, G2(+2) RSI, G6(+2) MACD zero | B1(+3), B2(+2), B6(+2) | ≤4 |
| TENDENCIA | G4(+2) EMA9×EMA21, G7(+2) fundos ascendentes, G11(+2) canal | B4(+2), B5(+2), B9(+2) | ≤4 |
| ESTRUTURA | G3(+2) suporte 20D, G8(+1) Bollinger inferior | B3(+2) resistência 20D | ≤3 |
| DIVERGENCIA | G9(+3) divergência RSI | B7(+3) | ≤3 |
| LIQUIDEZ | G5(+1) volume, G10(+3) zona de demanda | B8(+3) zona de oferta | ≤4 |

Caps são valores iniciais, calibráveis em `CONFIG`, não verdades fixas (mesma disciplina da Camada 1: hipótese a validar na Camada 5).

## Princípio de design: campos aditivos, shadow mode por padrão

Todas as mudanças de comportamento desta camada (regra de consenso por família, parâmetros diferenciados por setup) entram em **shadow mode**: persistidas como campos informativos no sinal, sem alterar a decisão real de emissão ou os parâmetros reais de estrutura/precificação da opção. Isso replica a disciplina já estabelecida na Camada 1 (`iv_filter_mode`) e evita que hipóteses não validadas (Camada 5) afetem produção.

O campo existente `gatilhos: list[str]` (texto livre, consumido por Telegram e frontend) **não muda de formato** — preserva compatibilidade total. Toda informação estruturada nova (IDs, famílias, setup) entra em campos adicionais.

---

## Parte 2.1 — Famílias de gatilhos com teto de contribuição

**Arquivos:** `backend/domain/scoring.py`, `backend/services/core_engine.py`, `backend/core/config.py`

- Registro `GATILHOS: dict[str, dict]` em `scoring.py` — `{"G1": {"familia": "OSCILADOR", "pontos": 3}, ...}` para os 20 IDs.
- `_avaliar_gatilhos` passa a anotar cada disparo com seu ID (mantendo `sinais_alta`/`sinais_baixa` em texto livre como hoje, sem mudança de formato), retornando também `gatilhos_ids_alta`/`gatilhos_ids_baixa: list[str]`.
- Nova função `calcular_familias(gatilhos_ids: list[str]) -> dict` em `scoring.py`: aplica os caps por família e retorna `{"score_capped": int, "familias_ativas": int, "breakdown": {familia: pontos_capped}}`.
- `analisar_ativo` calcula `familias_ativas` e persiste no sinal. Decisão de consenso shadow: `CONFIG["consenso_filter_mode"]="shadow"` (padrão) — calcula `consenso_decisao` ("passaria"/"bloquearia", regra `score_tecnico>=5 and familias_ativas>=2`) mas a emissão real continua decidida só por `score_tecnico>=MIN_SCORE`. Modo `"ativo"` (futuro) aplicaria o bloqueio de fato.
- Campos novos no sinal: `gatilhos_ids` (união alta+baixa do lado vencedor), `familias_ativas`, `score_familias_capped`, `consenso_decisao`.

## Parte 2.2 — Separação Setup Reversão × Continuação (shadow)

**Arquivos:** `backend/domain/scoring.py`, `backend/services/core_engine.py`, `backend/core/config.py`

- Função `classificar_setup(breakdown: dict) -> str` em `scoring.py`: soma pontos das famílias REVERSAO-like (OSCILADOR+DIVERGENCIA+ESTRUTURA) vs. TENDENCIA; retorna `"REVERSAO"`, `"CONTINUACAO"` ou `"HIBRIDO"` (empate).
- Função `parametros_setup_shadow(setup: str) -> dict` em `scoring.py`: retorna os parâmetros que *seriam* usados por setup (tabela do plano — OTM×0.7/×1.0, DTE 10-25/5-20, alvo2 +150%/+250%, stop -35%/-43%), sem aplicá-los.
- `analisar_ativo`/`_montar_sinal` persistem `setup` e `setup_params_shadow` (dict) no sinal. A estrutura real da opção (`_montar_estrutura_opcao`) **não é alterada** — continua usando os parâmetros únicos atuais.
- `CONFIG["setup_filter_mode"]="shadow"` (padrão, simetria com `iv_filter_mode`/`consenso_filter_mode` — não há modo "ativo" implementado nesta camada; é só o flag de disciplina para a futura promoção).

## Parte 2.3 — Assimetria CALL/PUT documentada

**Arquivos:** `docs/ESTRATEGIAS_OPCOES_B3.md`

- Sem mudança de código. Nova seção no documento registrando a assimetria 11×9 (23×21 pts) como decisão atual, citando os gatilhos espelho que faltam do lado baixista (mirror de G5/volume e G8/Bollinger superior) e remetendo sua eventual implementação para uma iteração futura com ciclo de validação próprio.

## Parte 2.4 — Telemetria por gatilho

**Arquivos:** `backend/services/outcome_service.py`, nova migração `006`

- Nova tabela `trigger_outcomes`:
  ```sql
  CREATE TABLE trigger_outcomes (
      id               BIGSERIAL PRIMARY KEY,
      signal_id        BIGINT NOT NULL,
      gatilho_id       TEXT NOT NULL,
      familia          TEXT,
      pontos           INTEGER,
      setup            TEXT,
      resultado_final  TEXT,
      retorno_pct      NUMERIC,
      dias_ate_resolucao INTEGER,
      created_at       TIMESTAMPTZ DEFAULT now()
  );
  CREATE INDEX idx_trigger_outcomes_gatilho ON trigger_outcomes (gatilho_id, resultado_final);
  ```
- `outcome_service.avaliar_sinais`, ao resolver um sinal (ganho/perda/aberto via Black-Scholes — mecanismo já existente, reusado sem mudança), passa a explodir o resultado: para cada `gatilho_id` em `sinal["gatilhos_ids"]`, insere uma linha em `trigger_outcomes` espelhando `resultado_final`/`retorno_pct`/`dias_ate_resolucao` do sinal pai, junto com `familia`/`pontos` (via lookup no registro `GATILHOS`) e `setup` (do sinal).
- Sinais antigos sem `gatilhos_ids` (anteriores a esta camada) são pulados nessa explosão — sem backfill retroativo (não há como saber quais gatilhos dispararam sem reprocessar OHLCV histórico, fora de escopo).

## Schema — Migração 006

```sql
ALTER TABLE signals
  ADD COLUMN IF NOT EXISTS gatilhos_ids          TEXT[],
  ADD COLUMN IF NOT EXISTS familias_ativas        INTEGER,
  ADD COLUMN IF NOT EXISTS score_familias_capped  INTEGER,
  ADD COLUMN IF NOT EXISTS consenso_decisao       TEXT,
  ADD COLUMN IF NOT EXISTS setup                  TEXT,
  ADD COLUMN IF NOT EXISTS setup_params_shadow     JSONB;

CREATE TABLE IF NOT EXISTS trigger_outcomes (
    id               BIGSERIAL PRIMARY KEY,
    signal_id        BIGINT NOT NULL,
    gatilho_id       TEXT NOT NULL,
    familia          TEXT,
    pontos           INTEGER,
    setup            TEXT,
    resultado_final  TEXT,
    retorno_pct      NUMERIC,
    dias_ate_resolucao INTEGER,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_trigger_outcomes_gatilho
  ON trigger_outcomes (gatilho_id, resultado_final);
```

Aplicação manual no Supabase Dashboard após merge, mesma disciplina das migrações anteriores (004/005).

## Testes

- `tests/test_scoring.py`: registro `GATILHOS` (20 entradas, soma de pontos por lado = 23/21), `calcular_familias` (caps aplicados corretamente, `familias_ativas` contando famílias distintas), `classificar_setup` (REVERSAO/CONTINUACAO/HIBRIDO em casos de fronteira de empate), `parametros_setup_shadow` (valores da tabela do plano).
- `tests/test_core_engine.py`: `_avaliar_gatilhos` retorna `gatilhos_ids_alta`/`gatilhos_ids_baixa` corretos para um df fixture conhecido; `analisar_ativo` persiste `familias_ativas`/`consenso_decisao`/`setup`/`setup_params_shadow` no sinal sem alterar `score`/`estrutura` reais (teste de regressão shadow, mesmo padrão da Camada 1).
- `tests/test_outcome_service.py`: ao resolver um sinal com `gatilhos_ids` populado, gera N linhas em `trigger_outcomes` (uma por ID) com os campos espelhados corretamente; sinal sem `gatilhos_ids` (legado) não gera linhas e não derruba o job.

## Critério de aceite da camada

Todo sinal novo carrega `gatilhos_ids`, `familias_ativas`, `score_familias_capped`, `consenso_decisao`, `setup`, `setup_params_shadow` — todos em modo shadow, sem alterar nenhuma decisão de emissão ou parâmetro de estrutura de opção real. `docs/ESTRATEGIAS_OPCOES_B3.md` documenta a assimetria 11×9. `trigger_outcomes` grava granularidade por gatilho para sinais resolvidos após o deploy desta camada. Suíte pytest completa passando (exceto a falha pré-existente e não relacionada já documentada).

## Pendências manuais pós-merge

- Aplicar migração `006` no Supabase Dashboard.
- Nenhuma promoção de shadow→ativo nesta camada (`consenso_filter_mode`/`setup_filter_mode` permanecem `"shadow"` até validação na Camada 5).

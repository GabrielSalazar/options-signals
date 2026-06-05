# Design — Carregador dinâmico de tickers da B3 (universo líquido)

**Data:** 2026-06-04
**Origem:** `docs/guia_integracao.html` (guia escrito para a arquitetura antiga `scanner_opcoes_b3_v3.py`), adaptado à arquitetura refatorada (junho/2026) `backend/{api,services,domain,core}`.

---

## 1. Contexto e objetivo

O guia propõe substituir uma lista estática de tickers por **toda a B3 filtrada por liquidez**, com um pré-filtro de volume barato e um limite `top_n`. Parte dessa visão **já existe** na base atual; este trabalho entrega a peça que falta e adiciona a API oficial da B3 como fonte redundante.

### O que já existe (não refazer)

| Componente | Local | Faz |
|---|---|---|
| `ATIVOS_B3` | [`backend/core/config.py:52`](../../../backend/core/config.py) | dict curado de ~53 tickers `{TICKER.SA: nome}` |
| `fetch_all_b3_tickers()` | [`backend/services/data_providers.py:51`](../../../backend/services/data_providers.py) | universo completo via **brapi `/available`** (símbolos negociáveis), cache 24h |
| `get_all_b3_assets()` | [`backend/core/config.py:127`](../../../backend/core/config.py) | merge curados + brapi → dict |
| Filtro de volume **tardio** | [`backend/services/core_engine.py:82`](../../../backend/services/core_engine.py) | rejeita `vol_med < 1M` **por quantidade de ações**, só após baixar 6m de OHLCV + indicadores + chain |

### A lacuna

Hoje `run_scan(all_b3=True)` faz o trabalho caro (download 6m + indicadores + chain de opções) para **~400 nomes**, mesmo que só ~80–120 sejam líquidos. Falta um **pré-filtro barato** que corte ~400 → ~150 *antes* da análise pesada, mais `top_n`.

---

## 2. Escopo (decisões travadas)

1. **Entregar:** pré-filtro de volume + `top_n`, adaptados à arquitetura atual, **e** adicionar a API oficial da B3 como segunda fonte (redundância).
2. **Métrica de liquidez:** **volume financeiro em R$** (preço médio × volume médio de ações, ~10 dias). O check tardio em `core_engine.py:82` mantém a **lógica** (quantidade de ações; só a chave é renomeada para `min_volume_acoes` — A5) — o pré-filtro é um corte grosseiro independente, não substitui o critério fino.
3. **Integração:** o universo líquido **vira o padrão do scan agendado** (a cada 30 min). Não só o caminho opt-in.
4. **Fonte B3:** colher **raízes + nomes de empresa** via API B3, **expandir sufixos `3`/`4`/`11`** como candidatos, e deixar o pré-filtro de volume remover o ruído (tickers que não negociam voltam vazios do yfinance). Bônus: nomes de empresa reais para tickers não-curados.
5. **Curados sempre incluídos:** `ATIVOS_B3` passa direto pelo filtro (precedência + fallback), de-riscando o limiar e garantindo que o scan nunca perca nomes bons conhecidos.
6. **Defaults:** `min_volume_rs = 5_000_000` (R$5M/dia), `ticker_top_n = 150`, `ticker_cache_segundos = 3600`.

### Pontos expostos incluídos nesta entrega (A1–A5)

A revisão de impacto (2026-06-04) identificou pontos que a mudança expõe. Decidido incluí-los **agora** (detalhe em §9):

- **A1** — corrigir violação de camadas: `config` (core) importa `services`. Mover orquestração para `ticker_loader`.
- **A2** — carga de APIs externas a ~3x (opcoes.net.br + yfinance): workers configuráveis + caches.
- **A3** — Telegram sem throttle e bloqueando o loop de scan: enviar fora do hot-loop, com throttle.
- **A4** — orçamento de tempo vs. cadência de 30min: logar duração, alavancas `top_n`/workers.
- **A5** — renomear `min_volume_diario` → `min_volume_acoes` (desambiguar do `min_volume_rs`).

### Fora de escopo (YAGNI)

- **B1 (follow-up):** decompor a função-deus `analisar_ativo` (~330 linhas) — PR separado, com TDD.
- Não alterar a **lógica** do filtro de volume de `core_engine.py:82` (só renomear a chave — A5).
- Não fazer chamada de detalhe por empresa na B3 (N+1, ~400 reqs).
- Não criar endpoint novo para o universo "completo sem filtro" (acessível só via parâmetro de função, p/ debug).
- Não tocar no frontend (confirmado: `src/` só chama `/signals/scan/all` curado).

---

## 3. Arquitetura e componentes

Segue a camada existente: `routers → services → domain/core`. Orquestração é responsabilidade de *serviço*; fetch bruto fica em `data_providers`.

```
backend/
  services/
    data_providers.py    (+2 funções: fetch B3 oficial, filtro de volume)
    ticker_loader.py     (NOVO — orquestra universo + get_all_b3_assets + cache; A1)
    signal_service.py    (run_scan: universo líquido padrão; Telegram fora do hot-loop A3; workers config A2)
    telegram_service.py  (helper de envio em lote com throttle; A3)
  core/
    config.py            (só constantes/helpers; NÃO importa services A1; +knobs; rename A5)
  api/routers/
    scan.py              (/scan/all-b3 passa a varrer o universo líquido)
    signals.py           (/watchlist importa do ticker_loader, não do config; A1)
```

### 3.1 `data_providers.fetch_b3_official_tickers() -> dict[str, str]`

- **O que faz:** itera as páginas de empresas da API oficial da B3, extrai a raiz (`issuingCompany`) e o nome (`tradingName`/`companyName`), e **expande cada raiz de 4 letras** em candidatos `{raiz}3`, `{raiz}4`, `{raiz}11`. Retorna `{ticker_base: nome_empresa}`.
- **Endpoint:** `GET https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy/CompanyCall/GetInitialCompanies/{b64}`, onde `b64 = base64(json({"language":"pt-br","pageNumber":N,"pageSize":120}))`. Resposta traz `page.totalPages` → paginar. Delay 0.3s/página. Headers de browser (`User-Agent`, `Accept: application/json`) para evitar 403.
- **Dependências:** `requests`, `cache` (24h, chave `b3_official_tickers`).
- **Erros:** qualquer falha → loga warning e retorna `{}` (degradação graciosa). Raízes não-alfabéticas de 4 chars são ignoradas.

### 3.2 `data_providers.filtrar_por_volume(tickers, min_volume_rs, batch_size=20, delay_s=1.0, period="10d") -> dict[str, float]`

- **O que faz:** baixa OHLCV de `period` via `yfinance` em lotes de `batch_size`, calcula o **volume financeiro médio diário** `média(Close × Volume)` por ticker e retorna `{ticker.SA: volume_rs}` **apenas** para os que atingem `min_volume_rs`.
- **Robustez:** tickers sem dados são ignorados; erro em um lote → loga e pula o lote; delay `delay_s` entre lotes (gentileza de rate limit).
- **Dependências:** `yfinance`. (Não usa cache próprio — o resultado é cacheado uma camada acima, no `ticker_loader`.)

### 3.3 `ticker_loader.carregar_tickers_b3(...) -> dict[str, str]` (NOVO)

```python
def carregar_tickers_b3(
    min_volume_rs: float | None = None,    # None → CONFIG["min_volume_rs"]
    top_n: int | None = None,              # None → CONFIG["ticker_top_n"] (que pode ser None = sem limite)
    usar_api_b3: bool = True,
    usar_brapi: bool = True,
    usar_lista_curada: bool = True,
    filtrar_volume: bool = True,
    cache_segundos: int | None = None,     # None → CONFIG["ticker_cache_segundos"]
    force_refresh: bool = False,
) -> dict[str, str]:                       # {TICKER.SA: nome}, ordenado (curados primeiro)
```

**Passos:**
1. Resolve defaults a partir de `CONFIG`.
2. **Cache em processo** (dict de módulo `_cache`, chaveado pelos parâmetros): se fresco (`< cache_segundos`) e não `force_refresh` → retorna.
3. **Monta universo bruto** `{base: nome}`:
   - curados `ATIVOS_B3` (se `usar_lista_curada`) — carregam nome, têm precedência;
   - `fetch_b3_official_tickers()` (se `usar_api_b3`) — não sobrescreve nome de curado;
   - `fetch_all_b3_tickers()` (se `usar_brapi`) — nome = base se inédito.
4. Normaliza (UPPER, base sem `.SA`) e dedup.
5. **Filtro de volume** (se `filtrar_volume`): aplica `filtrar_por_volume()` apenas aos **não-curados**; curados entram sempre.
6. **`top_n`:** ordem = curados (na ordem de `ATIVOS_B3`) + não-curados aprovados (por volume R$ desc); trunca em `top_n` (se `None`, sem limite).
7. Cacheia e retorna `{f"{base}.SA": nome}` (dict ordenado → consumidores iteram curados primeiro).

### 3.4 Integração

- **A1 — `get_all_b3_assets()` sai do `config` (core) para o `ticker_loader` (service).** O `config.py` deixa de importar `services` (fim da violação de camadas). A função vira um *thin wrapper* sobre `carregar_tickers_b3()` no loader.
  - [`signals.py`](../../../backend/api/routers/signals.py) `/watchlist` passa a importar `get_all_b3_assets` de `ticker_loader` (não de `config`). Reflete o universo líquido (cache-first; cold cache paga o pré-filtro uma vez).
  - [`signal_service.py`](../../../backend/services/signal_service.py) importa o universo do `ticker_loader`, não mais de `config`.
- **`signal_service.run_scan(verbose=False, universe="liquido")`** — assinatura muda de `all_b3: bool` para `universe: str` (`"liquido"` | `"curado"`):
  - `"liquido"` (default) → `carregar_tickers_b3()` (filtrado + top_n);
  - `"curado"` → `ATIVOS_B3` (comportamento legado).
  - **A2:** o `ThreadPoolExecutor` usa `CONFIG["scan_max_workers"]` (default 8) em vez de 10 hardcoded.
  - **A3:** o loop de coleta **não** envia Telegram inline; acumula sinais e, ao final, chama `telegram_service.notificar_lote(sinais)` (envio com throttle).
- **Scheduler** ([`scheduler.py:20`](../../../backend/services/scheduler.py)) → `run_scan()` usa o default `"liquido"`. ✅
- **Endpoints** ([`scan.py`](../../../backend/api/routers/scan.py)):
  - `/signals/scan/all` → `run_scan(universe="curado")` (inalterado);
  - `/signals/scan/all-b3` → `run_scan(universe="liquido")` (**novo significado:** universo líquido pré-filtrado ~150, antes era ~400 cru).

---

## 4. Fluxo de dados

```
scheduler (30min)  ─┐
/scan/all-b3       ─┼─► run_scan(universe="liquido")
get_all_b3_assets  ─┘            │
                                 ▼
                      carregar_tickers_b3()
                                 │ cache em processo (TTL 3600s)?  → hit, retorna
                                 ▼ miss
        ┌──────────────┬─────────────────┬──────────────────┐
        ▼              ▼                 ▼                  
   ATIVOS_B3   fetch_b3_official   fetch_all_b3_tickers     
   (curados)   (raízes→3/4/11)     (brapi /available)       
        └──────────────┴─────────────────┘
                                 ▼ união + dedup
                       filtrar_por_volume (R$, yfinance, lotes de 20)
                                 │ curados sempre passam
                                 ▼ ordena (curados, depois R$ desc) + top_n
                       {TICKER.SA: nome}  ──► loop de análise (analisar_ativo)
```

---

## 5. Configuração (campos em `CONFIG`)

```python
# Carregador de tickers
"min_volume_rs":         5_000_000,   # piso de volume financeiro diário (R$) p/ pré-filtro
"ticker_top_n":          150,         # nº máx de tickers no universo líquido (None = sem limite)
"ticker_cache_segundos": 3600,        # TTL do cache da lista líquida (em processo)
# Pontos expostos (A2/A3)
"scan_max_workers":      8,           # workers do scan completo (era 10 hardcoded) — alavanca anti rate-limit
"telegram_throttle_s":   0.5,         # delay entre envios de Telegram (evita 429 com muitos sinais)
```

**A5 — rename:** `min_volume_diario` → `min_volume_acoes` (1M, quantidade de ações, usado por `core_engine:82`). A **lógica** não muda; só o nome, para desambiguar de `min_volume_rs`. Atualizar: `config.py`, `core_engine.py:82`, `tests/test_config.py:27` (`REQUIRED_KEYS`).

---

## 6. Tratamento de erros / fallback

| Cenário | Comportamento |
|---|---|
| API B3 fora do ar | `fetch_b3_official_tickers()` → `{}`; segue com brapi + curados |
| brapi fora do ar | `fetch_all_b3_tickers()` → `[]`; segue com B3 + curados |
| Ambas fora do ar | universo = só curados (`ATIVOS_B3`) — scan nunca para |
| yfinance falha num lote | loga, pula o lote; demais lotes seguem |
| Redis indisponível | cache em processo cobre o reuso entre scans (independe do Redis) |
| Cold cache no 1º scan | paga ~45–90s do pré-filtro uma vez; `max_instances=1` evita sobreposição |

---

## 7. Testes (pytest, sem rede)

**`tests/test_ticker_loader.py` (novo):**
- união + dedup das 3 fontes; nomes de curados preservados;
- curados sempre incluídos mesmo se o filtro de volume não os retorna;
- ordenação `top_n` (curados primeiro, depois R$ desc) e truncamento;
- `top_n=None` → sem limite;
- reuso de cache (2ª chamada dentro do TTL não refaz fetch — assert fetch chamado 1×);
- `force_refresh` ignora cache;
- degradação: B3 cai / brapi cai / ambas caem.

**`tests/test_data_providers.py` (novo ou estendido):**
- `fetch_b3_official_tickers`: parsing de páginas (mock `requests`), expansão de sufixos 3/4/11, captura de nomes;
- `fetch_b3_official_tickers`: erro → `{}`;
- `filtrar_por_volume`: cálculo financeiro R$ (mock `yf.download`), aplicação do limiar, lotes;
- `filtrar_por_volume`: ignora tickers sem dados.

**Cobertura dos pontos expostos:**
- `test_config.py`: `REQUIRED_KEYS` passa a exigir `min_volume_acoes` (não `min_volume_diario`) + `scan_max_workers` (A5/A2).
- `test_ticker_loader.py`: `get_all_b3_assets` (wrapper) vive no loader e delega (A1).
- `test_signal_service.py` (novo ou estendido): `run_scan(universe=...)` seleciona o universo certo (mock loader); Telegram é chamado **uma vez ao final** via `notificar_lote`, não dentro do loop (A3) — usa mock para assert.
- `test_telegram.py` (novo): `notificar_lote` respeita o throttle e envia N mensagens (mock `requests.post` + `time.sleep`).

Mocks isolam `requests`, `yfinance` e `time.sleep` — sem chamadas de rede nem esperas reais nos testes.

---

## 8. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| API B3 retorna 403 (anti-bot) | headers de browser; em falha, degrada para brapi+curados (sem quebrar) |
| Expansão 3/4/11 gera ruído | pré-filtro de volume remove candidatos que não negociam |
| Scan agendado mais lento (universo maior) | cache 1h da lista; `top_n=150` limita; curados garantem mínimo |
| `/scan/all-b3` muda de semântica (~400→~150) | documentar no CHANGELOG; comportamento é o desejado (mais útil e rápido) |
| Limiar R$5M corta nome desejado | curados nunca são cortados; `min_volume_rs` ajustável via CONFIG |

---

## 9. Pontos expostos pela mudança — detalhamento (A1–A5)

### A1 — Violação de camadas (`core` importa `services`)
**Problema:** [`config.py:133`](../../../backend/core/config.py) (`get_all_b3_assets`) faz `from backend.services.data_providers import ...`, invertendo a regra *routers → services → domain/core*.
**Correção:** mover `get_all_b3_assets` para `ticker_loader.py` (wrapper sobre `carregar_tickers_b3`). `config.py` fica só com constantes (`ATIVOS_B3`, `OTM_*`, `CONFIG`) e helpers puros (`score_horario`, reentrada, horário). Consumidores ([`signals.py:8`](../../../backend/api/routers/signals.py), [`signal_service.py:16`](../../../backend/services/signal_service.py)) importam do loader.
**Risco:** baixo — refactor de import; comportamento preservado. Testes de import garantem.

### A2 — Carga de APIs externas a ~3x
**Problema:** scan completo dispara ~150 scrapes `opcoes.net.br` ([`_fetch_chain`](../../../backend/services/data_providers.py#L75)) + ~150 downloads yfinance, 10 concorrentes → risco de bloqueio/429.
**Correção:** `scan_max_workers` (default 8) configurável no `ThreadPoolExecutor` de `run_scan`. Caches existentes (chain 3min, ohlcv 5min) reaproveitados. `top_n` é a alavanca primária para reduzir carga. (Sem reescrever o cliente HTTP — YAGNI.)

### A3 — Telegram sem throttle, bloqueando o loop
**Problema:** [`enviar_telegram`](../../../backend/services/telegram_service.py#L53) (POST síncrono, timeout 10s) roda **dentro** do loop de coleta de `run_scan` ([`signal_service.py:235`](../../../backend/services/signal_service.py#L235)). 3x mais sinais → scan mais lento + 429.
**Correção:** novo `telegram_service.notificar_lote(sinais)` que envia após o loop, com `time.sleep(CONFIG["telegram_throttle_s"])` entre mensagens. `run_scan`/`scan_stream` acumulam e chamam uma vez. `_maybe_broadcast` (SSE) continua no loop (é não-bloqueante).
**Bônus (B3):** ao mexer em `telegram_service`, verificar se as f-strings usam `\\n` literal (renderiza `\n` no Telegram) e corrigir para quebra real se for o caso.

### A4 — Orçamento de tempo vs. cadência de 30min
**Problema:** scan de ~150 + pré-filtro cold pode estourar 30min; `max_instances=1` pula execuções silenciosamente.
**Correção:** logar duração do scan (`início`/`fim`/`Δs`) em `run_scan`; cache de 1h limita o custo do pré-filtro a 1×/hora; `top_n` e `scan_max_workers` são as alavancas. Sem mudar a cadência (decisão do usuário). Observabilidade primeiro; otimização só se os logs mostrarem estouro.

### A5 — `min_volume_diario` → `min_volume_acoes`
**Problema:** dois "volumes" (`min_volume_diario` em ações vs novo `min_volume_rs` em R$) confundem.
**Correção:** rename puro em `config.py`, `core_engine.py:82` e `tests/test_config.py:27`. Lógica inalterada.

---

## 10. Follow-ups (PRs separados)

- **B1 — Decompor `analisar_ativo`** (~330 linhas, [core_engine.py:20-347](../../../backend/services/core_engine.py)) em `_carregar_ohlcv` / `_avaliar_gatilhos` / `_montar_estrutura_opcao` / `_montar_sinal`, com TDD. Maior ganho de manutenção; sensível a comportamento → isolado.
- **B2 — Enriquecer nome em `scan_single`/`scan_batch`** via mapa do loader (hoje usam só `ATIVOS_B3`, mostram código cru para não-curados). Baixa prioridade.

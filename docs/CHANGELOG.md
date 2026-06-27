# Changelog

All notable changes to this project will be documented in this file.

## [Não lançado]

### Fixed
- **Look-ahead bias eliminado nos pivots locais (Camada 0.1):** `is_fundo_local`/
  `is_topo_local` passam a usar janela simétrica confirmada (`pivots_confirmados`,
  `CONFIG["pivot_ordem"]=1`) e os gatilhos de fundos/topos + zonas de demanda/oferta
  consomem apenas pivots confirmados (excluindo as últimas `ordem` linhas). O backtest
  deixa de enxergar o futuro. Backtest de referência (PETR4, 2025-06→2026-06):
  win-rate PENDENTE (medição não concluída — yfinance retornou zero dados em
  ambiente de execução; re-executar com BRAPI_TOKEN configurado), 0 sinais
  (indisponibilidade de dados, não regressão do motor). Guarda permanente em
  `tests/test_lookahead.py`.
- **Bônus de sessão fora do threshold de emissão (Camada 0.2):** a decisão de emitir
  passa a usar **apenas** o score técnico/direcional. O bônus de horário deixa de ser
  somado ao score antes do corte `min_score` e vira campo informativo `bonus_sessao`
  (priorização, não filtro). Sinais carregam `score_tecnico` + `bonus_sessao`,
  persistidos no Supabase (migração `002`) e exibidos separados no Telegram.
- **Cooldown de reentrada por (ticker, direção) (Camada 0.3):** o bloqueio deixa de ser
  cego à direção. Mesma direção dentro de `reentrada_mesma_direcao_dias` bloqueia; a
  direção oposta ao sinal vigente só emite se `score >= score_vigente +
  reentrada_direcao_oposta_delta_score`. `_historico_sinais` passa a guardar tipo+score;
  `rebuild_historico_sinais` reconstrói a partir do Supabase.
- **Higiene técnica (Camada 0.4):** `score_horario`/`dentro_horario_pregao` agora avaliam
  o horário em `America/Sao_Paulo` (antes `datetime.now()` naive, fuso do servidor);
  `tzdata` adicionado às dependências. A chave de cache de OHLCV inclui `period`
  (`ohlcv:{ticker}:{interval}:{period}`), evitando contaminação entre janelas. Config do
  Telegram persiste no Supabase (migração `003`) com fallback ao arquivo JSON.

> **Pendências da Camada 0 (não-bloqueantes):** aplicar as migrações `002`/`003` no
> Supabase (SQL Editor) e medir o delta de backtest pós-correção de look-ahead quando
> houver dados de mercado (`BRAPI_TOKEN`).

### Fixed (Camada 1 — Volatilidade Implícita)
- **Rótulo de IV corrigido**: o campo que era exibido como "IV" na verdade era
  volatilidade histórica de 20 dias. Renomeado para `hv_20d` em todo o backend
  (`signal_service`, `outcome_service`, `outcome.py`, `telegram_service`) e no frontend
  (`SignalCard`, `VolatilitySkew`, `alerts`/`analytics`/`scanner`/`signals` pages).

### Added (Camada 1 — Volatilidade Implícita)
- **Fallback chain de IV implícita real** (`resolver_iv`,
  [backend/domain/options_math.py](../backend/domain/options_math.py)): deriva a IV do
  prêmio real de tela quando disponível e válido (no-arbitrage), cai para a mediana da
  IV dos strikes líquidos vizinhos, depois para HV 20d × 1.1, e por último para um
  default de 0.40. Os Greeks do sinal (`iv_impl`, `iv_source`) agora usam essa cadeia em
  vez da HV histórica.
- **Histórico diário de IV e IV Rank** ([backend/services/iv_history_service.py](../backend/services/iv_history_service.py),
  migração `005`): job agendado pós-fechamento (18h BRT, dias úteis) persiste a IV ATM
  diária por ticker líquido em `iv_history`. `iv_rank()` calcula o percentil de 252 dias
  quando há ≥60 dias úteis de histórico (`confiavel=True`); caso contrário usa o proxy
  `iv_premium` (IV ATM / HV 20d).
- **Filtro de volatilidade na emissão de sinais** (`avaliar_filtro_iv`,
  [backend/domain/scoring.py](../backend/domain/scoring.py)): bloqueia ou exige score
  técnico ≥7 quando a IV Rank/premium indica opção "cara". Roda em **modo shadow** por
  padrão (`CONFIG["iv_filter_mode"]="shadow"` — loga a decisão sem filtrar); modo
  `"ativo"` filtra de fato. Sinais carregam `iv_rank`/`iv_premium`/`iv_filter_decisao`,
  persistidos no Supabase (migração `004`).

> **Pendências da Camada 1 (não-bloqueantes):** aplicar as migrações `004`/`005` no
> Supabase (SQL Editor) antes do deploy; manter `iv_filter_mode="shadow"` em produção
> até `iv_history` acumular ≥60 dias úteis de cobertura para a maioria do universo
> líquido (acompanhar via `iv_rank(...)["confiavel"]`).

### Added
- **Rastreamento de desfecho de sinais** ([backend/domain/outcome.py](../backend/domain/outcome.py),
  [backend/services/outcome_service.py](../backend/services/outcome_service.py)): reprecifica
  cada sinal via Black-Scholes ao longo do preço da ação (abordagem A) e classifica
  ganho/perda/aberto. Endpoint `GET /signals/outcomes?days=N` agrega o **win-rate do
  clássico** vs. o **efeito de filtrar pelo score ponderado** — base de dados para decidir
  o scoring (clássico × ponderado).

### Removido
- **Filtro de R/R retirado**: o gate `rr_alvo1 < rr_minimo` em `_montar_estrutura_opcao`
  e a config `rr_minimo` foram removidos. Como alvos e stop são percentuais fixos, o
  R/R era uma **constante** (~0.58) → o filtro nunca discriminava sinais (aceitava todos
  ou rejeitava todos). Os valores `rr_alvo1/2/final` continuam no sinal como **informação**
  (exibidos no card), apenas não filtram mais. A decisão de emissão fica com `score` + `delta`.

### Melhorias (rodada de refatoração jun/2026)
- **[P0] Cache com fallback em memória** ([backend/core/cache.py](../backend/core/cache.py)):
  quando o Redis está indisponível, o cache passa a usar um store TTL in-process em vez
  de virar no-op. Resolve a causa estrutural do rate-limit (cada scan rebaixava tudo).
  Também corrige `pd.read_json(str)` deprecado.
- **[P1] Logging central** ([backend/core/logging_config.py](../backend/core/logging_config.py)):
  silencia o ruído de providers (yfinance/urllib3/peewee) que poluía o log com
  "possibly delisted"/"Failed download"; aviso da brapi por-ticker rebaixado a debug.
- **[P1] Testes de integração HTTP** ([tests/test_api_integration.py](../tests/test_api_integration.py)):
  cobertura via `TestClient` de health, `/signals`, watchlist, strategies e history.
- **[P1] Fonte única de tickers no frontend** ([src/lib/tickers.ts](../src/lib/tickers.ts)):
  scanner e signals derivam de `SECTORS` (fim da duplicação que exigia editar 2 arquivos).
  Remove OIBR3 (deslistada).
- **[P2] `validar_config()`** ([backend/core/config.py](../backend/core/config.py)): fail-fast
  no boot para invariantes (rr_minimo ≤ R/R natural, DTE/delta válidos, stop<0, alvos crescentes).
- **[P3] Limpeza**: docstring do `scoring` reflete os pesos reais (118 bruto, cap 100);
  remove `calcular_dte` (morto após refactor de vencimentos) e variáveis órfãs.

### Added
- **Carregador dinâmico de tickers da B3** ([backend/services/ticker_loader.py](../backend/services/ticker_loader.py)):
  universo líquido = curados (`ATIVOS_B3`) + API oficial da B3 + brapi, com pré-filtro
  de **volume financeiro (R$)** e `top_n`. Cache TTL em processo (independe do Redis).
- `data_providers`: `fetch_b3_official_tickers()` (API oficial da B3, expansão de
  sufixos 3/4/11) e `filtrar_por_volume()` (volume financeiro médio em R$).
- `CONFIG`: `min_volume_rs`, `ticker_top_n`, `ticker_cache_segundos`, `scan_max_workers`,
  `telegram_throttle_s`.
- `ticker_loader.nome_ativo()`: resolve o nome da empresa (curados → API B3 → código). [B2]
- Testes: `test_ticker_loader`, `test_data_providers`, `test_signal_service`, `test_telegram`
  e **`test_core_engine`** (caracterização de `analisar_ativo`, que antes tinha cobertura zero).

### Changed
- Scan agendado passa a varrer o **universo líquido** por padrão
  (`run_scan(universe="liquido")`); `POST /signals/scan/all-b3` agora varre ~150 líquidos
  (antes ~400 crus). `POST /signals/scan/all` segue na lista curada.
- `get_all_b3_assets` movido de `config` (core) para `ticker_loader` (service) — fim da
  violação de camadas (core importava services). [A1]
- Telegram enviado em **lote com throttle**, fora do hot-loop de scan. [A3]
- Workers do scan configuráveis via `CONFIG["scan_max_workers"]` (era 10 fixo). [A2]
- `CONFIG`: `min_volume_diario` renomeado para `min_volume_acoes` (desambigua do
  `min_volume_rs`). [A5]
- **`analisar_ativo` decomposto** (~330 → ~40 linhas) em `_carregar_ohlcv`,
  `_avaliar_gatilhos`, `_montar_estrutura_opcao` e `_montar_sinal`, sem mudança de
  comportamento (travado por testes de caracterização). [B1]
- `scan_single`/`scan_batch` usam o nome de empresa enriquecido para tickers não-curados. [B2]

### Fixed
- Mensagens do Telegram usavam `\n` literal em vez de quebras de linha reais. [B3]
- **Nenhum sinal era emitido:** o gate de R/R exigia `rr_minimo=0.8`, mas a R/R do alvo1
  (`alvo1_pct/|stop_pct|` ≈ 0.58) é constante e sempre menor → todo sinal (teórico e real)
  era rejeitado. `rr_minimo` baixado para **0.5** (R/R natural da estratégia de scale-out,
  em que alvo1 é realização parcial e alvo2/final são os alvos de fato). Guard em
  `test_config` impede reintroduzir o bug (`rr_minimo <= alvo1_pct/|stop_pct|`).

## [4.2.0] - 2026-06-03

### Refatoração Geral (clean code, sem mudança de contrato)

#### Limpeza estrutural
- Relatórios de sessões antigas movidos da raiz para [docs/archive/](archive/)
  (REWRITE_ANALYSIS, README_REWRITE_SUMMARY, GITHUB_STRUCTURE, CLEANUP_LOG, STRUCTURE, .github-structure).
- `ESTADO_ATUAL.md` e `REPORT_COMPLETO.md` atualizados para refletir o estado real.

#### Backend — routers + camada de serviço
- `backend/api/main.py` reduzido de **898 → 81 linhas**: agora só `create_app()`,
  `lifespan` e `include_router`.
- Endpoints divididos em routers: `health`, `signals`, `scan`, `backtest`, `market`, `config`.
- Lógica de negócio extraída para serviços: `signal_service`, `telegram_service`,
  `supabase_client`, `scheduler`.
- Removido o router `/market` morto (nunca incluído) e a duplicação de endpoints inline.

### Fixed
- **Sombreamento de rotas:** `GET /signals/scan/stream`, `POST /signals/scan/all` e
  `POST /signals/scan/all-b3` eram capturados por `/signals/scan/{ticker}` (retornavam
  422 ou faziam scan errado). A ordenação correta dos routers restaura o comportamento
  esperado pelo frontend. Coberto por `tests/test_api_routing.py` (21 testes).

### Added
- **Testes de front-end:** Vitest + React Testing Library (happy-dom) com 36 testes
  cobrindo `black-scholes`, `strategies`, `monte-carlo`, `format` e smoke RTL.
  Scripts `npm test` / `npm run test:watch`.
- **Paginação real** no histórico de sinais: `offset` em `/signals/history`,
  `fetchSignalHistory(limit, offset)` e botão "Carregar mais" na página de alertas
  (no lugar do limite hardcoded de 200).

## [4.1.0] - 2026-05-29

### Added
- **Shadow mode do score ponderado:** [core_engine.py](../core_engine.py) calcula o score ponderado em paralelo ao clássico e persiste `score_ponderado` + `ponderado_passou` no Supabase, sem afetar a decisão (controlado por `CONFIG["scoring_mode"]`).
- **IV de mercado real:** quando `opcoes.net` retorna `preco_tela`, o pipeline deriva IV via Newton-Raphson e recalcula os Greeks com a IV real. Campo `iv_mercado` no JSON.
- **Filtro de liquidez:** `CONFIG["min_negocios_opcao"] = 10` rejeita opções com poucos negócios em [data_providers.py](../data_providers.py).
- **Fallback brapi:** `fetch_brapi_historical()` é usado quando `yfinance` falha ou retorna vazio.
- **CLI `--realtime`:** scanner v3 ganhou loop nativo com `--realtime --every N --all-b3`.
- **Endpoint `/signals/performance`:** dashboard agregado (win-rate por ticker, score médio clássico × ponderado, concordância, delta médio).
- **Frontend SignalCard:** exibe Delta/Theta/Vega/Gamma/POP/IV e o score ponderado em modo expandido.
- **`backtest_recalibracao.py`:** runner comparativo dos multiplicadores antigos vs novos.

### Fixed
- Removidos avisos do linter: `bb_up` unused em [core_engine.py](../core_engine.py); `interval` unused em `run_scan`; `app` unused no lifespan da FastAPI.

## [4.0.0] - 2026-05-29

### Added
- **Greeks no pipeline:** novo módulo [greeks.py](../greeks.py) com Delta, Gamma, Theta, Vega, Rho, POP e IV (Newton-Raphson). Greeks são anexados a cada sinal e persistidos no Supabase.
- **Filtro de qualidade por Delta:** sinais com `|Δ|` fora de `[delta_min, delta_max]` (0,15–0,45) são rejeitados, evitando deep-OTM sem liquidez.
- **Score ponderado 0–100:** novo módulo [scoring.py](../scoring.py) com pesos calibrados (MACD, RSI, Estocástico, ADX, Bollinger, volume, tendência). Coexiste com o score clássico via `CONFIG["scoring_mode"]`.
- **Indicadores extras:** ADX, Williams %R, CCI, `bb_pct`, `bb_width`, `vol_ratio`, `trend_up`/`trend_down` em [indicators.py](../indicators.py).
- **Universo completo B3:** `data_providers.fetch_all_b3_tickers()` puxa todos os tickers via brapi `/available` (cache 24h). Helper `config.get_all_b3_assets()` mescla com a lista curada. Novo endpoint `POST /signals/scan/all-b3` e flag `?all_b3=true` em `/signals/watchlist`.
- **Watchlist curada expandida:** +23 tickers (COGN3, EMBR3, RENT3, PRIO3, RAIL3, ENEV3, EQTL3, CSAN3, HAPV3, HYPE3, RDOR3, NTCO3, CPLE6, CYRE3, TIMS3, VBBR3, VIVT3, YDUQ3, MULT3, PCAR3, MRFG3, BBDC3, ITUB3).
- **Campo `book_until`** em cada sinal (data-limite da ordem no book, padrão 7 dias).
- **Docs:** [GREEKS_E_BLACK_SCHOLES.md](GREEKS_E_BLACK_SCHOLES.md) e [SCORING_PONDERADO.md](SCORING_PONDERADO.md).

### Changed
- **Alvos recalibrados sobre 31 sinais reais:** `alvo2_pct 1.50→2.50`, `alvo_final_pct 4.00→7.00`, `stop_pct -0.42→-0.43`.
- **Faixa de compra:** de ±10% (hardcoded) para `CONFIG["buy_band_pct"] = 0.035` (±3,5%), alinhado ao padrão observado.
- Removidas todas as menções a "TP Capital" em código, docs e UI.

## [2.1.0] - 2026-05-27

### Added
- **17 Novas Estratégias de Opções:** Adicionado suporte nativo no simulador (frontend) para posições puras, estratégias com ação, spreads, volatilidade e estruturas complexas. 
- **Integração de Preço da Ação-Objeto:** Motor de payoff agora suporta cálculo de Covered Call e Protective Put modelando o PL das ações (`stockOffset`).
- **Cards Dinâmicos:** Interface da página de estratégias reescrita usando um layout de cards responsivo dividido em 5 categorias, com labels inteligentes por strike.
- **Cache Redis no Backend:** Adicionado suporte a `REDIS_URL` para fazer cache dos retornos das APIs do `yfinance` e `opcoes.net.br`.
- **Parallel Scraping:** Endpoint `/market/opcoes` e processos de varredura refatorados para utilizar `ThreadPoolExecutor`, baixando o tempo de latência de varredura das opções.

### Changed
- Refatorado `strategies.ts` exportando metadados completos (`STRATEGY_META`) para serem facilmente consumidos pela UI.
- Otimizada inicialização (`lifespan`) do FastAPI para testar a conectividade do Redis logo no startup.
- Documentação limpa e movida para centralização em `docs/` e `README.md`.

### Fixed
- Corrigido `CORS` configurando corretamente as variáveis de ambiente em produção (Render e Vercel).
- Correção de timezone e timestamps no uso da biblioteca de options pricing.

## [2.0.0] - 2026-05-26

- Lançamento inicial da versão web com Next.js, FastAPI e Supabase.
- Motor com 19 gatilhos técnicos.
- Scanner em tempo real com SSE (Server-Sent Events).

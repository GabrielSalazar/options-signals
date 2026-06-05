# Changelog

All notable changes to this project will be documented in this file.

## [Não lançado]

### Added
- **Carregador dinâmico de tickers da B3** ([backend/services/ticker_loader.py](../backend/services/ticker_loader.py)):
  universo líquido = curados (`ATIVOS_B3`) + API oficial da B3 + brapi, com pré-filtro
  de **volume financeiro (R$)** e `top_n`. Cache TTL em processo (independe do Redis).
- `data_providers`: `fetch_b3_official_tickers()` (API oficial da B3, expansão de
  sufixos 3/4/11) e `filtrar_por_volume()` (volume financeiro médio em R$).
- `CONFIG`: `min_volume_rs`, `ticker_top_n`, `ticker_cache_segundos`, `scan_max_workers`,
  `telegram_throttle_s`.
- Testes: `test_ticker_loader`, `test_data_providers`, `test_signal_service`, `test_telegram`.

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

### Fixed
- Mensagens do Telegram usavam `\n` literal em vez de quebras de linha reais. [B3]

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

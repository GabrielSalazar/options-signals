# Refatoração Geral — B3 Options Signals

**Data:** 2026-06-03
**Autor:** Gabriel Salazar (com assistência do Claude Code)
**Status:** Aprovado — em execução

---

## Objetivo

Refatoração geral faseada do projeto, priorizando legibilidade e clean code, cobrindo:
limpeza estrutural → qualidade de código → fechamento de lacunas de qualidade.

## Fora de escopo (decisões do usuário)

- Autenticação, página `/login` e `middleware.ts` de proteção de rotas.
- Scripts Python legados da raiz: `scanner_opcoes_b3 - v2.py`, `scanner_opcoes_b3_v3.py`,
  `refactor.py` — mantidos intactos nesta rodada (o CLI v3 está com imports quebrados
  pós-migração, mas a decisão de recuperá-lo/removê-lo fica para depois).

## Princípios

- **Sem mudança de comportamento** nas Fases 1–2: os contratos HTTP consumidos pelo
  frontend permanecem idênticos.
- **Verde a cada fase**: a suíte de backend (baseline: 119 testes) deve continuar
  passando após cada commit.
- **Commits coesos**: cada fase é um ou poucos commits com escopo claro.

---

## Fase 1 — Limpeza estrutural (risco baixo)

Não toca em código de execução.

- Criar `docs/archive/` e mover relatórios de sessões antigas da raiz:
  `REWRITE_ANALYSIS.md`, `README_REWRITE_SUMMARY.md`, `GITHUB_STRUCTURE.md`,
  `CLEANUP_LOG.txt`, `STRUCTURE.txt`, `.github-structure.txt`.
- Atualizar `docs/ESTADO_ATUAL.md` e `docs/REPORT_COMPLETO.md` para refletir o estado
  real (Redis ativo, 119 testes de backend, Greeks, score ponderado, backend modularizado),
  marcando os itens já entregues.

**Resultado:** raiz enxuta (sobram README, configs de build, Dockerfile, requirements e
os scripts legados).

## Fase 2 — Qualidade do backend (routers + serviços)

Reorganizar `backend/api/main.py` (898 linhas) sem mudar contratos.

- **Routers** em `backend/api/routers/`: `signals.py`, `scan.py`, `backtest.py`,
  `market.py` (substituindo o router morto atual que nunca foi incluído), `config.py`.
  Cada um com seu `APIRouter`.
- **Serviços** em `backend/services/`:
  - `persist_signals`, `cleanup_old_signals`, `run_scan`/`_scan_one`, `_rebuild_historico_sinais`
    → `signal_service.py`.
  - `enviar_telegram`, `_load_telegram_config`, `_save_telegram_config` → `telegram_service.py`.
  - scheduler + jobs → `scheduler.py`.
- **`main.py` final:** apenas `lifespan`, `create_app()`, configuração de CORS e
  `include_router(...)`. Alvo: < 80 linhas.
- Eliminar a duplicação `/market` (endpoints inline vs router morto).
- Atualizar os imports nos testes existentes conforme os símbolos migram de módulo.

**Critério de aceite:** `python -m pytest` continua verde (119+).

## Fase 3 — Qualidade do frontend + lacunas (sem auth)

- **Setup de testes:** adicionar Vitest + React Testing Library (melhor encaixe com
  Next 16 / React 19 que Jest), script `test` no `package.json`, config e setup base.
- **Testes-base** nos módulos puros de maior ROI: `src/lib/black-scholes.ts`,
  `src/lib/strategies.ts`, `src/lib/monte-carlo.ts`, `src/lib/format.ts`.
- **Paginação:** substituir os limites hardcoded de 200 registros em `alerts`/`signals`
  por paginação real (o backend `/signals` já aceita `limit`/`offset`).

## Fase 4 — Consolidação

- Atualizar `docs/CHANGELOG.md` com a refatoração.
- Verificação final: `python -m pytest` (backend) + `npm test` (frontend) +
  `npm run lint` + `npm run build`, todos verdes.

---

## Arquitetura-alvo do backend (pós-Fase 2)

```
backend/
├─ api/
│  ├─ main.py            # create_app() + lifespan + include_router  (< 80 linhas)
│  └─ routers/
│     ├─ signals.py      # /signals, /signals/history, /signals/analytics, /signals/performance, /signals/watchlist
│     ├─ scan.py         # /signals/scan*, /signals/scan/stream, /signals/alerts/stream
│     ├─ backtest.py     # /backtest/*
│     ├─ market.py       # /market, /market/opcoes, /market/opcoes/chain
│     └─ config.py       # /config/telegram, /signals/strategies
├─ services/
│  ├─ signal_service.py  # persist, cleanup, run_scan, rebuild_historico
│  ├─ telegram_service.py
│  └─ scheduler.py       # BackgroundScheduler + jobs
├─ core/                 # config, cache  (inalterado)
└─ domain/               # greeks, indicators, options_math, scoring  (inalterado)
```

## Riscos e mitigação

- **Quebrar contrato HTTP** → mitigado pela suíte de testes e por manter paths/respostas idênticos.
- **Imports circulares** ao extrair serviços (scheduler usa run_scan que usa persist) →
  organizar dependências em sentido único: `routers → services → domain/core`.
- **Estado global** (`_last_scan_sinais`, `_historico_sinais`) → manter no módulo de serviço
  apropriado, preservando o comportamento atual.

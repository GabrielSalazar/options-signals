# Estado Atual do Projeto — B3 Options Signals

**Data:** 2026-06-03  
**Versão:** v4.1 (Next.js + FastAPI + Supabase + Redis)  
**Status:** Em produção — parcialmente funcional

---

## Stack em Produção

| Camada | Tecnologia | URL | Status |
|--------|-----------|-----|--------|
| Frontend | Next.js 16 + TypeScript + Tailwind | https://options-signals.vercel.app | ✅ Online |
| Backend | FastAPI + Python + APScheduler | https://options-signals-b79i.onrender.com | ✅ Online (free tier) |
| DB/Auth | Supabase PostgreSQL + Realtime | gbpiwddxqkpvpurbnjwv | ✅ Migração aplicada |
| Cache | Redis (via Render) | — | ✅ Ativo e Otimizado |

---

## Páginas Implementadas

| Rota | Componente | Backend Real | Status |
|------|-----------|-------------|--------|
| `/` | Dashboard + LiveFeed + MarketWidget | `/market` | ✅ Completo (paralelizado via Redis) |
| `/scanner` | SSE stream, ~90 tickers B3 | `/signals/scan/stream` | ✅ Completo |
| `/signals` | Filtro setor + stock picker + Realtime | Supabase | ✅ Completo |
| `/alerts` | Feed filtros + CSV + regras localStorage | `/signals/history` | ✅ Completo |
| `/backtest` | Equity curve Recharts (AreaChart) + Sortino/Calmar | `/backtest/run` | ✅ Completo |
| `/analytics` | Vol Smile + IV Surface 3D (Plotly) | `/signals/analytics/{ticker}` | ✅ Completo |
| `/portfolio` | Paper Trading + modal de encerramento | localStorage | ✅ Completo |
| `/strategies` | Biblioteca de estratégias | Motor local (17 estratégias) | ✅ Completo (UI Dinâmica + Gráficos Recharts) |
| `/login` | Autenticação | Supabase Auth | ❌ Rota inexistente |

---

## Endpoints Backend

| Endpoint | Método | Status | Notas |
|----------|--------|--------|-------|
| `/health` | GET | ✅ | Retorna status básico e monitoramento Redis |
| `/signals` | GET | ✅ | Filtros: tipo, min_score, limit, offset |
| `/signals/scan/{ticker}` | POST | ✅ | Input validado (Path regex) |
| `/signals/scan/stream` | GET | ✅ | SSE com progresso por ticker |
| `/signals/scan/all` | POST | ✅ | Scan completo ATIVOS_B3 |
| `/signals/history` | GET | ✅ | Filtros: ticker, tipo_sinal, limit |
| `/signals/analytics/{ticker}` | GET | ✅ | Total, calls, puts, avg_score |
| `/backtest/run` | POST | ✅ | Pydantic validado |
| `/market` | GET | ✅ | IBOV + 8 ações, cache Redis e ThreadPoolExecutor |
| `/config/telegram` | GET/POST | ⚠️ | Não persistido após restart |

---

## Infraestrutura

### Variáveis Vercel
- `NEXT_PUBLIC_SUPABASE_URL` ✅
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` ✅
- `SUPABASE_SERVICE_ROLE_KEY` ✅
- `NEXT_PUBLIC_API_URL` ✅

### Variáveis Render
- `SUPABASE_URL` ✅
- `SUPABASE_SERVICE_ROLE_KEY` ✅
- `ALLOWED_ORIGINS` ✅
- `PORT` ✅
- `REDIS_URL` ✅ Configurado e validado

### Supabase
- Migration 001 aplicada ✅
- 29 colunas na tabela `signals`
- Realtime habilitado
- RLS: anon SELECT, service_role INSERT

---

## APScheduler (Backend)

| Job | Trigger | O que faz |
|-----|---------|-----------|
| `scan_job` | Mon-Fri 10:00–15:30, a cada 30min | Scan de 29 ativos, salva sinais, envia Telegram |
| `cleanup_job` | Diário às 2h | Remove sinais com >30 dias |

---

## Algoritmo de Sinais

Motor de 21 gatilhos técnicos (incluindo ponderados):
- **11 gatilhos ALTA** (G1–G11): Stochastic, RSI, EMA, MACD, Bollinger, Volume, Divergência, Canal, Suporte
- **Novos Gatilhos Institucionais**: VWAP (Bônus +5) e TTM Squeeze (Bônus +8) no modo ponderado
- **8 gatilhos BAIXA** (B1–B8): equivalentes bearish
- **Bônus horário**: +0 a +3 pts conforme janela de liquidez
- **Score mínimo**: 5 (configurável)
- **R/R mínimo**: 0.8x

Performance histórica documentada: 82% win rate, +60.4% expectância por trade.

---

## Construtor de Estratégias (Frontend)

O motor de estratégias suporta as 17 operações estruturadas com cálculo dinâmico de payoff:

| Categoria | Estratégias |
|---|---|
| **Posições Puras** | Long Call, Short Call, Long Put, Short Put |
| **Com Ação** | Covered Call, Protective Put |
| **Spreads** | Bull Call Spread, Bear Put Spread, Bull Put Spread, Bear Call Spread |
| **Volatilidade** | Long Straddle, Long Strangle, Short Straddle, Short Strangle, Butterfly |
| **Complexas** | Iron Condor |

---

## Próximos Passos Prioritários

### Em andamento — Refatoração Geral (jun/2026)
Ver spec em [superpowers/specs/2026-06-03-refatoracao-geral-design.md](superpowers/specs/2026-06-03-refatoracao-geral-design.md):
1. **Limpeza estrutural** — relatórios soltos da raiz movidos para `docs/archive/`; docs de estado atualizados.
2. **Qualidade do backend** — `main.py` (898 linhas) dividido em routers + camada de serviço.
3. **Testes de front-end** — setup Vitest + RTL e cobertura dos módulos puros (`lib/`).
4. **Paginação** — substituir limites hardcoded de 200 em `alerts`/`signals`.

### Backlog (fora da refatoração atual)
- **Página /login + `middleware.ts`** — autenticação e proteção de rotas (adiado).
- **Tab "Opções" MarketWidget** — precisaria endpoint de options pricing.
- **Alertas push/email** — backend não notifica proativamente.
- **Restart Render se adormecido** — render.com → options-signals-b79i → Restart (limitação do free tier).

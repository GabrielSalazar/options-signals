# B3 Options Signals Dashboard

> Professional-grade algorithmic options scanner and analysis platform for B3 (Bolsa de Valores Brasileira) with real-time signals, historical backtesting, and advanced volatility analytics.

[![Next JS](https://img.shields.io/badge/Next-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Development](#development)
- [Known Issues](#known-issues)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Overview

B3 Options Signals is a full-stack platform for algorithmic options trading on the Brazilian exchange. It combines real-time market scanning, proprietary signal generation, and interactive analytics to help traders identify high-probability trading opportunities.

**Key Capabilities:**
- **Real-time market scanner** — automated SSE-based scanning of ~90 B3 tickers with live signal generation
- **Proprietary signal engine** — 19 technical triggers (11 bullish, 8 bearish) with historical backtesting and performance metrics
- **Interactive analytics** — volatility smile analysis, IV surface 3D visualization, Greeks calculation
- **Strategy builder** — 17+ pre-configured options strategies with live payoff simulation and risk analysis
- **Paper trading** — risk-free portfolio simulator for strategy testing and validation

**Production URLs:**

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | [https://options-signals.vercel.app](https://options-signals.vercel.app) | ✅ Live |
| **API Backend** | [https://options-signals-b79i.onrender.com](https://options-signals-b79i.onrender.com) | ✅ Live |
| **API Docs** | [https://options-signals-b79i.onrender.com/docs](https://options-signals-b79i.onrender.com/docs) | ✅ Swagger UI |

---

## Quick Start

### 🐳 Docker (Recommended)

The fastest way to get everything running locally:

```bash
# Clone repository
git clone https://github.com/GabrielSalazar/options-signals.git
cd options-signals

# Start all services (frontend, backend, Redis)
docker-compose up --build
```

Services will be available at:
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

To stop:
```bash
docker-compose down
```

### 🐍 Manual Setup (Python + Node.js)

#### Prerequisites

- Python 3.11+
- Node.js 18+
- pip and npm

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn main:app --reload --port 8000
```

Backend will be available at: [http://localhost:8000](http://localhost:8000)

#### Frontend Setup

In a **new terminal**:

```bash
# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

Frontend will be available at: [http://localhost:3000](http://localhost:3000)

#### Environment Variables

Create `.env.local` in the root directory:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ0...
SUPABASE_SERVICE_ROLE_KEY=eyJ0...

# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Redis (optional, improves performance)
REDIS_URL=redis://localhost:6379

# Telegram Notifications (optional)
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Market Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Web Browser                                 │
│                  (Client Application)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND: Next.js 16 (Vercel)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Pages (src/app/)                                              │
│  ├─ page.tsx              (Dashboard + LiveFeed)               │
│  ├─ scanner/              (Real-time ticker scanner)           │
│  ├─ signals/              (Signal history + filtering)         │
│  ├─ analytics/            (Volatility analysis)                │
│  ├─ backtest/             (Historical simulation)              │
│  ├─ estrategias/          (Strategy library)                   │
│  ├─ portfolio/            (Paper trading)                      │
│  ├─ alerts/               (Alert management)                   │
│  └─ api/                  (Route handlers + middleware)        │
│                                                                 │
│  Components (src/components/)                                  │
│  ├─ SignalCard.tsx        (Individual signal display)          │
│  ├─ SignalsTable.tsx      (Signal table with sorting)          │
│  ├─ LiveFeed.tsx          (Real-time signal feed)              │
│  ├─ MarketWidget.tsx      (Market data display)                │
│  ├─ EquityChart.tsx       (Recharts equity curve)              │
│  ├─ IVSurface.tsx         (Plotly 3D IV surface)               │
│  ├─ PayoffChart.tsx       (Strategy payoff visualization)      │
│  ├─ PortfolioDashboard.tsx (Paper trading UI)                  │
│  ├─ StrategiesBuilder.tsx (Strategy configurator)              │
│  └─ [14 more components]  (UI + domain-specific)               │
│                                                                 │
│  Utilities (src/lib/)                                          │
│  ├─ api.ts                (Backend API calls)                  │
│  ├─ black-scholes.ts      (Options pricing)                    │
│  ├─ monte-carlo.ts        (Risk simulation)                    │
│  ├─ supabase.ts           (DB client)                          │
│  ├─ config.ts             (Constants)                          │
│  └─ format.ts             (Formatting utilities)               │
│                                                                 │
│  Styling: Tailwind CSS + Dotwork Design System (custom)        │
│  State: React Context (AuthContext)                            │
│  Real-time: Supabase Realtime subscriptions + SSE              │
│                                                                 │
└────────────────┬──────────────────────┬──────────────────────────┘
                 │ REST/SSE             │ WebSocket
                 ↓                      ↓
     ┌───────────────────────────┐   ┌────────────────────────────┐
     │ BACKEND: FastAPI          │   │ DATABASE: Supabase         │
     │ (Render - Free Tier)      │   │ (PostgreSQL + Realtime)    │
     │                           │   │                            │
     │ Routes (main.py)          │   │ Tables:                    │
     │ ├─ GET /health           │   │ • signals                  │
     │ ├─ GET /market           │   │ • users (auth)             │
     │ ├─ POST /signals/scan/{t} │   │ • strategies               │
     │ ├─ GET /signals/stream    │   │ • backtest_results        │
     │ ├─ GET /signals           │   │ • alerts                  │
     │ ├─ POST /backtest/run     │   │                            │
     │ ├─ GET /analytics/{ticker}│   │ Auth:                      │
     │ └─ GET /config/telegram   │   │ • Supabase Auth (JWT)     │
     │                           │   │                            │
     │ Modules:                  │   │ Real-time:                │
     │ ├─ core_engine.py         │   │ • PostgreSQL LISTEN/      │
     │ ├─ indicators.py          │   │   NOTIFY                  │
     │ ├─ config.py              │   │ • WebSocket subscr.       │
     │ ├─ cache.py               │   │                            │
     │ ├─ backtest.py            │   │ Security:                 │
     │ ├─ data_providers.py      │   │ • RLS policies            │
     │ └─ scanner_opcoes_b3_v3.py│   │ • JWT validation          │
     │                           │   │                            │
     │ Scheduling (APScheduler): │   │                            │
     │ • scan_job (30min)        │   │                            │
     │ • cleanup_job (daily)     │   │                            │
     │                           │   │                            │
     │ Cache Layer (Redis):      │   │                            │
     │ • Market data (60s TTL)   │   │                            │
     │ • OHLCV cache (300s TTL)  │   │                            │
     │ • Backtest results (tmp)  │   │                            │
     │                           │   │                            │
     │ Performance:              │   │                            │
     │ • ThreadPoolExecutor (3-4)│   │                            │
     │ • Async/await with SSE    │   │                            │
     │ • Pydantic validation     │   │                            │
     │                           │   │                            │
     └───────────────────────────┘   └────────────────────────────┘
                 │                              │
                 └──────────────┬───────────────┘
                                ↓
                   ┌─────────────────────────────┐
                   │ External Data Providers     │
                   ├─────────────────────────────┤
                   │ • Yahoo Finance (yfinance)  │
                   │ • B3 Market Data (opcoes.net)
                   │ • Telegram API (optional)   │
                   └─────────────────────────────┘
```

### Data Flow: Request to Signal

**Scenario: User scans ticker PETR4**

```
1. Frontend User Action
   └─ User clicks "Scan PETR4" button on scanner page
      └─ triggers: handleScan("PETR4", filters)

2. Frontend API Call
   └─ fetch("http://localhost:3000/api/signals/scan", {
        method: "POST",
        body: JSON.stringify({ ticker: "PETR4", filters: {...} })
      })
      
3. Next.js Route Handler (src/app/api/signals/scan/route.ts)
   └─ Validates input (ticker format, etc)
      └─ Forwards to Python backend:
         fetch("http://localhost:8000/signals/scan/PETR4", {...})

4. FastAPI Backend Processing (main.py - /signals/scan/{ticker})
   a) Input Validation
      └─ Path regex check: ^[A-Z0-9]+\.SA$
      
   b) Data Retrieval (core_engine.py - analisar_ativo())
      └─ Check cache (Redis): cache_get_df("ohlcv:PETR4.SA:1d")
         └─ If miss:
            ├─ Download from yfinance (6 months data)
            ├─ Exponential backoff retry (3 attempts: 1s, 2s, 4s)
            └─ Cache to Redis (300s TTL)
      
   c) Indicator Calculation (indicators.py)
      └─ calcular_indicadores(df) computes:
         ├─ RSI (14-period)
         ├─ MACD (12,26,9)
         ├─ Stochastic (14,3,3)
         ├─ Bollinger Bands (20,2)
         ├─ EMA crossovers (8,21)
         ├─ Volume analysis
         ├─ Divergence detection
         ├─ Price channels
         ├─ Support/resistance zones
         └─ [19 total triggers]
      
   d) Signal Scoring (core_engine.py)
      └─ For BULLISH signals (G1-G11):
         ├─ Stochastic oversold? +1
         ├─ RSI momentum? +1
         ├─ EMA crossover? +1
         ├─ MACD crossover? +1
         ├─ [11 triggers total] +1 each
         └─ Session bonus (+0 to +3 based on market hour)
            └─ Score = sum of triggers + session bonus
      
   e) Options Calculation (options_math.py)
      └─ mes_vencimento_ideal(score) → select expiration
      └─ estimar_iv_historica(ticker, mes)
      └─ estimar_premio_otm(strike, iv, dte)
      
   f) Response Construction
      └─ Returns SignalObject:
         {
           "ticker": "PETR4.SA",
           "nome": "Petrobras",
           "tipo_sinal": "ALTA",
           "score": 7,
           "preco_acao": 28.45,
           "ticker_opcao": "PETR4C28",
           "strike_ref": 28.00,
           "dist_otm_pct": 1.6,
           "iv_hist": 0.24,
           "dte": 12,
           "mes_venc": 6,
           "timestamp": "2026-05-27T15:30:00Z"
         }
      
   g) Persistence (if score >= min_score)
      └─ supabase.from("signals")
         .upsert(signal_data)
         └─ Realtime subscriptions notified
      
   h) Notifications (optional)
      └─ If telegram_token configured:
         └─ enviar_telegram(signal) sends to chat

5. Response to Frontend
   └─ JSON response with Signal data
      └─ Frontend displays in SignalCard component
      └─ Updates local state / Supabase Realtime
      └─ Chart updates (if analytics)

6. Background Jobs (APScheduler)
   ├─ scan_job: Every 30 min Mon-Fri 10:00-15:30
   │  └─ Scans all 29 tickers in ATIVOS_B3
   │     └─ Persists signals to Supabase
   │     └─ Sends Telegram notifications
   │
   └─ cleanup_job: Daily at 02:00 UTC
      └─ Deletes signals older than 30 days
```

### Component Architecture

#### Frontend Components

**Layout & Navigation:**
- `layout.tsx` — Root layout with AuthProvider, fonts, metadata
- `SiteNav.tsx` — Navigation bar with active page highlight
- `TickerBar.tsx` — Live IBOV + top 8 stocks ticker strip
- `SiteFooter.tsx` — Footer with contact/links

**Signal Management:**
- `SignalCard.tsx` — Individual signal display with Greeks, IV, DTE
- `SignalsTable.tsx` — Sortable table of signals with filtering
- `LiveFeed.tsx` — Real-time signal feed with Supabase subscriptions

**Analytics & Charts:**
- `EquityChart.tsx` — Recharts line chart for equity curves
- `IVSurface.tsx` — Plotly 3D surface visualization for IV data
- `VolatilitySkew.tsx` — Volatility smile curve (Recharts)
- `PayoffChart.tsx` — Strategy payoff diagram

**Strategy Tools:**
- `StrategiesBuilder.tsx` — Interactive strategy configuration UI
- `GreeksCalculator.tsx` — Real-time Greeks calculation
- `PayoffChart.tsx` — Payoff visualization by underlying price
- `RiskSimulator.tsx` — Monte Carlo risk analysis
- `HedgingSimulator.tsx` — Hedge ratio calculation

**Portfolio Management:**
- `PortfolioDashboard.tsx` — Paper trading interface
- `BacktestMetrics.tsx` — Backtest KPI display (Sharpe, Drawdown, Win Rate)

**UI Primitives:**
- Located in `src/components/ui/` — Radix UI + Tailwind base components

#### Backend Modules

**Core Analysis (core_engine.py)**
```python
def analisar_ativo(ticker, interval="1d", df_provided=None):
    """
    Main analysis function that:
    1. Downloads/caches OHLCV data
    2. Calculates all technical indicators
    3. Generates signal scores
    4. Returns options recommendations
    """
```

**Technical Indicators (indicators.py)**
```python
def calcular_indicadores(df):
    """
    Calculates 19 technical indicators:
    • Momentum: RSI, MACD, Stochastic
    • Volatility: Bollinger Bands, ATR
    • Trend: EMA crossovers
    • Volume: Relative volume
    • Advanced: Divergence, channels, zones
    """
```

**Options Mathematics (options_math.py)**
```python
def mes_vencimento_ideal(score):
    """Selects option expiration based on score"""
    
def estimar_iv_historica(ticker, mes):
    """Calculates historical IV for ticker"""
    
def estimar_premio_otm(strike, iv, dte):
    """Estimates OTM option premium using Black-Scholes"""
```

**Caching Layer (cache.py)**
```python
def cache_get_df(key):
    """Redis GET with fallback to None"""
    
def cache_set_df(key, df, ttl=300):
    """Redis SET with TTL and DataFrame serialization"""
```

**Data Providers (data_providers.py)**
```python
def get_real_options_from_opcoes_net(ticker):
    """Fetches real B3 options chain from opcoes.net API"""
```

**Configuration (config.py)**
```python
ATIVOS_B3 = [
    "PETR4.SA", "VALE3.SA", "USIM5.SA", ...  # 29 tickers
]

CONFIG = {
    "min_volume_diario": 100_000,
    "score_minimo": 5,
    "reentrada_min_dias": 1,
    # ... more settings
}
```

**Backtesting (backtest.py)**
```python
def backtest_strategy(ticker, signals, capital=10000):
    """
    Simulates historical strategy performance:
    • Entry on signal generation
    • Exit on fixed take-profit/stop-loss
    • Returns equity curve, Sharpe, drawdown, win rate
    """
```

**Scheduling (main.py - APScheduler)**
```python
scheduler.add_job(
    scan_job,
    CronTrigger(day_of_week="mon-fri", hour="10-15", minute="*/30"),
    id="scan_job"
)
# Runs every 30 min Mon-Fri 10:00-15:30 (market hours)

scheduler.add_job(
    cleanup_job,
    CronTrigger(hour=2, minute=0),  # 02:00 UTC
    id="cleanup_job"
)
# Runs daily, deletes signals older than 30 days
```

---

## Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 16.1.6 | React framework, SSR, API routes |
| **React** | 19.2.3 | UI library |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 3.4.17 | Styling, responsive design |
| **Radix UI** | Latest | Accessible component primitives |
| **Recharts** | 3.7.0 | 2D charts (equity curves, analysis) |
| **Plotly.js** | 3.5.1 | 3D visualization (IV surface) |
| **Supabase.js** | 2.106.2 | Real-time database client |
| **Axios** | 1.13.4 | HTTP client for API calls |
| **SWR** | 2.4.0 | Data fetching with caching |
| **React Hot Toast** | 2.6.0 | Toast notifications |
| **Lucide React** | 0.563.0 | Icon library |
| **Class Variance Authority** | 0.7.1 | Component variants |
| **clsx** | 2.1.1 | Conditional classname merging |
| **Tailwind Merge** | 3.4.0 | Tailwind class conflict resolution |

**Custom Fonts:**
- DM Sans (body text)
- Lora (headings)
- JetBrains Mono (code/numbers)

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | ≥0.100.0 | Web framework, REST API |
| **Python** | 3.11 | Language |
| **Uvicorn** | ≥0.23.0 | ASGI server |
| **Pydantic** | ≥2.0.0 | Data validation, serialization |
| **APScheduler** | ≥3.10.0 | Background job scheduling |
| **yfinance** | Latest | Market data retrieval |
| **pandas** | Latest | Data manipulation, analysis |
| **numpy** | Latest | Numerical computation |
| **scipy** | Latest | Scientific computing (IV estimation) |
| **redis** | ≥5.0.0 | Caching layer |
| **supabase-py** | ≥2.0.0 | Database client |
| **requests** | Latest | HTTP requests |
| **python-dotenv** | ≥1.0.0 | Environment variable management |
| **python-multipart** | Latest | File upload handling |
| **email-validator** | Latest | Email validation |
| **tqdm** | Latest | Progress bars |
| **colorama** | Latest | Terminal colors |
| **tabulate** | Latest | Table formatting |

### Database

| Technology | Component | Purpose |
|------------|-----------|---------|
| **PostgreSQL** | Supabase | Primary data store |
| **Realtime Subscriptions** | Supabase | WebSocket push notifications |
| **Row Level Security** | Supabase | Authorization layer |
| **Redis** | Render | Distributed cache |

### DevOps & Deployment

| Technology | Purpose |
|-----------|---------|
| **Docker** | Containerization |
| **Docker Compose** | Local orchestration |
| **Vercel** | Frontend hosting (Next.js optimized) |
| **Render** | Backend hosting (FastAPI + free tier) |
| **GitHub** | Source control, CI/CD |
| **Supabase** | Managed PostgreSQL + Realtime |

### Development Tools

| Tool | Purpose |
|------|---------|
| **ESLint** | JavaScript/TypeScript linting |
| **TypeScript Compiler** | Type checking |
| **Tailwind CSS** | Styling utility framework |
| **PostCSS** | CSS transformation |
| **Autoprefixer** | CSS vendor prefixes |

---

## Features

### ✅ Fully Implemented

#### Real-time Scanning
- Live SSE stream scanning ~90 B3 tickers simultaneously
- Progress visualization with completion percentage
- 19 technical trigger calculation per ticker
- Dynamic signal generation with score-based ranking
- Optional Telegram push notifications

#### Signal Management
- Persistent signal history in Supabase (30-day rolling window)
- Multi-field filtering (ticker, signal type, sector, date range)
- Supabase Realtime subscriptions for live feed updates
- CSV export of signal history
- Manual filter configuration with localStorage persistence

#### Historical Analysis
- Full backtest engine with walk-forward analysis
- Equity curve visualization with Recharts
- Performance metrics: Sharpe ratio, max drawdown, win rate, total return
- Trade-by-trade breakdown
- Strategy parameter optimization

#### Volatility Analytics
- Volatility smile curve visualization (2D)
- IV surface 3D rendering (Plotly)
- Historical IV estimation by expiration month
- Call/Put IV comparison
- Greeks visualization (Delta, Gamma, Theta, Vega)

#### Strategy Library
- 17 pre-configured options strategies:
  - **Basic:** Long Call, Long Put, Covered Call, Protective Put
  - **Spreads:** Bull Call/Put Spread, Bear Call/Put Spread, Iron Condor
  - **Advanced:** Long/Short Straddle, Long/Short Strangle, Butterfly
  - **Ratio:** Call Ratio, Put Ratio
  - **Custom:** User-defined strategies
- Interactive payoff diagram calculator
- Greeks-based pricing with Black-Scholes
- Risk/Reward ratio visualization
- Live strategy simulation

#### Paper Trading
- Simulated portfolio with real signal entry points
- Position entry/exit mechanics with market impact
- P&L tracking in real-time
- Portfolio composition visualization
- Trade history with detailed metrics

#### Market Data
- Live IBOV index tracking
- Top 8 stock prices in TickerBar
- Market hours validation (Mon-Fri 10:00-15:30 Brasília time)
- Real-time data refresh

### ⚠️ Partial Implementation

| Feature | Status | Blocker |
|---------|--------|---------|
| **Options Pricing Tab** | UI skeleton exists | Backend endpoint for real options chain needed |
| **Proactive Alerts** | Rules can be defined | Backend notification system not implemented |
| **Live Greeks** | Frontend calculation done | Real-time options data needed |

### ❌ Not Implemented

| Feature | Impact | Est. Effort |
|---------|--------|------------|
| **Login/Authentication Page** | High — nav link broken | 2–3 hours |
| **Route Protection Middleware** | High — auth prerequisite | 2 hours |
| **Automated Test Suite** | High — 0% coverage | 3–5 days |
| **Rate Limiting** | Medium — DoS prevention | 2 hours |
| **Observability/Metrics** | Medium — production visibility | 1 day |

---

## Project Structure

```
options-signals/
│
├── Frontend (Next.js)
│   ├── src/
│   │   ├── app/                          # Next.js App Router pages
│   │   │   ├── page.tsx                  # Dashboard home
│   │   │   ├── layout.tsx                # Root layout with providers
│   │   │   ├── error.tsx                 # Error boundary
│   │   │   ├── global-error.tsx          # Global error handler
│   │   │   │
│   │   │   ├── scanner/                  # Real-time scanner
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── signals/                  # Signal history & filtering
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── analytics/                # Volatility analysis
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── backtest/                 # Historical simulation
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── estrategias/              # Strategy library
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── portfolio/                # Paper trading
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── alerts/                   # Alert management
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── api/                      # Next.js API routes
│   │   │   │   ├── signals/
│   │   │   │   ├── backtest/
│   │   │   │   ├── analytics/
│   │   │   │   └── health/
│   │   │   │
│   │   │   └── globals.css               # Global styles + Tailwind
│   │   │
│   │   ├── components/                   # Reusable React components
│   │   │   ├── SignalCard.tsx            # Signal display card
│   │   │   ├── SignalsTable.tsx          # Signal table
│   │   │   ├── LiveFeed.tsx              # Real-time feed
│   │   │   ├── MarketWidget.tsx          # Market data display
│   │   │   ├── EquityChart.tsx           # Equity curve (Recharts)
│   │   │   ├── IVSurface.tsx             # 3D IV surface (Plotly)
│   │   │   ├── VolatilitySkew.tsx        # Vol smile (Recharts)
│   │   │   ├── PayoffChart.tsx           # Strategy payoff
│   │   │   ├── StrategiesBuilder.tsx     # Strategy UI
│   │   │   ├── GreeksCalculator.tsx      # Greeks calculation
│   │   │   ├── PortfolioDashboard.tsx    # Paper trading UI
│   │   │   ├── BacktestMetrics.tsx       # Backtest KPIs
│   │   │   ├── SiteNav.tsx               # Navigation
│   │   │   ├── TickerBar.tsx             # Live ticker strip
│   │   │   ├── SiteFooter.tsx            # Footer
│   │   │   ├── RiskBadge.tsx             # Risk indicator
│   │   │   ├── RiskSimulator.tsx         # Risk analysis
│   │   │   ├── HedgingSimulator.tsx      # Hedging calculation
│   │   │   ├── CollapseShell.tsx         # Collapsible container
│   │   │   └── ui/                       # Radix UI primitives
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── select.tsx
│   │   │       ├── input.tsx
│   │   │       └── [more]
│   │   │
│   │   ├── lib/                          # Utility functions
│   │   │   ├── api.ts                    # Backend API client (Axios)
│   │   │   ├── black-scholes.ts          # Options pricing
│   │   │   ├── monte-carlo.ts            # Risk simulation
│   │   │   ├── supabase.ts               # Supabase client
│   │   │   ├── supabase-auth.ts          # Auth utilities
│   │   │   ├── supabase-db.ts            # DB queries
│   │   │   ├── config.ts                 # Constants
│   │   │   └── format.ts                 # Formatting helpers
│   │   │
│   │   ├── context/                      # React Context
│   │   │   └── AuthContext.tsx           # Global auth state
│   │   │
│   │   ├── hooks/                        # Custom hooks
│   │   │   └── useSignals.ts             # Signal data fetching
│   │   │
│   │   └── types/                        # TypeScript types
│   │       ├── signals.ts
│   │       ├── strategies.ts
│   │       └── [more]
│   │
│   ├── package.json                      # Dependencies + scripts
│   ├── tsconfig.json                     # TypeScript config
│   ├── tailwind.config.js                # Tailwind theme config
│   ├── postcss.config.js                 # PostCSS config
│   ├── eslint.config.mjs                 # ESLint rules
│   └── .env.local                        # Environment variables
│
├── Backend (FastAPI + Python)
│   ├── main.py                           # FastAPI app, routers
│   ├── core_engine.py                    # Signal analysis engine
│   ├── indicators.py                     # Technical indicators
│   ├── options_math.py                   # Options Greeks & pricing
│   ├── backtest.py                       # Backtesting engine
│   ├── config.py                         # B3 tickers, parameters
│   ├── cache.py                          # Redis caching layer
│   ├── data_providers.py                 # Market data sources
│   ├── scanner_opcoes_b3_v3.py           # Telegram integration
│   │
│   ├── requirements.txt                  # Python dependencies
│   ├── .env                              # Environment variables
│   └── Dockerfile                        # Container image
│
├── Infrastructure
│   ├── docker-compose.yml                # Local development stack
│   ├── .dockerignore                     # Docker build exclusions
│   ├── .gitignore                        # Git exclusions
│   └── render.yaml                       # Render deployment config
│
├── Documentation
│   ├── docs/
│   │   ├── ESTADO_ATUAL.md              # Current project status
│   │   ├── REPORT_COMPLETO.md           # Full audit report
│   │   ├── ARQUITETURA_PRODUCAO.md      # Production architecture
│   │   ├── QUICKSTART.md                # Setup guide
│   │   ├── ESTRATEGIAS_OPCOES_B3.md     # Signal triggers explained
│   │   ├── MONTAGEM_DE_SINAL_B3.md      # Signal pipeline
│   │   ├── SUPABASE_SETUP.md            # Database schema
│   │   ├── CHANGELOG.md                 # Version history
│   │   └── LINKS_PRODUCAO.md            # Production resources
│   │
│   ├── gregas/                           # Strategy documentation
│   │   ├── RESUMO_EXECUTIVO.md
│   │   ├── fase2_estrategias_detalhado.md
│   │   └── plano_desenvolvimento_gregas.md
│   │
│   └── README.md                         # This file
│
└── Configuration
    ├── tsconfig.json                     # TypeScript config
    ├── next.config.js                    # Next.js config
    ├── tailwind.config.js                # Tailwind config
    └── .claude/                          # Claude Code settings
        └── settings.local.json
```

---

## API Reference

### Base URL
```
http://localhost:8000
```

### Authentication
Currently no authentication required on endpoints. Supabase Auth will be integrated in v2.2.

### Endpoints

#### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "2.1",
  "timestamp": "2026-05-27T15:30:00Z",
  "redis": "connected"
}
```

#### 2. Market Data
```http
GET /market
```

Returns IBOV and 8 major stock prices (cached for 60 seconds).

**Response:**
```json
{
  "ibov": 129850.25,
  "stocks": {
    "PETR4.SA": 28.45,
    "VALE3.SA": 72.10,
    "USIM5.SA": 18.95,
    ...
  },
  "cached": true,
  "timestamp": "2026-05-27T15:30:00Z"
}
```

#### 3. Scan Single Ticker
```http
POST /signals/scan/{ticker}
```

Scans a single ticker and returns signal if conditions met.

**Path Parameters:**
- `ticker` (string, required) — B3 ticker format (e.g., `PETR4.SA`)

**Query Parameters:**
- `min_score` (int, default: 5) — Minimum signal score
- `min_volume` (int, default: 100000) — Minimum daily volume

**Response:**
```json
{
  "sinal": {
    "ticker": "PETR4.SA",
    "nome": "Petrobras",
    "tipo_sinal": "ALTA",
    "score": 7,
    "preco_acao": 28.45,
    "ticker_opcao": "PETR4C28",
    "strike_ref": 28.00,
    "dist_otm_pct": 1.6,
    "iv_hist": 0.24,
    "dte": 12,
    "mes_venc": 6,
    "gregas": {
      "delta": 0.65,
      "gamma": 0.08,
      "theta": -0.02,
      "vega": 0.15
    },
    "timestamp": "2026-05-27T15:30:00Z"
  }
}
```

#### 4. Scan Stream (SSE)
```http
GET /signals/scan/stream
```

Server-Sent Events stream scanning all B3 tickers. Keep connection open for ~3–5 minutes.

**Query Parameters:**
- `min_score` (int, default: 5)
- `limit` (int, default: 100)

**Response (Server-Sent Events):**
```
data: {"ticker":"PETR4.SA","progress":"1/90"}
data: {"ticker":"VALE3.SA","progress":"2/90","sinal":{...}}
...
```

#### 5. Signal History
```http
GET /signals
```

Retrieve historical signals with filtering.

**Query Parameters:**
- `ticker` (string, optional) — Filter by ticker
- `tipo_sinal` (string, optional) — "ALTA" or "BAIXA"
- `limit` (int, default: 50)
- `offset` (int, default: 0)

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "ticker": "PETR4.SA",
      "tipo_sinal": "ALTA",
      "score": 7,
      ...
    }
  ],
  "total": 342,
  "limit": 50,
  "offset": 0
}
```

#### 6. Backtest Strategy
```http
POST /backtest/run
```

Simulate historical strategy performance.

**Request Body:**
```json
{
  "ticker": "PETR4.SA",
  "strategy": "long_call",
  "entry_score": 5,
  "initial_capital": 10000,
  "position_size": 0.1
}
```

**Response:**
```json
{
  "sinais": 45,
  "metrics": {
    "win_rate": 0.82,
    "total_return": 0.604,
    "max_drawdown": -0.18,
    "sharpe_ratio": 1.45,
    "trades": 45
  },
  "equity_curve": [10000, 10150, 10320, ...],
  "data": [
    {
      "date": "2024-01-15",
      "entry_price": 28.45,
      "exit_price": 29.10,
      "pnl": 0.065,
      "return_pct": 2.3
    }
  ]
}
```

#### 7. Volatility Analytics
```http
GET /signals/analytics/{ticker}
```

Get volatility and IV data for a ticker.

**Path Parameters:**
- `ticker` (string, required) — B3 ticker

**Response:**
```json
{
  "ticker": "PETR4.SA",
  "total_signals": 15,
  "calls": 8,
  "puts": 7,
  "avg_score": 6.2,
  "avg_iv": 0.24,
  "iv_by_month": {
    "jun": 0.23,
    "jul": 0.25,
    "aug": 0.26
  },
  "volatility_smile": [
    {"strike": 26.0, "iv": 0.28},
    {"strike": 28.0, "iv": 0.24},
    {"strike": 30.0, "iv": 0.26}
  ]
}
```

#### 8. Telegram Configuration
```http
GET /config/telegram
POST /config/telegram
```

Get or update Telegram bot configuration.

**POST Body:**
```json
{
  "token": "123:ABC...",
  "chat_id": "123456789"
}
```

**Response:**
```json
{
  "configured": true,
  "chat_id": "123456789"
}
```

### Error Handling

All errors return standard HTTP status codes with JSON error details:

```json
{
  "detail": "Invalid ticker format. Expected: XXX9.SA"
}
```

**Common Status Codes:**
- `400` — Bad request (invalid parameters)
- `404` — Resource not found
- `500` — Server error
- `503` — Service unavailable (Redis/Supabase down)

### Rate Limiting

Currently **not enforced**. Will be added in v2.3.

---

## Development

### Frontend Development

**Start dev server:**
```bash
npm run dev
```

**Build for production:**
```bash
npm run build
npm start
```

**Linting:**
```bash
npm run lint
```

**Type checking:**
```bash
tsc --noEmit
```

### Backend Development

**Start with auto-reload:**
```bash
uvicorn main:app --reload --port 8000
```

**View API documentation:**
```
http://localhost:8000/docs
```

**Run background jobs:**
Jobs start automatically with APScheduler. Monitor in logs:
```
2026-05-27 15:30:00 INFO scan_job: Scanning 29 tickers...
2026-05-27 15:35:00 INFO scan_job: Found 12 signals
```

### Testing

Currently **0% test coverage**. Adding tests is a v2.3 priority.

**Planned test structure:**
```
tests/
├── backend/
│   ├── test_core_engine.py
│   ├── test_indicators.py
│   └── test_backtest.py
└── frontend/
    ├── components.test.tsx
    └── hooks.test.ts
```

---

## Known Issues & Roadmap

### 🔴 High Priority Bugs

**Backend:**
1. **Telegram Config Persistence** — Settings lost on server restart
   - Fix: Persist to Supabase instead of temporary JSON file
   
2. **Timezone Edge Cases** — `dentro_horario_pregao()` uses `datetime.now()` 
   - Fix: Use `pytz.timezone('America/Sao_Paulo')`
   
3. **Cache Key Collision** — Backtest cache doesn't include interval/period
   - Fix: `f"ohlcv:{ticker}:{interval}:{period}"`
   
4. **Redis Reconnection** — Disabled after first failure
   - Fix: Implement exponential backoff retry logic

**Frontend:**
1. **SSE Unmount Race Condition** — Message handler writes to unmounted component
   - Fix: Add `if (!mountedRef.current) return` check
   
2. **Token Expiration** — Supabase auth tokens expire silently after 1 hour
   - Fix: Implement `onAuthStateChange()` token refresh
   
3. **Array Bounds Check Missing** — `SignalCard.tsx` accesses `meses[signal.mes_venc - 1]`
   - Fix: Guard with bounds check
   
4. **Artificial Delay** — 400ms fake delay in strategies page
   - Fix: Remove timeout artifact

### 🟡 Medium Priority

- Add rate limiting to backend
- Implement observability (logs, metrics, tracing)
- Add automated test suite
- Implement authentication system

### 🟢 Roadmap

**v2.2 (Next):**
- Implement `/login` page with Supabase Auth
- Add route protection middleware
- Fix all high-priority bugs
- Add rate limiting

**v2.3:**
- Establish automated test suite (Jest + pytest)
- Add observability/monitoring
- Implement WebSocket notifications for alerts
- Improve performance with query optimization

**v3.0:**
- Multi-user support with proper authentication
- Real broker API integration
- Advanced backtester with Monte Carlo
- Live trading capability

---

## Deployment

### Prerequisites

- GitHub account with repository push access
- Vercel account (free tier sufficient)
- Render.com account (free tier sufficient)
- Supabase project created

### Frontend Deployment (Vercel)

1. **Connect repository:**
   - Go to [vercel.com](https://vercel.com)
   - Import GitHub repository
   - Select root directory (or specify `./`)

2. **Set environment variables:**
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` (production backend URL)

3. **Deploy:**
   ```bash
   git push origin main
   ```
   Vercel auto-deploys on push.

**Production URL:** [https://options-signals.vercel.app](https://options-signals.vercel.app)

### Backend Deployment (Render.com)

1. **Create new Web Service:**
   - Connect GitHub repository
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port ${PORT}`

2. **Set environment variables:**
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `ALLOWED_ORIGINS` (include Vercel frontend URL)
   - `REDIS_URL` (if using Redis)
   - `TELEGRAM_BOT_TOKEN` (optional)
   - `TELEGRAM_CHAT_ID` (optional)

3. **Deploy:**
   - Trigger manual deploy or push to main

**Production URL:** [https://options-signals-b79i.onrender.com](https://options-signals-b79i.onrender.com)

**Note:** Free tier has cold-start delays (~30s). Upgrade to Pro for better performance.

### Database Setup (Supabase)

1. Create PostgreSQL project
2. Run migration in SQL editor:
   ```sql
   CREATE TABLE signals (
     id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
     ticker text NOT NULL,
     tipo_sinal text NOT NULL,
     score int,
     preco_acao float,
     created_at timestamp DEFAULT now()
   );
   ```
3. Enable Row Level Security (RLS)
4. Enable Realtime for `signals` table

---

## Troubleshooting

### "Unable to connect to backend"

**Symptoms:** "Connection refused" or timeout errors

**Diagnosis:**
1. Check `NEXT_PUBLIC_API_URL` matches backend URL
2. Verify backend is running: `curl http://localhost:8000/health`
3. Check CORS: backend should log `ALLOWED_ORIGINS` validation
4. If Render free tier: backend may be cold (wait 30 seconds)

**Fix:**
```bash
# Local development
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

# Production
NEXT_PUBLIC_API_URL=https://options-signals-b79i.onrender.com npm run build
```

### "No signals found"

**Symptoms:** Scanner shows 0 signals

**Diagnosis:**
1. Check market hours: Mon–Fri, 10:00–15:30 Brasília time (UTC-3)
2. Check score threshold: default minimum is 5
3. Verify B3 market is open (not a holiday)
4. Check volume filter: stocks must have >100k daily volume

**Fix:**
Lower minimum score threshold in scanner UI filters.

### "Redis connection failed"

**Symptoms:** Backend logs show "Redis unavailable"

**Diagnosis:**
1. Check Redis is running: `redis-cli ping` should return `PONG`
2. Check Redis URL in environment: `echo $REDIS_URL`

**Fix:**
```bash
# If using Docker
docker-compose up redis

# If installed locally
redis-server
```

### "Paper trading portfolio not saving"

**Symptoms:** Refreshing page loses portfolio

**Diagnosis:**
Portfolio uses browser `localStorage`, not persistent backend

**Fix:**
Workaround: Export portfolio to CSV before closing browser

---

## Contributing

Contributions welcome! Before starting work:

1. **Check current issues:** [GitHub Issues](https://github.com/GabrielSalazar/options-signals/issues)
2. **Review audit report:** [REPORT_COMPLETO.md](./docs/REPORT_COMPLETO.md)
3. **Create issue for major changes:** Discuss approach before implementation
4. **Follow conventions:**
   - TypeScript: strict mode, explicit types
   - Python: type hints with Pydantic validation
   - Commits: descriptive messages with issue references
5. **Test locally:** Run dev server and test UI/API changes

**Code Quality Standards:**
- Frontend: ESLint (Next.js preset), TypeScript strict mode
- Backend: Type hints required, Pydantic validation for inputs
- Both: No console.log in production code, meaningful error messages

---

## License

Proprietary. Not for redistribution without explicit written permission.

---

## Support & Contact

- **Issues/Bugs:** [GitHub Issues](https://github.com/GabrielSalazar/options-signals/issues)
- **Email:** [gsalazar93@gmail.com](mailto:gsalazar93@gmail.com)
- **Telegram:** [@OptionsSignals](https://t.me/optionssignals) (if enabled)
- **Production Status:** [https://options-signals.vercel.app](https://options-signals.vercel.app)

---

## Additional Resources

**Documentation:**
- [ESTADO_ATUAL.md](./docs/ESTADO_ATUAL.md) — Current project status and pages
- [REPORT_COMPLETO.md](./docs/REPORT_COMPLETO.md) — Full technical audit
- [ARQUITETURA_PRODUCAO.md](./docs/ARQUITETURA_PRODUCAO.md) — Production architecture
- [ESTRATEGIAS_OPCOES_B3.md](./docs/ESTRATEGIAS_OPCOES_B3.md) — Signal triggers explained
- [QUICKSTART.md](./docs/QUICKSTART.md) — Setup guide

**External:**
- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Guide](https://fastapi.tiangolo.com)
- [Supabase Docs](https://supabase.com/docs)
- [Tailwind CSS Reference](https://tailwindcss.com/docs)
- [Recharts Gallery](https://recharts.org)
- [Plotly.js Documentation](https://plotly.com/javascript)

---

**Last Updated:** 2026-05-27  
**Version:** 2.1  
**Maintainer:** Gabriel Salazar  
**Repository:** [https://github.com/GabrielSalazar/options-signals](https://github.com/GabrielSalazar/options-signals)
**Last Updated:** 2026-05-27 (rewritten with comprehensive architecture)  

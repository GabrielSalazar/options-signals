# Dashboard de Sinais de Opções B3

> Plataforma profissional de análise e backtesting de oportunidades no mercado de Opções da B3 (Bolsa de Valores Brasileira) com sinais em tempo real, simulação histórica e análise avançada de volatilidade.

[![Next JS](https://img.shields.io/badge/Next-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-%23007ACC.svg?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python](https://img.shields.io/badge/Python-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

---

## Índice

- [Visão Geral](#visão-geral)
- [Início Rápido](#início-rápido)
- [Arquitetura](#arquitetura)
- [Stack de Tecnologias](#stack-de-tecnologias)
- [Funcionalidades](#funcionalidades)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Referência da API](#referência-da-api)
- [Desenvolvimento](#desenvolvimento)
- [Problemas Conhecidos](#problemas-conhecidos)
- [Deployment](#deployment)
- [Contribuindo](#contribuindo)

---

## Visão Geral

B3 Options Signals é uma plataforma full-stack para negociação algorítmica de opções na bolsa brasileira. Combina varredura de mercado em tempo real, geração proprietária de sinais e análise interativa para ajudar traders a identificar oportunidades de negociação de alta probabilidade.

**Capacidades Principais:**
- **Scanner de mercado em tempo real** — varredura automatizada baseada em SSE de ~90 tickers B3 com geração de sinais ao vivo
- **Motor de sinais proprietário** — 19 gatilhos técnicos (11 bullish, 8 bearish) com backtesting histórico e métricas de desempenho
- **Análise interativa** — análise de volatility smile, visualização de superfície 3D de IV, cálculo de gregas
- **Construtor de estratégias** — 17+ estratégias de opções pré-configuradas com simulação dinâmica de payoff e análise de risco
- **Paper trading** — simulador de portfólio sem risco para teste e validação de estratégias

**URLs de Produção:**

| Serviço | URL | Status |
|---------|-----|--------|
| **Frontend** | [https://options-signals.vercel.app](https://options-signals.vercel.app) | ✅ Online |
| **API Backend** | [https://options-signals-b79i.onrender.com](https://options-signals-b79i.onrender.com) | ✅ Online |
| **Documentação API** | [https://options-signals-b79i.onrender.com/docs](https://options-signals-b79i.onrender.com/docs) | ✅ Swagger UI |

---

## Início Rápido

### 🐳 Docker (Recomendado)

A forma mais rápida de executar tudo localmente:

```bash
# Clonar repositório
git clone https://github.com/GabrielSalazar/options-signals.git
cd options-signals

# Iniciar todos os serviços (frontend, backend, Redis)
docker-compose up --build
```

Os serviços estarão disponíveis em:
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **API Backend:** [http://localhost:8000](http://localhost:8000)
- **Documentação API:** [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

Para parar:
```bash
docker-compose down
```

### 🐍 Setup Manual (Python + Node.js)

#### Pré-requisitos

- Python 3.11+
- Node.js 18+
- pip e npm

#### Setup do Backend

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Iniciar servidor FastAPI
uvicorn main:app --reload --port 8000
```

Backend estará disponível em: [http://localhost:8000](http://localhost:8000)

#### Setup do Frontend

Em **outro terminal**:

```bash
# Instalar dependências
npm install

# Iniciar servidor dev Next.js
npm run dev
```

Frontend estará disponível em: [http://localhost:3000](http://localhost:3000)

#### Variáveis de Ambiente

Crie `.env.local` no diretório raiz:

```env
# Configuração Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ0...
SUPABASE_SERVICE_ROLE_KEY=eyJ0...

# Configuração API
NEXT_PUBLIC_API_URL=http://localhost:8000

# Redis (opcional, melhora performance)
REDIS_URL=redis://localhost:6379

# Notificações Telegram (opcional)
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui

# Configuração de Mercado
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## Arquitetura

### Visão Geral do Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                     Navegador Web                               │
│                  (Aplicação do Cliente)                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND: Next.js 16 (Vercel)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Páginas (src/app/)                                            │
│  ├─ page.tsx              (Dashboard + Feed ao Vivo)           │
│  ├─ scanner/              (Scanner de tickers em tempo real)   │
│  ├─ signals/              (Histórico + filtros de sinais)      │
│  ├─ analytics/            (Análise de volatilidade)            │
│  ├─ backtest/             (Simulação histórica)                │
│  ├─ estrategias/          (Biblioteca de estratégias)          │
│  ├─ portfolio/            (Paper trading)                      │
│  ├─ alerts/               (Gerenciamento de alertas)           │
│  └─ api/                  (Manipuladores de rotas + middleware)│
│                                                                 │
│  Componentes (src/components/)                                 │
│  ├─ SignalCard.tsx        (Exibição de sinal individual)      │
│  ├─ SignalsTable.tsx      (Tabela de sinais com ordenação)    │
│  ├─ LiveFeed.tsx          (Feed de sinais em tempo real)       │
│  ├─ MarketWidget.tsx      (Exibição de dados de mercado)       │
│  ├─ EquityChart.tsx       (Curva de equity Recharts)          │
│  ├─ IVSurface.tsx         (Superfície 3D IV Plotly)           │
│  ├─ PayoffChart.tsx       (Visualização de payoff)            │
│  ├─ PortfolioDashboard.tsx (UI de paper trading)              │
│  ├─ StrategiesBuilder.tsx (Configurador de estratégias)       │
│  └─ [14+ componentes]     (UI + domínio-específico)           │
│                                                                 │
│  Utilitários (src/lib/)                                        │
│  ├─ api.ts                (Chamadas da API Backend)            │
│  ├─ black-scholes.ts      (Precificação de opções)            │
│  ├─ monte-carlo.ts        (Simulação de risco)                │
│  ├─ supabase.ts           (Cliente DB)                         │
│  ├─ config.ts             (Constantes)                         │
│  └─ format.ts             (Utilitários de formatação)          │
│                                                                 │
│  Estilo: Tailwind CSS + Dotwork Design System (customizado)    │
│  Estado: React Context (AuthContext)                           │
│  Tempo Real: Supabase Realtime + SSE                           │
│                                                                 │
└────────────────┬──────────────────────┬──────────────────────────┘
                 │ REST/SSE             │ WebSocket
                 ↓                      ↓
     ┌───────────────────────────┐   ┌────────────────────────────┐
     │ BACKEND: FastAPI          │   │ DATABASE: Supabase         │
     │ (Render - Free Tier)      │   │ (PostgreSQL + Realtime)    │
     │                           │   │                            │
     │ Rotas (main.py)           │   │ Tabelas:                   │
     │ ├─ GET /health           │   │ • signals                  │
     │ ├─ GET /market           │   │ • users (auth)             │
     │ ├─ POST /signals/scan/{t} │   │ • strategies               │
     │ ├─ GET /signals/stream    │   │ • backtest_results        │
     │ ├─ GET /signals           │   │ • alerts                  │
     │ ├─ POST /backtest/run     │   │                            │
     │ ├─ GET /analytics/{ticker}│   │ Autenticação:              │
     │ └─ GET /config/telegram   │   │ • Supabase Auth (JWT)     │
     │                           │   │                            │
     │ Módulos:                  │   │ Tempo Real:                │
     │ ├─ core_engine.py         │   │ • PostgreSQL LISTEN/      │
     │ ├─ indicators.py          │   │   NOTIFY                  │
     │ ├─ config.py              │   │ • Subscrições WebSocket   │
     │ ├─ cache.py               │   │                            │
     │ ├─ backtest.py            │   │ Segurança:                 │
     │ ├─ data_providers.py      │   │ • Políticas RLS            │
     │ └─ scanner_opcoes_b3_v3.py│   │ • Validação JWT            │
     │                           │   │                            │
     │ Agendamento (APScheduler):│   │                            │
     │ • scan_job (30min)        │   │                            │
     │ • cleanup_job (diário)    │   │                            │
     │                           │   │                            │
     │ Camada de Cache (Redis):  │   │                            │
     │ • Dados de mercado (60s)  │   │                            │
     │ • Cache OHLCV (300s)      │   │                            │
     │ • Resultados backtest (tmp)                                 │
     │                           │   │                            │
     │ Performance:              │   │                            │
     │ • ThreadPoolExecutor (3-4)│   │                            │
     │ • Async/await com SSE     │   │                            │
     │ • Validação Pydantic      │   │                            │
     │                           │   │                            │
     └───────────────────────────┘   └────────────────────────────┘
                 │                              │
                 └──────────────┬───────────────┘
                                ↓
                   ┌─────────────────────────────┐
                   │ Provedores de Dados Externos│
                   ├─────────────────────────────┤
                   │ • Yahoo Finance (yfinance)  │
                   │ • Dados B3 (opcoes.net)     │
                   │ • API Telegram (opcional)   │
                   └─────────────────────────────┘
```

### Fluxo de Dados: Requisição para Sinal

**Cenário: Usuário escaneia ticker PETR4**

```
1. Ação do Usuário no Frontend
   └─ Usuário clica em "Escanear PETR4"
      └─ Dispara: handleScan("PETR4", filters)

2. Chamada da API Frontend
   └─ fetch("http://localhost:3000/api/signals/scan", {
        method: "POST",
        body: JSON.stringify({ ticker: "PETR4", filters: {...} })
      })
      
3. Manipulador de Rota Next.js (src/app/api/signals/scan/route.ts)
   └─ Valida entrada (formato de ticker, etc)
      └─ Encaminha para backend Python:
         fetch("http://localhost:8000/signals/scan/PETR4", {...})

4. Processamento Backend FastAPI (main.py - /signals/scan/{ticker})
   a) Validação de Entrada
      └─ Verificação regex: ^[A-Z0-9]+\.SA$
      
   b) Recuperação de Dados (core_engine.py - analisar_ativo())
      └─ Verifica cache (Redis): cache_get_df("ohlcv:PETR4.SA:1d")
         └─ Se miss:
            ├─ Download do yfinance (6 meses de dados)
            ├─ Retry com backoff exponencial (3 tentativas: 1s, 2s, 4s)
            └─ Cache para Redis (300s TTL)
      
   c) Cálculo de Indicadores (indicators.py)
      └─ calcular_indicadores(df) calcula:
         ├─ RSI (período 14)
         ├─ MACD (12,26,9)
         ├─ Estocástico (14,3,3)
         ├─ Bandas de Bollinger (20,2)
         ├─ Cruzamentos EMA (8,21)
         ├─ Análise de volume
         ├─ Detecção de divergência
         ├─ Canais de preço
         ├─ Zonas de suporte/resistência
         └─ [19 gatilhos totais]
      
   d) Pontuação do Sinal (core_engine.py)
      └─ Para sinais BULLISH (G1-G11):
         ├─ Estocástico oversold? +1
         ├─ Momentum RSI? +1
         ├─ Cruzamento EMA? +1
         ├─ Cruzamento MACD? +1
         ├─ [11 gatilhos totais] +1 cada
         └─ Bônus de sessão (+0 a +3 conforme hora de mercado)
            └─ Score = soma de gatilhos + bônus de sessão
      
   e) Cálculo de Opções (options_math.py)
      └─ mes_vencimento_ideal(score) → seleciona vencimento
      └─ estimar_iv_historica(ticker, mes)
      └─ estimar_premio_otm(strike, iv, dte)
      
   f) Construção da Resposta
      └─ Retorna SignalObject:
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
      
   g) Persistência (se score >= min_score)
      └─ supabase.from("signals")
         .upsert(signal_data)
         └─ Subscrições Realtime notificadas
      
   h) Notificações (opcional)
      └─ Se telegram_token configurado:
         └─ enviar_telegram(signal) envia para chat

5. Resposta para Frontend
   └─ Resposta JSON com dados do Sinal
      └─ Frontend exibe em componente SignalCard
      └─ Atualiza estado local / Supabase Realtime
      └─ Gráficos atualizam (se análise)

6. Trabalhos em Segundo Plano (APScheduler)
   ├─ scan_job: A cada 30 min segunda-sexta 10:00-15:30
   │  └─ Escaneia todos os 29 tickers em ATIVOS_B3
   │     └─ Persiste sinais no Supabase
   │     └─ Envia notificações Telegram
   │
   └─ cleanup_job: Diariamente às 02:00 UTC
      └─ Deleta sinais com mais de 30 dias
```

### Arquitetura de Componentes

#### Componentes Frontend

**Layout & Navegação:**
- `layout.tsx` — Layout raiz com AuthProvider, fontes, metadados
- `SiteNav.tsx` — Barra de navegação com destaque de página ativa
- `TickerBar.tsx` — Fita de ticker ao vivo IBOV + top 8 ações
- `SiteFooter.tsx` — Rodapé com contato/links

**Gerenciamento de Sinais:**
- `SignalCard.tsx` — Exibição de sinal individual com gregas, IV, DTE
- `SignalsTable.tsx` — Tabela ordenável de sinais com filtros
- `LiveFeed.tsx` — Feed de sinais em tempo real com subscrições Supabase

**Analytics & Gráficos:**
- `EquityChart.tsx` — Gráfico de linha Recharts para curvas de equity
- `IVSurface.tsx` — Visualização Plotly 3D para dados de IV
- `VolatilitySkew.tsx` — Curva de volatility smile (Recharts)
- `PayoffChart.tsx` — Diagrama de payoff da estratégia

**Ferramentas de Estratégia:**
- `StrategiesBuilder.tsx` — UI interativa de configuração de estratégia
- `GreeksCalculator.tsx` — Cálculo dinâmico de gregas
- `PayoffChart.tsx` — Visualização de payoff por preço do ativo
- `RiskSimulator.tsx` — Análise de risco Monte Carlo
- `HedgingSimulator.tsx` — Cálculo de razão de hedge

**Gerenciamento de Portfólio:**
- `PortfolioDashboard.tsx` — Interface de paper trading
- `BacktestMetrics.tsx` — Exibição de KPIs de backtest (Sharpe, Drawdown, Win Rate)

**Primitivos de UI:**
- Localizados em `src/components/ui/` — Componentes base Radix UI + Tailwind

#### Módulos Backend

**Análise Principal (core_engine.py)**
```python
def analisar_ativo(ticker, interval="1d", df_provided=None):
    """
    Função de análise principal que:
    1. Baixa/cacheia dados OHLCV
    2. Calcula todos os indicadores técnicos
    3. Gera pontuações de sinal
    4. Retorna recomendações de opções
    """
```

**Indicadores Técnicos (indicators.py)**
```python
def calcular_indicadores(df):
    """
    Calcula 19 indicadores técnicos:
    • Momentum: RSI, MACD, Estocástico
    • Volatilidade: Bandas de Bollinger, ATR
    • Tendência: Cruzamentos EMA
    • Volume: Volume relativo
    • Avançado: Divergência, canais, zonas
    """
```

**Matemática de Opções (options_math.py)**
```python
def mes_vencimento_ideal(score):
    """Seleciona vencimento da opção baseado no score"""
    
def estimar_iv_historica(ticker, mes):
    """Calcula IV histórica para ticker"""
    
def estimar_premio_otm(strike, iv, dte):
    """Estima prêmio de opção OTM usando Black-Scholes"""
```

**Camada de Cache (cache.py)**
```python
def cache_get_df(key):
    """Redis GET com fallback para None"""
    
def cache_set_df(key, df, ttl=300):
    """Redis SET com TTL e serialização de DataFrame"""
```

**Provedores de Dados (data_providers.py)**
```python
def get_real_options_from_opcoes_net(ticker):
    """Busca chain real de opções B3 da API opcoes.net"""
```

**Configuração (config.py)**
```python
ATIVOS_B3 = [
    "PETR4.SA", "VALE3.SA", "USIM5.SA", ...  # 29 tickers
]

CONFIG = {
    "min_volume_diario": 100_000,
    "score_minimo": 5,
    "reentrada_min_dias": 1,
    # ... mais configurações
}
```

**Backtesting (backtest.py)**
```python
def backtest_strategy(ticker, signals, capital=10000):
    """
    Simula desempenho histórico de estratégia:
    • Entrada no ponto de geração de sinal
    • Saída em take-profit/stop-loss fixo
    • Retorna curva de equity, Sharpe, drawdown, win rate
    """
```

**Agendamento (main.py - APScheduler)**
```python
scheduler.add_job(
    scan_job,
    CronTrigger(day_of_week="mon-fri", hour="10-15", minute="*/30"),
    id="scan_job"
)
# Executa a cada 30 min segunda-sexta 10:00-15:30 (horário de mercado)

scheduler.add_job(
    cleanup_job,
    CronTrigger(hour=2, minute=0),  # 02:00 UTC
    id="cleanup_job"
)
# Executa diariamente, deleta sinais com mais de 30 dias
```

---

## Stack de Tecnologias

### Frontend

| Tecnologia | Versão | Propósito |
|-----------|--------|----------|
| **Next.js** | 16.1.6 | Framework React, SSR, rotas API |
| **React** | 19.2.3 | Biblioteca UI |
| **TypeScript** | 5.x | Segurança de tipo |
| **Tailwind CSS** | 3.4.17 | Estilo, design responsivo |
| **Radix UI** | Latest | Primitivos de componentes acessíveis |
| **Recharts** | 3.7.0 | Gráficos 2D (curvas de equity, análise) |
| **Plotly.js** | 3.5.1 | Visualização 3D (superfície IV) |
| **Supabase.js** | 2.106.2 | Cliente de banco de dados em tempo real |
| **Axios** | 1.13.4 | Cliente HTTP para chamadas de API |
| **SWR** | 2.4.0 | Fetching de dados com cache |
| **React Hot Toast** | 2.6.0 | Notificações toast |
| **Lucide React** | 0.563.0 | Biblioteca de ícones |
| **Class Variance Authority** | 0.7.1 | Variantes de componentes |
| **clsx** | 2.1.1 | Mesclagem condicional de classname |
| **Tailwind Merge** | 3.4.0 | Resolução de conflito de classe Tailwind |

**Fontes Customizadas:**
- DM Sans (texto do corpo)
- Lora (títulos)
- JetBrains Mono (código/números)

### Backend

| Tecnologia | Versão | Propósito |
|-----------|--------|----------|
| **FastAPI** | ≥0.100.0 | Framework web, API REST |
| **Python** | 3.11 | Linguagem |
| **Uvicorn** | ≥0.23.0 | Servidor ASGI |
| **Pydantic** | ≥2.0.0 | Validação de dados, serialização |
| **APScheduler** | ≥3.10.0 | Agendamento de trabalhos em background |
| **yfinance** | Latest | Recuperação de dados de mercado |
| **pandas** | Latest | Manipulação e análise de dados |
| **numpy** | Latest | Computação numérica |
| **scipy** | Latest | Computação científica (estimativa IV) |
| **redis** | ≥5.0.0 | Camada de cache |
| **supabase-py** | ≥2.0.0 | Cliente de banco de dados |
| **requests** | Latest | Requisições HTTP |
| **python-dotenv** | ≥1.0.0 | Gerenciamento de variáveis de ambiente |
| **python-multipart** | Latest | Tratamento de upload de arquivos |
| **email-validator** | Latest | Validação de email |
| **tqdm** | Latest | Barras de progresso |
| **colorama** | Latest | Cores de terminal |
| **tabulate** | Latest | Formatação de tabelas |

### Banco de Dados

| Tecnologia | Componente | Propósito |
|-----------|-----------|---------|
| **PostgreSQL** | Supabase | Armazenamento de dados primário |
| **Subscrições Realtime** | Supabase | Notificações push via WebSocket |
| **Row Level Security** | Supabase | Camada de autorização |
| **Redis** | Render | Cache distribuído |

### DevOps & Deployment

| Tecnologia | Propósito |
|-----------|---------|
| **Docker** | Containerização |
| **Docker Compose** | Orquestração local |
| **Vercel** | Hosting frontend (otimizado Next.js) |
| **Render** | Hosting backend (FastAPI + free tier) |
| **GitHub** | Controle de versão, CI/CD |
| **Supabase** | PostgreSQL gerenciado + Realtime |

### Ferramentas de Desenvolvimento

| Ferramenta | Propósito |
|-----------|---------|
| **ESLint** | Linting JavaScript/TypeScript |
| **TypeScript Compiler** | Verificação de tipo |
| **Tailwind CSS** | Framework de utilitários de estilo |
| **PostCSS** | Transformação CSS |
| **Autoprefixer** | Prefixos de vendor CSS |

---

## Funcionalidades

### ✅ Totalmente Implementadas

#### Varredura em Tempo Real
- Stream SSE ao vivo varrendo ~90 tickers B3 simultaneamente
- Visualização de progresso com percentual de conclusão
- Cálculo de 19 gatilhos técnicos por ticker
- Geração dinâmica de sinal com classificação por score
- Notificações push Telegram opcionais

#### Gerenciamento de Sinais
- Histórico de sinais persistente no Supabase (janela móvel 30 dias)
- Filtros multi-campo (ticker, tipo de sinal, setor, intervalo de data)
- Subscrições Supabase Realtime para atualizações de feed ao vivo
- Export CSV de histórico de sinais
- Configuração manual de filtros com persistência localStorage

#### Análise Histórica
- Motor de backtest completo com análise walk-forward
- Visualização de curva de equity com Recharts
- Métricas de desempenho: Sharpe ratio, drawdown máximo, win rate, retorno total
- Breakdown trade por trade
- Otimização de parâmetros de estratégia

#### Analytics de Volatilidade
- Visualização de curva volatility smile (2D)
- Renderização de superfície 3D IV (Plotly)
- Estimativa de IV histórica por mês de vencimento
- Comparação IV Call/Put
- Visualização de gregas (Delta, Gamma, Theta, Vega)

#### Biblioteca de Estratégias
- 17 estratégias de opções pré-configuradas:
  - **Básicas:** Long Call, Long Put, Covered Call, Protective Put
  - **Spreads:** Bull Call/Put Spread, Bear Call/Put Spread, Iron Condor
  - **Avançadas:** Long/Short Straddle, Long/Short Strangle, Butterfly
  - **Razão:** Call Ratio, Put Ratio
  - **Customizadas:** Estratégias definidas pelo usuário
- Calculadora de diagrama de payoff interativa
- Precificação baseada em gregas com Black-Scholes
- Visualização de razão Risco/Recompensa
- Simulação de estratégia ao vivo

#### Paper Trading
- Portfólio simulado com pontos de entrada de sinal real
- Mecânica de entrada/saída de posição com impacto de mercado
- Rastreamento de P&L em tempo real
- Visualização de composição de portfólio
- Histórico de trade com métricas detalhadas

#### Dados de Mercado
- Rastreamento de índice IBOV ao vivo
- Preços das top 8 ações em TickerBar
- Validação de horário de mercado (segunda-sexta 10:00-15:30 horário Brasília)
- Atualização de dados em tempo real

### ⚠️ Implementação Parcial

| Funcionalidade | Status | Bloqueador |
|----------|--------|-----------|
| **Aba de Precificação de Opções** | UI skeleton existe | Endpoint backend para chain real de opções necessário |
| **Alertas Proativos** | Regras podem ser definidas | Sistema de notificação backend não implementado |
| **Gregas ao Vivo** | Cálculo frontend feito | Dados de opções em tempo real necessário |

### ❌ Não Implementadas

| Funcionalidade | Impacto | Esforço Est. |
|----------|--------|------------|
| **Página de Login/Autenticação** | Alto — link de nav quebrado | 2–3 horas |
| **Middleware de Proteção de Rotas** | Alto — pré-requisito de auth | 2 horas |
| **Suite de Testes Automatizados** | Alto — zero cobertura | 3–5 dias |
| **Rate Limiting** | Médio — prevenção de DoS | 2 horas |
| **Observabilidade/Métricas** | Médio — visibilidade de produção | 1 dia |

---

## Estrutura do Projeto

```
options-signals/
│
├── Frontend (Next.js)
│   ├── src/
│   │   ├── app/                          # Páginas Next.js App Router
│   │   │   ├── page.tsx                  # Dashboard home
│   │   │   ├── layout.tsx                # Layout raiz com provedores
│   │   │   ├── error.tsx                 # Error boundary
│   │   │   ├── global-error.tsx          # Manipulador de erro global
│   │   │   │
│   │   │   ├── scanner/                  # Scanner em tempo real
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── signals/                  # Histórico de sinais & filtros
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── analytics/                # Análise de volatilidade
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── backtest/                 # Simulação histórica
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── estrategias/              # Biblioteca de estratégias
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── portfolio/                # Paper trading
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── alerts/                   # Gerenciamento de alertas
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── api/                      # Rotas API Next.js
│   │   │   │   ├── signals/
│   │   │   │   ├── backtest/
│   │   │   │   ├── analytics/
│   │   │   │   └── health/
│   │   │   │
│   │   │   └── globals.css               # Estilos globais + Tailwind
│   │   │
│   │   ├── components/                   # Componentes React reutilizáveis
│   │   │   ├── SignalCard.tsx            # Card de exibição de sinal
│   │   │   ├── SignalsTable.tsx          # Tabela de sinais
│   │   │   ├── LiveFeed.tsx              # Feed em tempo real
│   │   │   ├── MarketWidget.tsx          # Exibição de dados de mercado
│   │   │   ├── EquityChart.tsx           # Curva de equity (Recharts)
│   │   │   ├── IVSurface.tsx             # Superfície 3D IV (Plotly)
│   │   │   ├── VolatilitySkew.tsx        # Vol smile (Recharts)
│   │   │   ├── PayoffChart.tsx           # Payoff de estratégia
│   │   │   ├── StrategiesBuilder.tsx     # UI de estratégia
│   │   │   ├── GreeksCalculator.tsx      # Cálculo de gregas
│   │   │   ├── PortfolioDashboard.tsx    # UI de paper trading
│   │   │   ├── BacktestMetrics.tsx       # KPIs de backtest
│   │   │   ├── SiteNav.tsx               # Navegação
│   │   │   ├── TickerBar.tsx             # Fita de ticker ao vivo
│   │   │   ├── SiteFooter.tsx            # Rodapé
│   │   │   ├── RiskBadge.tsx             # Indicador de risco
│   │   │   ├── RiskSimulator.tsx         # Análise de risco
│   │   │   ├── HedgingSimulator.tsx      # Cálculo de hedge
│   │   │   ├── CollapseShell.tsx         # Container colapsável
│   │   │   └── ui/                       # Primitivos Radix UI
│   │   │       ├── button.tsx
│   │   │       ├── card.tsx
│   │   │       ├── select.tsx
│   │   │       ├── input.tsx
│   │   │       └── [mais]
│   │   │
│   │   ├── lib/                          # Funções utilitárias
│   │   │   ├── api.ts                    # Cliente de API backend (Axios)
│   │   │   ├── black-scholes.ts          # Precificação de opções
│   │   │   ├── monte-carlo.ts            # Simulação de risco
│   │   │   ├── supabase.ts               # Cliente Supabase
│   │   │   ├── supabase-auth.ts          # Utilitários de auth
│   │   │   ├── supabase-db.ts            # Queries de DB
│   │   │   ├── config.ts                 # Constantes
│   │   │   └── format.ts                 # Helpers de formatação
│   │   │
│   │   ├── context/                      # React Context
│   │   │   └── AuthContext.tsx           # Estado de auth global
│   │   │
│   │   ├── hooks/                        # Custom hooks
│   │   │   └── useSignals.ts             # Fetching de dados de sinais
│   │   │
│   │   └── types/                        # Tipos TypeScript
│   │       ├── signals.ts
│   │       ├── strategies.ts
│   │       └── [mais]
│   │
│   ├── package.json                      # Dependências + scripts
│   ├── tsconfig.json                     # Configuração TypeScript
│   ├── tailwind.config.js                # Configuração tema Tailwind
│   ├── postcss.config.js                 # Configuração PostCSS
│   ├── eslint.config.mjs                 # Regras ESLint
│   └── .env.local                        # Variáveis de ambiente
│
├── Backend (FastAPI + Python)
│   ├── main.py                           # App FastAPI, rotas
│   ├── core_engine.py                    # Motor de análise de sinais
│   ├── indicators.py                     # Indicadores técnicos
│   ├── options_math.py                   # Gregas & precificação de opções
│   ├── backtest.py                       # Motor de backtesting
│   ├── config.py                         # Tickers B3, parâmetros
│   ├── cache.py                          # Camada de caching Redis
│   ├── data_providers.py                 # Fontes de dados de mercado
│   ├── scanner_opcoes_b3_v3.py           # Integração Telegram
│   │
│   ├── requirements.txt                  # Dependências Python
│   ├── .env                              # Variáveis de ambiente
│   └── Dockerfile                        # Imagem de container
│
├── Infrastructure
│   ├── docker-compose.yml                # Stack local
│   ├── .dockerignore                     # Exclusões Docker
│   ├── .gitignore                        # Exclusões Git
│   └── render.yaml                       # Configuração deployment Render
│
├── Documentation
│   ├── docs/
│   │   ├── ESTADO_ATUAL.md              # Estado atual do projeto
│   │   ├── REPORT_COMPLETO.md           # Relatório de auditoria completo
│   │   ├── ARQUITETURA_PRODUCAO.md      # Arquitetura de produção
│   │   ├── QUICKSTART.md                # Guia de setup
│   │   ├── ESTRATEGIAS_OPCOES_B3.md     # Gatilhos de sinais explicados
│   │   ├── MONTAGEM_DE_SINAL_B3.md      # Pipeline de sinais
│   │   ├── SUPABASE_SETUP.md            # Schema de banco de dados
│   │   ├── CHANGELOG.md                 # Histórico de versões
│   │   └── LINKS_PRODUCAO.md            # Recursos de produção
│   │
│   ├── gregas/                           # Documentação de estratégias
│   │   ├── RESUMO_EXECUTIVO.md
│   │   ├── fase2_estrategias_detalhado.md
│   │   └── plano_desenvolvimento_gregas.md
│   │
│   └── README.md                         # Este arquivo
│
└── Configuration
    ├── tsconfig.json                     # Configuração TypeScript
    ├── next.config.js                    # Configuração Next.js
    ├── tailwind.config.js                # Configuração Tailwind
    └── .claude/                          # Configurações Claude Code
        └── settings.local.json
```

---

## Referência da API

### URL Base
```
http://localhost:8000
```

### Autenticação
Atualmente **nenhuma autenticação necessária** nos endpoints. Supabase Auth será integrada na v2.2.

### Endpoints

#### 1. Health Check
```http
GET /health
```

**Resposta:**
```json
{
  "status": "ok",
  "version": "2.1",
  "timestamp": "2026-05-27T15:30:00Z",
  "redis": "connected"
}
```

#### 2. Dados de Mercado
```http
GET /market
```

Retorna IBOV e preços de 8 ações principais (cache 60 segundos).

**Resposta:**
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

#### 3. Escanear Ticker Único
```http
POST /signals/scan/{ticker}
```

Escaneia um único ticker e retorna sinal se condições atendidas.

**Parâmetros de Path:**
- `ticker` (string, obrigatório) — Formato ticker B3 (ex: `PETR4.SA`)

**Parâmetros de Query:**
- `min_score` (int, padrão: 5) — Score mínimo de sinal
- `min_volume` (int, padrão: 100000) — Volume diário mínimo

**Resposta:**
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

#### 4. Escanear Stream (SSE)
```http
GET /signals/scan/stream
```

Stream Server-Sent Events varrendo todos os tickers B3. Mantenha conexão aberta por ~3–5 minutos.

**Parâmetros de Query:**
- `min_score` (int, padrão: 5)
- `limit` (int, padrão: 100)

**Resposta (Server-Sent Events):**
```
data: {"ticker":"PETR4.SA","progress":"1/90"}
data: {"ticker":"VALE3.SA","progress":"2/90","sinal":{...}}
...
```

#### 5. Histórico de Sinais
```http
GET /signals
```

Recupera sinais históricos com filtros.

**Parâmetros de Query:**
- `ticker` (string, opcional) — Filtrar por ticker
- `tipo_sinal` (string, opcional) — "ALTA" ou "BAIXA"
- `limit` (int, padrão: 50)
- `offset` (int, padrão: 0)

**Resposta:**
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

#### 6. Backtesting de Estratégia
```http
POST /backtest/run
```

Simula desempenho histórico de estratégia.

**Corpo da Requisição:**
```json
{
  "ticker": "PETR4.SA",
  "strategy": "long_call",
  "entry_score": 5,
  "initial_capital": 10000,
  "position_size": 0.1
}
```

**Resposta:**
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

#### 7. Analytics de Volatilidade
```http
GET /signals/analytics/{ticker}
```

Obter dados de volatilidade e IV para um ticker.

**Parâmetros de Path:**
- `ticker` (string, obrigatório) — Ticker B3

**Resposta:**
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
    "ago": 0.26
  },
  "volatility_smile": [
    {"strike": 26.0, "iv": 0.28},
    {"strike": 28.0, "iv": 0.24},
    {"strike": 30.0, "iv": 0.26}
  ]
}
```

#### 8. Configuração de Telegram
```http
GET /config/telegram
POST /config/telegram
```

Obter ou atualizar configuração de bot Telegram.

**Corpo POST:**
```json
{
  "token": "123:ABC...",
  "chat_id": "123456789"
}
```

**Resposta:**
```json
{
  "configured": true,
  "chat_id": "123456789"
}
```

### Tratamento de Erros

Todos os erros retornam códigos HTTP padrão com detalhes JSON:

```json
{
  "detail": "Formato de ticker inválido. Esperado: XXX9.SA"
}
```

**Códigos de Status Comuns:**
- `400` — Requisição inválida (parâmetros inválidos)
- `404` — Recurso não encontrado
- `500` — Erro do servidor
- `503` — Serviço indisponível (Redis/Supabase down)

### Rate Limiting

Atualmente **não aplicado**. Será adicionado na v2.3.

---

## Desenvolvimento

### Desenvolvimento do Frontend

**Iniciar servidor de dev:**
```bash
npm run dev
```

**Build para produção:**
```bash
npm run build
npm start
```

**Linting:**
```bash
npm run lint
```

**Verificação de tipo:**
```bash
tsc --noEmit
```

### Desenvolvimento do Backend

**Iniciar com auto-reload:**
```bash
uvicorn main:app --reload --port 8000
```

**Ver documentação da API:**
```
http://localhost:8000/docs
```

**Executar trabalhos em background:**
Trabalhos iniciam automaticamente com APScheduler. Monitor nos logs:
```
2026-05-27 15:30:00 INFO scan_job: Varrendo 29 tickers...
2026-05-27 15:35:00 INFO scan_job: Encontrados 12 sinais
```

### Testes

Atualmente **0% cobertura de testes**. Adicionar testes é prioridade v2.3.

**Estrutura de teste planejada:**
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

## Problemas Conhecidos & Roadmap

### 🔴 Bugs de Alta Prioridade

**Backend:**
1. **Persistência de Config Telegram** — Configurações perdidas em restart de servidor
   - Fix: Persistir no Supabase em vez de arquivo JSON temporário
   
2. **Edge Cases de Timezone** — `dentro_horario_pregao()` usa `datetime.now()` 
   - Fix: Usar `pytz.timezone('America/Sao_Paulo')`
   
3. **Colisão de Chave de Cache** — Cache de backtest não inclui interval/period
   - Fix: `f"ohlcv:{ticker}:{interval}:{period}"`
   
4. **Reconexão Redis** — Desativada após primeira falha
   - Fix: Implementar lógica retry com backoff exponencial

**Frontend:**
1. **Race Condition no Unmount SSE** — Manipulador de mensagem escreve em componente desmontado
   - Fix: Adicionar check `if (!mountedRef.current) return`
   
2. **Expiração de Token** — Tokens Supabase auth expiram silenciosamente após 1 hora
   - Fix: Implementar `onAuthStateChange()` refresh de token
   
3. **Bounds Check Faltando** — `SignalCard.tsx` acessa `meses[signal.mes_venc - 1]`
   - Fix: Guard com bounds check
   
4. **Atraso Artificial** — Delay fake de 400ms em página de estratégias
   - Fix: Remover artifact de timeout

### 🟡 Prioridade Média

- Adicionar rate limiting ao backend
- Implementar observabilidade (logs, métricas, tracing)
- Adicionar suite de testes automatizados
- Implementar sistema de autenticação

### 🟢 Roadmap

**v2.2 (Próximo):**
- Implementar página `/login` com Supabase Auth
- Adicionar middleware de proteção de rota
- Corrigir todos os bugs de alta prioridade
- Adicionar rate limiting

**v2.3:**
- Estabelecer suite de testes automatizados (Jest + pytest)
- Adicionar observabilidade/monitoring
- Implementar notificações WebSocket para alertas
- Melhorar performance com otimização de queries

**v3.0:**
- Suporte multi-usuário com autenticação adequada
- Integração real com API de broker
- Backtester avançado com simulação Monte Carlo
- Capacidade de negociação ao vivo

---

## Deployment

### Pré-requisitos

- Conta GitHub com acesso push ao repositório
- Conta Vercel (free tier suficiente)
- Conta Render.com (free tier suficiente)
- Projeto Supabase criado

### Deployment do Frontend (Vercel)

1. **Conectar repositório:**
   - Vá para [vercel.com](https://vercel.com)
   - Importe repositório GitHub
   - Selecione diretório raiz (ou especifique `./`)

2. **Definir variáveis de ambiente:**
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` (URL backend de produção)

3. **Fazer deploy:**
   ```bash
   git push origin main
   ```
   Vercel auto-deploy em push.

**URL de Produção:** [https://options-signals.vercel.app](https://options-signals.vercel.app)

### Deployment do Backend (Render.com)

1. **Criar novo Web Service:**
   - Conectar repositório GitHub
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:app --host 0.0.0.0 --port ${PORT}`

2. **Definir variáveis de ambiente:**
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `ALLOWED_ORIGINS` (incluir URL frontend Vercel)
   - `REDIS_URL` (se usar Redis)
   - `TELEGRAM_BOT_TOKEN` (opcional)
   - `TELEGRAM_CHAT_ID` (opcional)

3. **Fazer deploy:**
   - Disparar deploy manual ou push para main

**URL de Produção:** [https://options-signals-b79i.onrender.com](https://options-signals-b79i.onrender.com)

**Nota:** Free tier tem delays de cold-start (~30s). Upgrade para Pro para melhor performance.

### Setup de Banco de Dados (Supabase)

1. Criar projeto PostgreSQL
2. Executar migration no editor SQL:
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
3. Habilitar Row Level Security (RLS)
4. Habilitar Realtime para tabela `signals`

---

## Solução de Problemas

### "Incapaz de conectar ao backend"

**Sintomas:** Erros "Connection refused" ou timeout

**Diagnóstico:**
1. Verificar se `NEXT_PUBLIC_API_URL` corresponde à URL do backend
2. Verificar se backend está rodando: `curl http://localhost:8000/health`
3. Verificar CORS: backend deve logar validação `ALLOWED_ORIGINS`
4. Se Render free tier: backend pode estar cold (esperar 30 segundos)

**Fix:**
```bash
# Desenvolvimento local
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

# Produção
NEXT_PUBLIC_API_URL=https://options-signals-b79i.onrender.com npm run build
```

### "Nenhum sinal encontrado"

**Sintomas:** Scanner mostra 0 sinais

**Diagnóstico:**
1. Verificar horário de mercado: segunda-sexta, 10:00–15:30 horário Brasília (UTC-3)
2. Verificar threshold de score: mínimo padrão é 5
3. Verificar se mercado B3 está aberto (não feriado)
4. Verificar filtro de volume: ações devem ter >100k volume diário

**Fix:**
Reduzir threshold de score mínimo nos filtros do scanner na UI.

### "Falha de conexão Redis"

**Sintomas:** Backend logs mostram "Redis unavailable"

**Diagnóstico:**
1. Verificar se Redis está rodando: `redis-cli ping` deve retornar `PONG`
2. Verificar Redis URL em ambiente: `echo $REDIS_URL`

**Fix:**
```bash
# Se usar Docker
docker-compose up redis

# Se instalado localmente
redis-server
```

### "Portfólio de paper trading não está salvando"

**Sintomas:** Refrescar página perde portfólio

**Diagnóstico:**
Portfólio usa browser `localStorage`, não backend persistente

**Fix:**
Workaround: Exportar portfólio para CSV antes de fechar navegador

---

## Contribuindo

Contribuições bem-vindas! Antes de começar:

1. **Verificar issues atuais:** [GitHub Issues](https://github.com/GabrielSalazar/options-signals/issues)
2. **Revisar relatório de auditoria:** [REPORT_COMPLETO.md](./docs/REPORT_COMPLETO.md)
3. **Criar issue para mudanças maiores:** Discutir abordagem antes da implementação
4. **Seguir convenções:**
   - TypeScript: strict mode, tipos explícitos
   - Python: type hints com validação Pydantic
   - Commits: mensagens descritivas com referências de issue
5. **Testar localmente:** Executar servidor dev e testar mudanças UI/API

**Padrões de Qualidade de Código:**
- Frontend: ESLint (preset Next.js), TypeScript strict mode
- Backend: Type hints obrigatórios, validação Pydantic para inputs
- Ambos: Sem console.log em código de produção, mensagens de erro significativas

---

## Licença

Proprietária. Não para redistribuição sem permissão escrita explícita.

---

## Suporte & Contato

- **Issues/Bugs:** [GitHub Issues](https://github.com/GabrielSalazar/options-signals/issues)
- **Email:** [gsalazar93@gmail.com](mailto:gsalazar93@gmail.com)
- **Telegram:** [@OptionsSignals](https://t.me/optionssignals) (se ativado)
- **Status de Produção:** [https://options-signals.vercel.app](https://options-signals.vercel.app)

---

## Recursos Adicionais

**Documentação:**
- [ESTADO_ATUAL.md](./docs/ESTADO_ATUAL.md) — Estado atual do projeto e páginas
- [REPORT_COMPLETO.md](./docs/REPORT_COMPLETO.md) — Auditoria técnica completa
- [ARQUITETURA_PRODUCAO.md](./docs/ARQUITETURA_PRODUCAO.md) — Arquitetura de produção
- [ESTRATEGIAS_OPCOES_B3.md](./docs/ESTRATEGIAS_OPCOES_B3.md) — Gatilhos de sinais explicados
- [QUICKSTART.md](./docs/QUICKSTART.md) — Guia de setup

**Externo:**
- [Documentação Next.js](https://nextjs.org/docs)
- [Guia FastAPI](https://fastapi.tiangolo.com)
- [Docs Supabase](https://supabase.com/docs)
- [Referência Tailwind CSS](https://tailwindcss.com/docs)
- [Galeria Recharts](https://recharts.org)
- [Documentação Plotly.js](https://plotly.com/javascript)

---

**Última Atualização:** 2026-05-27  
**Versão:** 2.1  
**Mantenedor:** Gabriel Salazar  
**Repositório:** [https://github.com/GabrielSalazar/options-signals](https://github.com/GabrielSalazar/options-signals)

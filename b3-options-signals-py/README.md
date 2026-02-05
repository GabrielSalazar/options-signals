# 📊 B3 Options Signals

> **Sistema Profissional de Análise e Sinais de Opções da B3**
> 
> Plataforma completa para identificação de oportunidades em opções brasileiras utilizando dados reais, análise técnica avançada e backtesting vetorizado.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Funcionalidades](#-funcionalidades)
- [Tecnologias](#-tecnologias)
- [Arquitetura](#-arquitetura)
- [Algoritmos Centrais](#-algoritmos-centrais)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [API Endpoints](#-api-endpoints)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Testes](#-testes)
- [Deploy](#-deploy)
- [Contribuindo](#-contribuindo)

---

## 🎯 Visão Geral

O **B3 Options Signals** é um sistema profissional de análise quantitativa para o mercado de opções brasileiro. Utilizando **dados reais** de múltiplas fontes (Yahoo Finance, StatusInvest), o sistema identifica automaticamente oportunidades de trading baseadas em:

- **20+ estratégias de opções** (Iron Condor, Butterflies, Straddles, Spreads)
- **Análise técnica avançada** (RSI, MACD, Bollinger Bands, Volume Profile)
- **Precificação Black-Scholes** para cálculo de Greeks (Delta, Gamma, Theta, Vega)
- **Backtesting vetorizado** com métricas profissionais (Sharpe, Sortino, Drawdown)
- **Alertas em tempo real** via Telegram

### Diferenciais

✅ **100% Dados Reais** - Sem mocks, integração direta com fontes confiáveis  
✅ **Cache Redis** - Fallback de 15 minutos para resiliência  
✅ **Processamento Vetorizado** - Alta performance com Pandas/Numpy  
✅ **API Assíncrona** - FastAPI com suporte a milhares de requisições/segundo  
✅ **Métricas Profissionais** - Integração com QuantStats para análise institucional  

---

## 🚀 Funcionalidades

### 1. Scanner de Oportunidades em Tempo Real

Escaneia ativos da B3 aplicando múltiplas estratégias simultaneamente:

```python
# Exemplo de resposta do scanner
{
  "ticker": "PETRP317",
  "strategy": "Cash Secured Put",
  "confidence_score": 89,
  "risk_flag": "🟢 SEGURO",
  "spot_price": 37.00,
  "legs": [{
    "action": "SELL",
    "type": "PUT",
    "strike": 31.70,
    "price": 0.10,
    "delta": -0.35
  }],
  "technicals": {
    "rsi": 68.5,
    "iv_rank": 72,
    "volume_ratio": 1.8
  }
}
```

### 2. Backtesting Vetorizado

Simula estratégias com dados históricos reais:

- **Período configurável** (7 dias até 5 anos)
- **Capital inicial customizável**
- **Métricas profissionais**: Sharpe Ratio, Sortino Ratio, Max Drawdown, Win Rate
- **Gráficos de equity curve** e drawdown

### 3. Análise Técnica Avançada

Calcula automaticamente:

- **RSI** (Relative Strength Index) - Identificação de sobrecompra/sobrevenda
- **MACD** (Moving Average Convergence Divergence) - Sinais de momentum
- **Bollinger Bands** - Volatilidade e squeeze patterns
- **SMAs** (20, 50, 200 períodos) - Tendências de longo prazo
- **Volume Profile** - Análise de liquidez

### 4. Sistema de Classificação de Risco

Cada sinal recebe:

- **Risk Flag**: 🟢 SEGURO | 🟡 MODERADO | 🚨 ALTO RISCO
- **Confidence Score**: 0-100 baseado em 7 critérios quantitativos
- **Max Loss**: Perda máxima teórica da estratégia

### 5. Alertas Telegram

Notificações automáticas a cada 5 minutos com:

- Sinais de alta confiança (>75%)
- Formatação rica com emojis e métricas
- Timestamp e validade do sinal

---

## 🛠 Tecnologias

### Backend (Python)

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Python** | 3.10+ | Linguagem principal |
| **FastAPI** | 0.100+ | Framework web assíncrono |
| **Uvicorn** | Latest | Servidor ASGI |
| **Pandas** | <2.2 | Processamento vetorizado de dados |
| **Numpy** | <2.0 | Computação numérica |
| **PandasTA** | Latest | Indicadores técnicos |
| **QuantStats** | Latest | Métricas de backtesting |
| **yfinance** | Latest | Dados históricos Yahoo Finance |
| **BeautifulSoup4** | 4.12+ | Web scraping (StatusInvest) |
| **Redis** | 5.0+ | Cache e fallback |
| **APScheduler** | 3.10+ | Agendamento de tarefas |
| **py_vollib** | Latest | Precificação Black-Scholes |
| **httpx** | Latest | Cliente HTTP assíncrono |
| **SQLAlchemy** | Latest | ORM para persistência |

### Frontend (Next.js)

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| **Next.js** | 16.1+ | Framework React |
| **React** | 19.2+ | Biblioteca UI |
| **TypeScript** | 5+ | Type safety |
| **Tailwind CSS** | 3.4+ | Estilização |
| **Shadcn/UI** | Latest | Componentes |
| **Recharts** | 3.7+ | Gráficos |
| **Axios** | 1.13+ | Cliente HTTP |
| **SWR** | Latest | Data fetching |

### Infraestrutura

- **Docker** & **Docker Compose** - Containerização
- **Redis** - Cache distribuído
- **SQLite** - Banco de dados (dev)
- **PostgreSQL** - Banco de dados (prod)

---

## 🏗 Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Scanner  │  │ Backtest │  │Strategies│  │  Alerts  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─────────────┼─────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                          │ HTTP/REST
        ┌─────────────────┴─────────────────┐
        │      BACKEND (FastAPI)            │
        │  ┌──────────────────────────┐    │
        │  │   API Layer (Routers)    │    │
        │  └──────────┬───────────────┘    │
        │             │                     │
        │  ┌──────────┴───────────────┐   │
        │  │  Business Logic Layer    │   │
        │  │  ┌────────┐  ┌─────────┐ │   │
        │  │  │Scanner │  │Backtester│ │   │
        │  │  └───┬────┘  └────┬────┘ │   │
        │  └──────┼────────────┼──────┘   │
        │         │            │           │
        │  ┌──────┴────────────┴──────┐   │
        │  │   Data Layer (app/data)  │   │
        │  │  ┌──────────────────┐    │   │
        │  │  │  B3RealData      │    │   │
        │  │  │  - StatusInvest  │    │   │
        │  │  │  - Yahoo Finance │    │   │
        │  │  └──────────────────┘    │   │
        │  │  ┌──────────────────┐    │   │
        │  │  │ TechnicalIndic.  │    │   │
        │  │  │  - RSI/MACD      │    │   │
        │  │  │  - Bollinger     │    │   │
        │  │  └──────────────────┘    │   │
        │  └──────────┬───────────────┘   │
        └─────────────┼───────────────────┘
                      │
        ┌─────────────┴───────────────┐
        │    CACHE LAYER (Redis)      │
        │  - Cotações (TTL 15min)     │
        │  - Cadeias (TTL 15min)      │
        │  - Indicadores (TTL 5min)   │
        └─────────────────────────────┘
```

### Fluxo de Dados

1. **Frontend** faz requisição para `/signals/scan/PETR4`
2. **API Router** recebe e valida a requisição
3. **Scanner** orquestra a busca de dados:
   - Tenta buscar do **Redis Cache**
   - Se miss, busca de **Yahoo Finance** / **StatusInvest**
   - Armazena no cache para próximas requisições
4. **TechnicalIndicators** calcula RSI, MACD, etc.
5. **Strategies** aplicam lógica de cada estratégia
6. **Filters** classificam por risco e score
7. **Response** retorna sinais filtrados ao frontend

---

## 🧮 Algoritmos Centrais

### 1. Precificação Black-Scholes

Utilizado para calcular preços teóricos e Greeks:

```python
# Fórmula Black-Scholes para Call
d1 = (ln(S/K) + (r + σ²/2)T) / (σ√T)
d2 = d1 - σ√T
C = S·N(d1) - K·e^(-rT)·N(d2)

# Greeks
Delta = N(d1)
Gamma = φ(d1) / (S·σ·√T)
Theta = -(S·φ(d1)·σ)/(2√T) - r·K·e^(-rT)·N(d2)
Vega = S·φ(d1)·√T
```

**Implementação**: `py_vollib` para cálculos otimizados

### 2. Processamento Vetorizado

Todas as estratégias são implementadas usando operações vetorizadas do Pandas:

```python
# Exemplo: Identificação de Iron Condor
df['call_otm'] = df['strike'] > df['spot'] * 1.05
df['put_otm'] = df['strike'] < df['spot'] * 0.95
df['high_iv'] = df['iv'] > df['iv'].quantile(0.7)

# Filtra em uma operação vetorizada
signals = df[
    (df['call_otm'] | df['put_otm']) & 
    df['high_iv'] & 
    (df['volume'] > 100)
]
```

**Performance**: Processa 10.000+ opções em <100ms

### 3. Backtesting Vetorizado

Simula trades sem loops:

```python
# Calcula retornos diários
returns = df['Close'].pct_change()

# Aplica estratégia vetorizada
positions = strategy.generate_signals(df)
strategy_returns = positions.shift(1) * returns

# Métricas via QuantStats
sharpe = qs.stats.sharpe(strategy_returns)
sortino = qs.stats.sortino(strategy_returns)
max_dd = qs.stats.max_drawdown(strategy_returns)
```

### 4. Sistema de Scoring

Cada sinal recebe score de 0-100 baseado em:

```python
score = 0
if rsi > 65: score += 25      # Put favorável
if iv_rank > 70: score += 20  # Volatilidade cara
if volume_ratio > 1.5: score += 15  # Liquidez
if delta in [-0.3, -0.4]: score += 15  # Delta ideal
if spread < 0.05: score += 10  # Spread apertado
if open_interest > 500: score += 10  # OI saudável
if trend == 'confirmed': score += 5  # Tendência

return min(score, 100)
```

### 5. Classificação de Risco

```python
RISK_MAP = {
    'naked_call': '🚨 ILIMITADO',
    'naked_put': '🚨 ALTO',
    'cash_secured_put': '🟢 SEGURO',
    'covered_call': '🟢 SEGURO',
    'iron_condor': '🟢 LIMITADO',
    'butterfly': '🟢 LIMITADO',
    'straddle': '🟡 MODERADO',
    'strangle': '🟡 MODERADO'
}
```

---

## 📦 Instalação

### Pré-requisitos

- **Python 3.10+**
- **Node.js 18+** (para frontend)
- **Redis** (opcional, para cache)
- **Git**

### 1. Clone o Repositório

```bash
git clone https://github.com/GabrielSalazar/options-signals.git
cd options-signals
```

### 2. Backend (Python)

```bash
cd b3-options-signals-py

# Crie ambiente virtual
python -m venv venv

# Ative o ambiente
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale dependências
pip install -r requirements.txt
```

### 3. Frontend (Next.js)

```bash
cd b3-options-signals-web

# Instale dependências
npm install
```

### 4. Configuração

Crie arquivo `.env` no backend:

```env
# Telegram (opcional)
TELEGRAM_BOT_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id

# Redis (opcional)
REDIS_URL=redis://localhost:6379
REDIS_ENABLED=true

# API
ALLOWED_ORIGINS=http://localhost:3000
```

### 5. Docker (Opcional)

```bash
# Suba todos os serviços (backend + frontend + redis)
docker-compose up --build
```

---

## 🎮 Uso

### Desenvolvimento Local

**Backend**:
```bash
cd b3-options-signals-py
uvicorn app.main:app --reload --port 8000
```

**Frontend**:
```bash
cd b3-options-signals-web
npm run dev
```

Acesse:
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Testes

```bash
# Backend
cd b3-options-signals-py

# Teste integração com dados reais
python test_real_data.py

# Teste scanner
python test_strategies.py

# Teste Telegram
python test_telegram.py
```

---

## 🔌 API Endpoints

### Signals & Scanning

#### `POST /signals/scan/{ticker}`
Escaneia um ticker específico.

**Request**:
```bash
curl -X POST http://localhost:8000/signals/scan/PETR4
```

**Response**:
```json
{
  "message": "Scan completed for PETR4",
  "signals_found": 3,
  "results": [...]
}
```

#### `GET /signals/strategies`
Lista todas as estratégias disponíveis.

#### `GET /signals/history?limit=100`
Retorna histórico de sinais.

### Backtesting

#### `POST /backtest/run`
Executa backtest de uma estratégia.

**Request**:
```json
{
  "ticker": "PETR4",
  "strategy_name": "Reversão por IFR (RSI)",
  "days": 252,
  "initial_capital": 10000.0
}
```

**Response**:
```json
{
  "message": "Backtest completed successfully",
  "metrics": {
    "sharpe_ratio": 1.85,
    "sortino_ratio": 2.12,
    "max_drawdown": -12.5,
    "win_rate": 68.5,
    "total_return": 45.2
  }
}
```

### Health & Monitoring

#### `GET /health`
Status do sistema e fontes de dados.

```json
{
  "status": "healthy",
  "data_source": "real",
  "sources": {
    "yahoo": "ok",
    "statusinvest": "ok",
    "redis": "ok"
  }
}
```

---

## 📁 Estrutura do Projeto

```
b3-options-signals/
├── b3-options-signals-py/          # Backend Python
│   ├── app/
│   │   ├── core/                   # Lógica central
│   │   │   ├── backtester.py       # Engine de backtesting
│   │   │   ├── strategies_vectorized.py  # 20+ estratégias
│   │   │   ├── risk_classifier.py  # Classificação de risco
│   │   │   └── models.py           # Modelos de dados
│   │   ├── data/                   # Camada de dados reais
│   │   │   ├── real_time.py        # StatusInvest + Yahoo
│   │   │   ├── technicals.py       # Indicadores técnicos
│   │   │   └── cache.py            # Redis cache
│   │   ├── services/               # Serviços de negócio
│   │   │   ├── scanner.py          # Scanner de oportunidades
│   │   │   ├── math_service.py     # Black-Scholes
│   │   │   └── crud.py             # Operações DB
│   │   └── routers/                # API endpoints
│   │       ├── signals.py          # Sinais e scanning
│   │       ├── backtest.py         # Backtesting
│   │       └── options.py          # Pricing e Greeks
│   ├── tests/                      # Testes
│   ├── requirements.txt            # Dependências Python
│   └── Dockerfile                  # Container backend
│
├── b3-options-signals-web/         # Frontend Next.js
│   ├── src/
│   │   ├── app/                    # Páginas (App Router)
│   │   │   ├── page.tsx            # Dashboard
│   │   │   ├── scanner/            # Scanner UI
│   │   │   ├── backtest/           # Backtest UI
│   │   │   └── strategies/         # Biblioteca estratégias
│   │   ├── components/             # Componentes React
│   │   │   ├── ui/                 # Shadcn/UI
│   │   │   ├── SignalCard.tsx      # Card de sinal
│   │   │   ├── BacktestMetrics.tsx # Métricas backtest
│   │   │   └── EquityChart.tsx     # Gráfico equity
│   │   └── lib/                    # Utilitários
│   ├── package.json                # Dependências Node
│   └── Dockerfile                  # Container frontend
│
└── docker-compose.yml              # Orquestração completa
```

---

## 🧪 Testes

### Validação de Dados Reais

```bash
python test_real_data.py
```

Testa:
- ✅ Conexão Yahoo Finance
- ✅ Busca de cotações
- ✅ Cadeia de opções
- ✅ Indicadores técnicos
- ✅ Cache Redis
- ✅ Volume de opções

### Testes de Estratégias

```bash
python test_strategies.py
```

Valida todas as 20+ estratégias implementadas.

---

## 🚢 Deploy

### Railway (Backend)

```bash
railway init
railway env:set REDIS_URL=redis://...
railway up
```

### Vercel (Frontend)

```bash
vercel
vercel env:add NEXT_PUBLIC_API_URL
vercel --prod
```

### Docker Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

### Convenções de Commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `refactor:` Refatoração de código
- `test:` Testes
- `chore:` Manutenção

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👨‍💻 Autor

**Gabriel Salazar**

- GitHub: [@GabrielSalazar](https://github.com/GabrielSalazar)
- LinkedIn: [Gabriel Salazar](https://linkedin.com/in/gabrielsalazar)

---

## 🙏 Agradecimentos

- **QuantStats** - Métricas profissionais de backtesting
- **PandasTA** - Biblioteca de indicadores técnicos
- **FastAPI** - Framework web moderno
- **Next.js** - Framework React de produção
- Comunidade B3 e traders brasileiros

---

## ⚠️ Disclaimer

Este sistema é fornecido apenas para fins educacionais e de pesquisa. **Não constitui recomendação de investimento**. O mercado de opções envolve riscos significativos. Sempre consulte um profissional certificado antes de operar.

---

<div align="center">

**Desenvolvido com ❤️ para a comunidade de traders brasileiros**

[⬆ Voltar ao topo](#-b3-options-signals)

</div>

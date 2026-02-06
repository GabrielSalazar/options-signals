# 🚀 B3 Options Signals (Scanner & Backtester)

![Next JS](https://img.shields.io/badge/Next.js-16.1.x-black?style=for-the-badge&logo=next.js)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Prisma](https://img.shields.io/badge/Prisma-ORM-2D3748?style=for-the-badge&logo=prisma)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Auth](https://img.shields.io/badge/Auth.js-Enabled-22c55e?style=for-the-badge)
![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-000000?style=for-the-badge&logo=vercel)
![Mobile](https://img.shields.io/badge/Mobile-Optimized-16a34a?style=for-the-badge)

Plataforma profissional para identificação, análise e backtesting de oportunidades no mercado de Opções da B3 (Brasil).

O projeto utiliza uma **Arquitetura Vetorizada** de alta performance (baseada em Pandas/NumPy) para processar milhares de strikes e vencimentos em milissegundos, detectando setups de trading automaticamente.

---

## 🔥 Funcionalidades Principais

### 1. Scanner de Alta Performance (Vectorized Engine)
- Processamento massivo de cadeias de opções.
- Detecção instantânea de oportunidades com base em condições técnicas e de volatilidade.
- **Cálculo de Gregas em Tempo Real** (Delta, Gama, Theta, Vega) via `py_vollib_vectorized`.

### 2. Top 20 Estratégias de Opções Implementadas
O sistema suporta e detecta automaticamente 20 estratégias complexas:

**Básicas & Direcionais:**
- Compra a Seco (Calls/Puts)
- Lançamento Coberto (Covered Call)
- Cash Secured Put (Venda de Put com garantia)

**Travas & Spreads:**
- Trava de Alta (Bull Call Spread)
- Trava de Baixa (Bear Put Spread)
- Trava de Calendário (Calendar Spread)
- Trava Diagonal (PMCC)

**Volatilidade & Renda:**
- Straddle (Compra/Venda)
- Strangle (Compra/Venda)
- Iron Condor (Renda em lateralização)
- Butterfly / Iron Butterfly
- Jade Lizard

**Proteção (Hedge):**
- Protective Put
- Collar

### 3. Backtesting Engine
Módulo dedicado para simular a performance das estratégias com dados históricos.
- Simulação de PnL (Lucro/Prejuízo) baseada no movimento do ativo base.
- Métricas: Win Rate, Retorno Total, Drawdown.
- Suporte a indicadores técnicos (ex: RSI/IFR) usando `pandas_ta`.

### 4. Integração de Alertas
- Envio de sinais em tempo real para **Telegram** e **WhatsApp**.
- Sistema "Fire-and-Forget" para não bloquear o scanner.

### 5. Dashboard Moderno
- Interface desenvolvida em **Next.js 14** + **TailwindCSS**.
- Visualização clara dos cards de estratégias com Risco, Popularidade e Instruções de Entrada/Saída.
- Traduzido totalmente para Português.

---

## 🛠️ Arquitetura Técnica

- **Backend:** Python 3.12 (FastAPI)
  - `pandas` & `numpy`: Core de cálculo vetorizado.
  - `py_vollib_vectorized`: Precificação Black-Scholes acelerada.
  - `pandas_ta`: Análise Técnica.
- **Frontend:** Next.js (React)
  - `shadcn/ui`: Componentes de UI modernos.
  - `lucide-react`: Ícones vetoriais.
- **Infraestrutura:** Docker & Docker Compose.

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos
- Docker & Docker Compose (Recomendado)
- Ou Python 3.10+ e Node.js 18+

### Opção 1: Via Docker (Recomendado)
```bash
docker-compose up --build
```
Acesse:
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs

### Opção 2: Instalação Manual

**1. Backend (Python)**
```bash
cd b3-options-signals-py
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**2. Frontend (Next.js)**
```bash
cd b3-options-signals-web
npm install
npm run dev
```

---

## 🧪 Como Rodar Backtests

O projeto inclui um script CLI para testar estratégias.

```bash
cd b3-options-signals-py

# Exemplo: Rodar backtest da estratégia RSI em PETR4 nos últimos 90 dias
python scripts/run_backtest.py
```

Exemplo de Saída:
```text
Strategy: Reversão por IFR (RSI)
Ticker: PETR4
Win Rate: 75.0%
Est. Return: 12.5%
```

---

## 📂 Estrutura de Pastas

```
/
├── b3-options-signals-py/       # Backend FastAPI
│   ├── app/
│   │   ├── core/
│   │   │   ├── strategies_vectorized.py  # Lógica das 20 Estratégias
│   │   │   └── backtester.py             # Engine de Backtest
│   │   └── setvices/
│   │       ├── scanner.py                # Motor de Busca Vetorizado
│   │       └── greeks.py                 # Cálculo de Gregas
│   └── scripts/                          # Scripts de verificação e backtest
│
└── b3-options-signals-web/      # Frontend Next.js
    └── src/app/strategies/      # Página de visualização de estratégias
```

---

## ⚠️ Isenção de Responsabilidade
Este projeto é educacional. Operar opções envolve alto risco financeiro. Os dados fornecidos neste ambiente de demonstração são simulados (mock) ou atrasados. Não utilize para operações reais sem integração profissional de dados.

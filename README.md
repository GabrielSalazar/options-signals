# B3 Options Signals

A platform for identifying and alerting trading opportunities in Brazilian Stock Options (B3).

## Components

- **Backend**: Python (FastAPI) + py_vollib for Greeks and Strategies.
- **Frontend**: Next.js (TypeScript) + TailwindCSS for Dashboard and Visualization.

## Features

- Real-time scanning of option chains (Mocked/Simulated).
- Algorithmic Strategies:
  - **High IV Reversal**: Detects deep OTM options with anomalous volatility.
  - **Delta Hedge**: Identifies ATM options for directional plays.
- Multi-Channel Alerts:
  - Telegram Bot
  - WhatsApp (via generic API Integration)

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+

### Setup

1. **Backend**:
   ```bash
   cd b3-options-signals-py
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Frontend**:
   ```bash
   cd b3-options-signals-web
   npm install
   npm run dev
   ```

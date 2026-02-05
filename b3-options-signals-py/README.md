# B3 Options Signals - Backend API

Powerful Python backend for analyzing Brazilian Stock Options (B3) using Black-Scholes pricing, Vectorized Backtesting, and Technical Analysis.

## 🚀 Features

*   **Vectorized Strategy Engine**: High-performance simulation using Pandas & Numpy.
    *   Support for 20+ strategies (Iron Condor, Butterflies, Straddles, Greeks-based).
*   **Backtesting System**:
    *   Integration with **QuantStats** for professional metrics (Sharpe, Sortino, Drawdown).
    *   Historical data mocked via `yfinance` (production ready for B3 data vendors).
*   **Technical Analysis**:
    *   **PandasTA** integration for indicators (RSI, Bollinger, MACD).
*   **FastAPI Architecture**:
    *   Async endpoints for Scanning (`/signals/scan`) and Backtesting (`/backtest/run`).
    *   Background tasks for heavy computations.

## 🛠 Installation

Requires **Python 3.10+** (tested on 3.12).

1.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # Linux/Mac
    ```

2.  **Install Dependencies**:
    > **Note on Compatibility**: `pandas-ta` currently requires specific versions of numpy/pandas. Use the following constraints:
    
    ```bash
    pip install "numpy<2" "pandas<2.2" pandas_ta quantstats fastapi uvicorn matplotlib seaborn yfinance
    ```
    *(If you encounter build errors, try installing with `--prefer-binary` or `--no-deps` for pandas_ta)*

## 🏃 Running the Server

Start the API server on port 8000:

```bash
uvicorn app.main:app --reload --port 8000
```

## 🔌 API Endpoints

### Signals & Scanning
*   `POST /signals/scan/{ticker}`: Scans a specific ticker (e.g., PETR4) for all active strategies.
*   `GET /signals/strategies`: Lists all registered strategies and their risk profiles.

### Backtesting
*   `POST /backtest/run`: Runs a simulation for a specific strategy/ticker over N days.
    *   Body: `{"ticker": "PETR4", "strategy_name": "Reversão por IFR (RSI)", "days": 252}`
*   `GET /backtest/strategies`: Lists strategies available for backtesting.

## 🧠 Project Structure

*   `app/core/strategies_vectorized.py`: Implementation of all 20+ option strategies.
*   `app/core/backtester.py`: Engine for historical simulation.
*   `app/services/scanner.py`: Logic for real-time market scanning.
*   `app/routers/`: API route definitions.

"""Endpoints de backtest e cálculo de métricas (Sharpe, Sortino, Calmar, etc.)."""
import re
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from backend.core.config import ATIVOS_B3

router = APIRouter(tags=["Backtest"])


class BacktestParams(BaseModel):
    ticker: str
    start_date: str = "2024-01-01"
    end_date: str = ""

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.upper().replace(".SA", "")
        if not re.match(r"^[A-Z]{4,5}[0-9]{1,2}$", v):
            raise ValueError("Ticker inválido — use formato B3 (ex: PETR4, VALE3)")
        return v


@router.get("/backtest/strategies")
def backtest_strategies():
    return {"strategies": ["momentum", "reversao", "breakout"]}


@router.post("/backtest/run")
def backtest_run(params: BacktestParams):
    from backend.services.backtest import rodar_backtest
    import numpy as np
    ticker_raw = params.ticker
    ticker = ticker_raw + ".SA"
    nome = ATIVOS_B3.get(ticker, ticker_raw)
    start = params.start_date
    end = params.end_date or datetime.now().strftime("%Y-%m-%d")

    sinais = rodar_backtest(ticker, nome, start, end)

    # Serialize pandas Timestamps
    for s in sinais:
        if "data_sinal" in s and hasattr(s["data_sinal"], "isoformat"):
            s["data_sinal"] = s["data_sinal"].isoformat()

    total = len(sinais)
    if total == 0:
        return {"sinais": 0, "metrics": None, "equity_curve": [], "data": []}

    wins = sum(1 for s in sinais if s.get("hit_alvo1"))
    win_rate = wins / total

    # Equity curve — 10% position sizing per trade
    equity = 10000.0
    equity_curve = [round(equity, 2)]
    trade_returns = []
    for s in sinais:
        if s.get("hit_alvo1"):
            r = s.get("max_return", 0) * 0.10
        elif s.get("hit_stop"):
            r = -0.03
        else:
            r = s.get("max_return", 0) * 0.05
        trade_returns.append(r)
        equity *= (1 + r)
        equity_curve.append(round(equity, 2))

    total_return_pct = (equity_curve[-1] / equity_curve[0] - 1) * 100

    peak = equity_curve[0]
    max_dd = 0.0
    for e in equity_curve:
        if e > peak:
            peak = e
        dd = (peak - e) / peak
        if dd > max_dd:
            max_dd = dd

    if len(trade_returns) > 1:
        mean_r = float(np.mean(trade_returns))
        std_r = float(np.std(trade_returns))
        sharpe = round(mean_r / std_r * (252 ** 0.5), 2) if std_r > 0 else 0.0

        # Sortino
        down_returns = [r for r in trade_returns if r < 0]
        std_down = float(np.std(down_returns)) if len(down_returns) > 1 else 0.0
        sortino = round(mean_r / std_down * (252 ** 0.5), 2) if std_down > 0 else 0.0

        # Calmar
        calmar = round(total_return_pct / 100 / max_dd, 2) if max_dd > 0 else 0.0

        # Expectancy ($) per trade based on 10k initial equity position sizing
        avg_win = float(np.mean([r for r in trade_returns if r > 0])) if any(r > 0 for r in trade_returns) else 0.0
        avg_loss = float(np.mean([r for r in trade_returns if r < 0])) if any(r < 0 for r in trade_returns) else 0.0
        expectancy_pct = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        expectancy_usd = round(expectancy_pct * 1000, 2)  # Assume $1000 per trade average size
    else:
        sharpe = 0.0
        sortino = 0.0
        calmar = 0.0
        expectancy_usd = 0.0

    return {
        "sinais": total,
        "metrics": {
            "win_rate": round(win_rate * 100, 1),
            "total_return": round(total_return_pct, 1),
            "max_drawdown": round(max_dd * 100, 1),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "expectancy": expectancy_usd,
            "trades": total,
        },
        "equity_curve": equity_curve,
        "data": sinais,
    }

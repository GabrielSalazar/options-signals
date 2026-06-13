"""Shared statistical and analytical computations for market data."""
import numpy as np
import pandas as pd
from backend.domain.volatility import compute_log_returns


def compute_statistical_indicators(df: pd.DataFrame) -> dict:
    """
    Compute shared statistical indicators: MA20/50/200, sigma_20, Bollinger %B, z-score.

    Statistical indicators are calculated from market OHLCV data over configurable rolling windows.
    Key behaviors and edge cases:
    - MA20/50/200: Simple moving averages; for shorter series, uses available data
    - sigma_20: Annualized volatility from log-returns (252 trading days/year); fallback to 0.4 if < 20 observations
    - BB %B: Position within Bollinger Bands (20-period, ±2 std); clamped to 0.5 if range is 0
    - Z-score: Normalized price displacement from MA20 using sigma_20; guarded for division by zero
    - All raw values returned without rounding; callers handle precision per context

    Args:
        df: DataFrame with required OHLCV columns (Close, High, Low, Open, Volume)

    Returns:
        dict with keys: ma20, ma50, ma200, sigma_20, bb_pct_b, z_score_20
        All values are floats; rounding is delegated to callers (market.py endpoints)

    Raises:
        ValueError: If required columns (Close, High, Low) are missing
    """
    # Input validation
    required_cols = ["Close", "High", "Low"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    close = df["Close"]
    preco_atual = float(close.iloc[-1])

    # Helper to compute SMA
    def _sma(series: pd.Series, window: int) -> float:
        return float(series.rolling(window).mean().iloc[-1]) if len(series) >= window else float(series.mean())

    ma20 = _sma(close, 20)
    ma50 = _sma(close, 50)
    ma200 = _sma(close, 200) if len(close) >= 200 else _sma(close, len(close))

    # Log-returns and sigma_20 (annualized volatility)
    # Fallback to 0.4 matches estimar_iv_historica default when < 20 observations
    log_ret = compute_log_returns(close)
    sigma_20 = float(log_ret.tail(20).std() * np.sqrt(252)) if len(log_ret) >= 20 else 0.4

    # Bollinger Bands %B (position within bands)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up = bb_mid + 2 * bb_std
    bb_lo = bb_mid - 2 * bb_std
    rng_bb = float((bb_up - bb_lo).iloc[-1])
    bb_pct_b = float((preco_atual - float(bb_lo.iloc[-1])) / rng_bb) if rng_bb > 0 else 0.5

    # Z-score (normalized price displacement from MA20)
    z_score_20 = float((preco_atual - ma20) / (sigma_20 + 1e-9)) if sigma_20 > 0 else 0.0

    return {
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "sigma_20": sigma_20,
        "bb_pct_b": bb_pct_b,
        "z_score_20": z_score_20,
    }

"""Shared statistical and analytical computations for market data."""
import numpy as np
import pandas as pd


def compute_statistical_indicators(df: pd.DataFrame) -> dict:
    """
    Compute shared statistical indicators: MA20/50/200, sigma_20, Bollinger %B, z-score.

    Args:
        df: DataFrame with OHLCV columns (Open, High, Low, Close, Volume)

    Returns:
        dict with keys: ma20, ma50, ma200, sigma_20, bb_pct_b, z_score_20
    """
    close = df["Close"]
    preco_atual = float(close.iloc[-1])

    # Helper to compute SMA
    def _sma(series, window):
        return float(series.rolling(window).mean().iloc[-1]) if len(series) >= window else float(series.mean())

    ma20 = _sma(close, 20)
    ma50 = _sma(close, 50)
    ma200 = _sma(close, 200) if len(close) >= 200 else _sma(close, len(close))

    # Log-returns and sigma_20
    log_ret = np.log(close / close.shift(1)).dropna()
    sigma_20 = float(log_ret.tail(20).std() * np.sqrt(252)) if len(log_ret) >= 20 else 0.4

    # Bollinger Bands %B
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up = bb_mid + 2 * bb_std
    bb_lo = bb_mid - 2 * bb_std
    rng_bb = float((bb_up - bb_lo).iloc[-1])
    bb_pct_b = float((preco_atual - float(bb_lo.iloc[-1])) / rng_bb) if rng_bb > 0 else 0.5

    # Z-score
    z_score_20 = float((preco_atual - ma20) / (sigma_20 + 1e-9)) if sigma_20 > 0 else 0.0

    return {
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2),
        "sigma_20": round(sigma_20, 4),
        "bb_pct_b": round(bb_pct_b, 4),
        "z_score_20": round(z_score_20, 4),
    }

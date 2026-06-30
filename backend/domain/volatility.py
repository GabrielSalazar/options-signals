"""Volatility and return calculations."""
import numpy as np
import pandas as pd


def compute_log_returns(close: pd.Series) -> pd.Series:
    """
    Compute log-returns from close prices.

    Args:
        close: pd.Series of close prices

    Returns:
        pd.Series of log-returns (n-1 values, NaN values dropped)
    """
    return (np.log(close / close.shift(1))).dropna()

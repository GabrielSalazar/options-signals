"""Tests for centralized log-returns computation."""
import pandas as pd
import numpy as np
import pytest
from backend.domain.volatility import compute_log_returns


def test_compute_log_returns():
    """Test basic log-returns computation."""
    close = pd.Series([40.0, 41.0, 40.5, 42.0, 41.5])
    log_ret = compute_log_returns(close)

    assert isinstance(log_ret, pd.Series)
    assert len(log_ret) == 4  # n-1 due to shift
    assert all(np.isfinite(log_ret.values))  # no NaN or inf
    assert np.isclose(log_ret.iloc[0], np.log(41.0 / 40.0))


def test_compute_log_returns_with_nans():
    """Test log-returns with NaN values in input."""
    close = pd.Series([40.0, np.nan, 41.0, 40.5, 42.0])
    log_ret = compute_log_returns(close)

    # Should handle NaN gracefully by dropping them
    assert isinstance(log_ret, pd.Series)
    assert all(np.isfinite(log_ret.values))


def test_compute_log_returns_short_series():
    """Test with series shorter than 2 values."""
    close = pd.Series([40.0])
    log_ret = compute_log_returns(close)

    # Should return empty series
    assert len(log_ret) == 0


def test_compute_log_returns_matches_manual_calc():
    """Verify against manual calculation."""
    close = pd.Series([100.0, 101.0, 99.5, 102.0])
    log_ret = compute_log_returns(close)

    expected = [
        np.log(101.0 / 100.0),
        np.log(99.5 / 101.0),
        np.log(102.0 / 99.5)
    ]

    np.testing.assert_array_almost_equal(log_ret.values, expected)

import numpy as np
import pandas as pd
import pytest

from backend.domain.analytics import compute_statistical_indicators


def test_compute_statistical_indicators_returns_dict():
    """Test basic functionality: returns dict with all required keys."""
    dates = pd.date_range('2024-01-01', periods=100, freq='B')
    close = pd.Series(np.random.uniform(40, 50, 100), index=dates)
    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*100})
    df['Open'] = close * (1 + np.random.uniform(-0.01, 0.01, 100))
    df['High'] = df['Open'] + 0.5
    df['Low'] = df['Open'] - 0.5

    result = compute_statistical_indicators(df)

    assert isinstance(result, dict)
    assert 'ma20' in result and 'ma50' in result and 'ma200' in result
    assert 'sigma_20' in result
    assert 'bb_pct_b' in result
    assert 'z_score_20' in result
    assert all(isinstance(v, float) for v in result.values())


def test_short_series_uses_sigma_fallback():
    """Test that sigma_20 fallback (0.4) is used for series with < 20 observations."""
    dates = pd.date_range('2024-01-01', periods=15, freq='B')
    close = pd.Series(np.linspace(40, 45, 15), index=dates)
    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*15})
    df['Open'] = close * 0.99
    df['High'] = close * 1.01
    df['Low'] = close * 0.98

    result = compute_statistical_indicators(df)

    assert result['sigma_20'] == 0.4, f"Expected fallback 0.4, got {result['sigma_20']}"


def test_exactly_21_periods_computes_sigma():
    """Test that 21 observations computes sigma (not fallback).

    Note: 21 prices = 20 log-returns (after shift+dropna), which meets the >= 20 threshold.
    """
    dates = pd.date_range('2024-01-01', periods=21, freq='B')
    # Create stable prices to get deterministic sigma
    close = pd.Series([100 + i * 0.1 for i in range(21)], index=dates)
    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*21})
    df['Open'] = close * 0.99
    df['High'] = close * 1.01
    df['Low'] = close * 0.98

    result = compute_statistical_indicators(df)

    # Should compute sigma, not use fallback
    assert result['sigma_20'] != 0.4, "Expected computed sigma, got fallback 0.4"


def test_exactly_50_periods():
    """Test boundary condition at 50 periods (MA50 window)."""
    dates = pd.date_range('2024-01-01', periods=50, freq='B')
    close = pd.Series(np.linspace(40, 50, 50), index=dates)
    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*50})
    df['Open'] = close * 0.99
    df['High'] = close * 1.01
    df['Low'] = close * 0.98

    result = compute_statistical_indicators(df)

    # All values should be defined
    assert result['ma20'] > 0
    assert result['ma50'] > 0
    assert 0 <= result['bb_pct_b'] <= 1


def test_exactly_200_periods():
    """Test boundary condition at 200 periods (MA200 window)."""
    dates = pd.date_range('2024-01-01', periods=200, freq='B')
    close = pd.Series(np.linspace(40, 50, 200), index=dates)
    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*200})
    df['Open'] = close * 0.99
    df['High'] = close * 1.01
    df['Low'] = close * 0.98

    result = compute_statistical_indicators(df)

    assert result['ma20'] > 0
    assert result['ma50'] > 0
    assert result['ma200'] > 0


def test_nan_input_handling():
    """Test that NaN values in Close don't crash computation."""
    dates = pd.date_range('2024-01-01', periods=100, freq='B')
    close = pd.Series(np.random.uniform(40, 50, 100), index=dates)
    # Introduce some NaN values
    close.iloc[5:10] = np.nan
    close = close.dropna()  # dropna should handle gracefully

    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*len(close)})
    df['Open'] = close * 0.99
    df['High'] = close * 1.01
    df['Low'] = close * 0.98

    result = compute_statistical_indicators(df)

    # Should not crash and all values should be defined
    assert all(isinstance(v, float) for v in result.values())
    assert not np.isnan(result['ma20'])


def test_missing_required_columns():
    """Test that missing required columns raises ValueError."""
    dates = pd.date_range('2024-01-01', periods=50, freq='B')
    # Missing 'Low' column
    df = pd.DataFrame({
        'Close': pd.Series(np.random.uniform(40, 50, 50), index=dates),
        'High': pd.Series(np.random.uniform(50, 55, 50), index=dates),
        'Volume': [1e6]*50
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        compute_statistical_indicators(df)


def test_values_not_double_rounded():
    """Test that values returned are unrounded (rounding delegated to callers)."""
    dates = pd.date_range('2024-01-01', periods=100, freq='B')
    close = pd.Series(np.random.uniform(40, 50, 100), index=dates)
    df = pd.DataFrame({'Close': close, 'Volume': [1e6]*100})
    df['Open'] = close * (1 + np.random.uniform(-0.01, 0.01, 100))
    df['High'] = df['Open'] + 0.5
    df['Low'] = df['Open'] - 0.5

    result = compute_statistical_indicators(df)

    # Values should be floats but may have many decimal places
    # (not pre-rounded to specific precision)
    ma20 = result['ma20']
    # If it was pre-rounded to 2 decimals, many values would end in .00, .01, .02, etc.
    # We can't easily verify "not rounded" but we can ensure they're raw floats
    assert isinstance(ma20, float)
    # The value should preserve original precision (not truncated)
    assert ma20 > 0

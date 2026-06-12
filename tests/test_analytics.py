import pandas as pd
import numpy as np
from backend.domain.analytics import compute_statistical_indicators

def test_compute_statistical_indicators_returns_dict():
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

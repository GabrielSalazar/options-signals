"""
Testes unitários para o módulo indicators.py.

Cobre:
  - calcular_indicadores com dados sintéticos
  - detectar_divergencia
  - encontrar_zonas_demanda_oferta
  - detectar_canal_linear
  - Edge cases (df curto, NaN, etc.)
"""
import pytest
import numpy as np
import pandas as pd
from indicators import (
    calcular_indicadores,
    detectar_divergencia,
    encontrar_zonas_demanda_oferta,
    detectar_canal_linear,
)


def _make_ohlcv(n=100, base=100.0, seed=42):
    """Gera um DataFrame OHLCV sintético com tendência de alta."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    returns = rng.normal(0.001, 0.015, n)
    close = base * np.cumprod(1 + returns)
    high = close * (1 + rng.uniform(0.005, 0.02, n))
    low = close * (1 - rng.uniform(0.005, 0.02, n))
    open_ = close * (1 + rng.uniform(-0.01, 0.01, n))
    volume = rng.integers(1_000_000, 10_000_000, n).astype(float)
    return pd.DataFrame({
        "Open": open_, "High": high, "Low": low,
        "Close": close, "Volume": volume,
    }, index=dates)


class TestCalcularIndicadores:
    """Testes para calcular_indicadores."""

    def test_adds_expected_columns(self):
        df = _make_ohlcv(100)
        result = calcular_indicadores(df)
        expected_cols = [
            "stoch_k", "stoch_d", "rsi", "ema9", "ema21", "ema200",
            "macd", "macd_signal", "macd_diff", "atr",
            "bb_upper", "bb_lower", "bb_mid", "adx",
            "bb_pct", "bb_width", "vol_ratio",
            "trend_up", "trend_down",
            "vol_media_20", "suporte_20", "resistencia_20",
            "var_pct", "is_fundo_local", "is_topo_local",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Coluna {col} ausente"

    def test_rsi_bounded(self):
        """RSI deve estar entre 0 e 100."""
        df = calcular_indicadores(_make_ohlcv(100))
        df = df.dropna()
        assert df["rsi"].min() >= 0
        assert df["rsi"].max() <= 100

    def test_stoch_bounded(self):
        """Estocástico K deve estar entre 0 e 100."""
        df = calcular_indicadores(_make_ohlcv(100))
        df = df.dropna()
        assert df["stoch_k"].min() >= 0
        assert df["stoch_k"].max() <= 100

    def test_ema_order(self):
        """EMA9 deve ser mais responsiva que EMA21 — a média dos valores abs diff ao close deve ser menor."""
        df = calcular_indicadores(_make_ohlcv(100))
        df = df.dropna()
        diff_9 = (df["Close"] - df["ema9"]).abs().mean()
        diff_21 = (df["Close"] - df["ema21"]).abs().mean()
        assert diff_9 < diff_21, "EMA9 deve ficar mais perto do close do que EMA21"

    def test_atr_positive(self):
        df = calcular_indicadores(_make_ohlcv(100))
        df = df.dropna()
        assert (df["atr"] > 0).all()

    def test_bb_lower_below_upper(self):
        df = calcular_indicadores(_make_ohlcv(100))
        df = df.dropna()
        assert (df["bb_lower"] < df["bb_upper"]).all()

    def test_trend_up_max_3(self):
        df = calcular_indicadores(_make_ohlcv(100))
        df = df.dropna()
        assert df["trend_up"].max() <= 3
        assert df["trend_up"].min() >= 0

    def test_short_df_returns_unchanged(self):
        """DataFrame com < 30 linhas é retornado sem alteração."""
        df = _make_ohlcv(10)
        result = calcular_indicadores(df)
        assert len(result) == 10
        assert "rsi" not in result.columns

    def test_none_input(self):
        result = calcular_indicadores(None)
        assert result is None


class TestDetectarDivergencia:
    """Testes para detectar_divergencia."""

    def test_bullish_divergence(self):
        """Preço cai mas RSI sobe → divergência altista."""
        df = _make_ohlcv(50)
        df = calcular_indicadores(df).dropna()
        # Forçar divergência altista
        n = len(df)
        df.iloc[-1, df.columns.get_loc("Close")] = df.iloc[-5, df.columns.get_loc("Close")] * 0.95
        df.iloc[-1, df.columns.get_loc("rsi")] = df.iloc[-5, df.columns.get_loc("rsi")] + 10
        alta, baixa = detectar_divergencia(df, janela=5)
        assert bool(alta) is True

    def test_bearish_divergence(self):
        """Preço sobe mas RSI cai → divergência baixista."""
        df = _make_ohlcv(50)
        df = calcular_indicadores(df).dropna()
        n = len(df)
        df.iloc[-1, df.columns.get_loc("Close")] = df.iloc[-5, df.columns.get_loc("Close")] * 1.05
        df.iloc[-1, df.columns.get_loc("rsi")] = df.iloc[-5, df.columns.get_loc("rsi")] - 10
        alta, baixa = detectar_divergencia(df, janela=5)
        assert bool(baixa) is True

    def test_no_divergence(self):
        """Sem divergência → ambos False."""
        df = _make_ohlcv(50)
        df = calcular_indicadores(df).dropna()
        # Mesma direção para preço e RSI
        df.iloc[-1, df.columns.get_loc("Close")] = df.iloc[-5, df.columns.get_loc("Close")] * 1.02
        df.iloc[-1, df.columns.get_loc("rsi")] = df.iloc[-5, df.columns.get_loc("rsi")] + 5
        alta, baixa = detectar_divergencia(df, janela=5)
        assert bool(alta) is False
        assert bool(baixa) is False

    def test_short_df(self):
        """DataFrame muito curto → (False, False)."""
        df = _make_ohlcv(3)
        df["rsi"] = 50.0
        alta, baixa = detectar_divergencia(df, janela=5)
        assert alta is False and baixa is False


class TestDetectarCanalLinear:
    """Testes para detectar_canal_linear."""

    def test_uptrend_detected(self):
        """Tendência de alta com preços crescentes."""
        n = 40
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        slope = np.linspace(0, 10, n)
        df = pd.DataFrame({
            "High": 105 + slope,
            "Low": 95 + slope,
            "Close": 100 + slope,
        }, index=idx)
        alt, bx, sl = detectar_canal_linear(df, janela=20)
        assert bool(alt) is True
        assert bool(bx) is False
        assert sl > 0

    def test_downtrend_detected(self):
        n = 40
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        slope = np.linspace(0, -10, n)
        df = pd.DataFrame({
            "High": 105 + slope,
            "Low": 95 + slope,
            "Close": 100 + slope,
        }, index=idx)
        alt, bx, sl = detectar_canal_linear(df, janela=20)
        assert bool(alt) is False
        assert bool(bx) is True
        assert sl < 0

    def test_short_df(self):
        df = pd.DataFrame({"High": [105], "Low": [95], "Close": [100]})
        alt, bx, sl = detectar_canal_linear(df, janela=20)
        assert alt is False and bx is False and sl == 0.0


class TestEncontrarZonas:
    """Testes para encontrar_zonas_demanda_oferta."""

    def test_returns_tuple_of_bools(self):
        df = _make_ohlcv(100)
        df = calcular_indicadores(df).dropna()
        dem, ofe = encontrar_zonas_demanda_oferta(df)
        assert isinstance(dem, bool)
        assert isinstance(ofe, bool)

    def test_short_df(self):
        df = _make_ohlcv(5)
        dem, ofe = encontrar_zonas_demanda_oferta(df)
        assert dem is False and ofe is False

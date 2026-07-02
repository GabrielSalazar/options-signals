"""
Testes unitários para o módulo indicators.py.

Cobre:
  - calcular_indicadores com dados sintéticos
  - detectar_divergencia
  - encontrar_zonas_demanda_oferta
  - detectar_canal_linear
  - Edge cases (df curto, NaN, etc.)
"""
from unittest.mock import patch

import numpy as np
import pandas as pd

from backend.domain.indicators import (
    calcular_indicadores,
    detectar_canal_linear,
    detectar_divergencia,
    encontrar_zonas_demanda_oferta,
    pivots_confirmados,
    ultimos_pivots_confirmados,
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
            "kc_upper", "kc_lower", "kc_mid", "vwap"
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
        """Divergência altista real: dois fundos confirmados, o mais recente
        com preço menor e RSI maior que o fundo confirmado anterior."""
        df = _make_ohlcv(50)
        df = calcular_indicadores(df).dropna()
        fundo_idxs = df.index[df["is_fundo_local"]]
        assert len(fundo_idxs) >= 2
        i_prev, i_last = fundo_idxs[-2], fundo_idxs[-1]
        df.loc[i_prev, "Low"] = 100.0
        df.loc[i_last, "Low"] = 95.0  # mínima mais baixa
        df.loc[i_prev, "rsi"] = 25.0
        df.loc[i_last, "rsi"] = 40.0  # RSI mais alto — divergência
        alta, baixa = detectar_divergencia(df, janela=len(df))
        assert bool(alta) is True

    def test_bearish_divergence(self):
        """Divergência baixista real: dois topos confirmados, o mais recente
        com preço maior e RSI menor que o topo confirmado anterior."""
        df = _make_ohlcv(50)
        df = calcular_indicadores(df).dropna()
        topo_idxs = df.index[df["is_topo_local"]]
        assert len(topo_idxs) >= 2
        i_prev, i_last = topo_idxs[-2], topo_idxs[-1]
        df.loc[i_prev, "High"] = 100.0
        df.loc[i_last, "High"] = 105.0  # máxima mais alta
        df.loc[i_prev, "rsi"] = 75.0
        df.loc[i_last, "rsi"] = 60.0  # RSI mais baixo — divergência
        alta, baixa = detectar_divergencia(df, janela=len(df))
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

    def test_rsi_com_nan_retorna_false_false(self):
        """Se algum valor de RSI na janela (cauda) for NaN, não dá pra avaliar divergência → (False, False)."""
        df = _make_ohlcv(20)
        df["rsi"] = [50.0] * 15 + [np.nan] * 5
        alta, baixa = detectar_divergencia(df, janela=5)
        assert bool(alta) is False and bool(baixa) is False

    def test_ponta_a_ponta_sem_pivots_nao_gera_divergencia_falsa(self):
        """Regressão do bug de divergência ponta-a-ponta: um candle de ruído
        isolado nas duas pontas da janela (sem pivô confirmado em nenhum dos
        dois lados) não deve contar como divergência — precisa de fundos/topos
        confirmados reais para comparar."""
        df = _make_ohlcv(60)
        df = calcular_indicadores(df).dropna()
        # Mexe só no candle -1 e -5: preço cai, RSI sobe — mas nenhum dos dois
        # é necessariamente um pivô confirmado (fundo/topo local).
        df.iloc[-1, df.columns.get_loc("Close")] = df.iloc[-5, df.columns.get_loc("Close")] * 0.95
        df.iloc[-1, df.columns.get_loc("rsi")] = df.iloc[-5, df.columns.get_loc("rsi")] + 10
        df.iloc[-1, df.columns.get_loc("is_fundo_local")] = False
        df.iloc[-5, df.columns.get_loc("is_fundo_local")] = False
        alta, baixa = detectar_divergencia(df, janela=5)
        assert bool(alta) is False


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

    def test_excecao_no_polyfit_retorna_false_false_zero(self):
        """Se np.polyfit lançar (ex: dados não-finitos), captura e retorna (False, False, 0.0)."""
        n = 40
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "High": [105.0] * n,
            "Low": [95.0] * n,
            "Close": [100.0] * n,
        }, index=idx)
        with patch("backend.domain.indicators.np.polyfit", side_effect=ValueError("falha no fit")):
            alt, bx, sl = detectar_canal_linear(df, janela=20)
        assert alt is False and bx is False and sl == 0.0

    def test_drift_ruidoso_com_slope_positivo_mas_r2_baixo_nao_e_canal(self):
        """Regressão: slope>0 nos topos e fundos não basta se o ajuste é
        ruim (R² baixo) — ruído aleatório não deve ser classificado como
        canal só porque a reta média sobe."""
        n = 40
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        rng = np.random.default_rng(3)
        slope = np.linspace(0, 3, n)  # drift fraco
        ruido = rng.uniform(-15, 15, n)  # ruído dominante sobre o drift
        df = pd.DataFrame({
            "High": 105 + slope + ruido,
            "Low": 95 + slope + ruido,
            "Close": 100 + slope + ruido,
        }, index=idx)
        alt, bx, sl = detectar_canal_linear(df, janela=20)
        assert bool(alt) is False
        assert bool(bx) is False

    def test_r2_minimo_configuravel_permite_relaxar_o_filtro(self):
        """Com r2_minimo=0.0 o filtro de qualidade fica inerte — o slope
        sozinho decide, preservando o comportamento pré-filtro sob demanda."""
        n = 40
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        rng = np.random.default_rng(3)
        slope = np.linspace(0, 3, n)
        ruido = rng.uniform(-15, 15, n)
        df = pd.DataFrame({
            "High": 105 + slope + ruido,
            "Low": 95 + slope + ruido,
            "Close": 100 + slope + ruido,
        }, index=idx)
        alt, bx, sl = detectar_canal_linear(df, janela=20, r2_minimo=0.0)
        assert bool(alt) is True

    def test_canal_lateral_sem_tendencia_clara(self):
        """Topos sobem mas fundos caem → sinais opostos, nem altista nem baixista."""
        n = 30
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        df = pd.DataFrame({
            "High": 105 + np.linspace(0, 5, n),   # topos subindo
            "Low": 95 - np.linspace(0, 5, n),     # fundos caindo
            "Close": 100 + np.zeros(n),
        }, index=idx)
        alt, bx, sl = detectar_canal_linear(df, janela=20)
        assert bool(alt) is False
        assert bool(bx) is False


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

    def _df_com_fundos(self, valores_low: dict, n: int = 30, preco: float = 100.0, atr: float = 1.0):
        """DataFrame sintético com fundos confirmados nos índices/valores dados."""
        idx = pd.date_range("2024-01-01", periods=n, freq="B")
        low = [preco] * n
        for i, v in valores_low.items():
            low[i] = v
        is_fundo = [False] * n
        for i in valores_low:
            is_fundo[i] = True
        return pd.DataFrame({
            "Close": [preco] * n, "Low": low, "High": [preco] * n,
            "atr": [atr] * n, "is_fundo_local": is_fundo, "is_topo_local": [False] * n,
        }, index=idx)

    def test_um_unico_toque_nao_caracteriza_zona_de_demanda(self):
        """Um único fundo confirmado perto do preço não é zona — precisa de
        ao menos 2 toques na mesma região (regressão do falso-positivo)."""
        df = self._df_com_fundos({20: 100.5}, preco=100.0, atr=1.0)
        dem, _ = encontrar_zonas_demanda_oferta(df, ordem=1)
        assert dem is False

    def test_dois_toques_na_mesma_regiao_caracteriza_zona_de_demanda(self):
        df = self._df_com_fundos({15: 100.3, 20: 100.6}, preco=100.0, atr=1.0)
        dem, _ = encontrar_zonas_demanda_oferta(df, ordem=1)
        assert dem is True

    def test_lookback_em_dias_ignora_fundo_fora_da_janela(self):
        """Fundos fora dos últimos `lookback` dias não contam, mesmo se
        próximos entre si — lookback deve ser temporal, não contagem de pivôs."""
        df = self._df_com_fundos({0: 100.3, 1: 100.6}, n=100, preco=100.0, atr=1.0)
        dem, _ = encontrar_zonas_demanda_oferta(df, lookback=20, ordem=1)
        assert dem is False


class TestPivotsConfirmados:
    """pivots_confirmados: janela simétrica + invariância a dados futuros."""

    def test_detecta_fundo_e_topo_simples(self):
        low  = [10, 9, 8, 9, 10, 11, 12, 11, 10]
        high = [11, 10, 9, 10, 11, 12, 13, 12, 11]
        df = pd.DataFrame({"Low": low, "High": high})
        is_fundo, is_topo = pivots_confirmados(df, ordem=1)
        assert bool(is_fundo.iloc[2]) is True
        assert bool(is_topo.iloc[6]) is True

    def test_ultimas_ordem_linhas_nunca_confirmadas(self):
        df = pd.DataFrame({"Low": list(range(10, 0, -1)), "High": list(range(11, 1, -1))})
        is_fundo, is_topo = pivots_confirmados(df, ordem=2)
        assert bool(is_fundo.iloc[-1]) is False
        assert bool(is_fundo.iloc[-2]) is False

    def test_invariante_a_dados_futuros(self):
        rng = np.random.default_rng(7)
        base = 50 + np.cumsum(rng.normal(0, 1.0, 120))
        df = pd.DataFrame({"Low": base - 0.5, "High": base + 0.5})
        ordem = 2
        t = 90
        f_trunc, t_trunc = pivots_confirmados(df.iloc[:t + 1], ordem)
        f_full,  t_full  = pivots_confirmados(df.iloc[:t + 1 + 20], ordem)
        lim = t - ordem
        assert f_trunc.iloc[:lim + 1].equals(f_full.iloc[:lim + 1])
        assert t_trunc.iloc[:lim + 1].equals(t_full.iloc[:lim + 1])


class TestUltimosPivotsConfirmados:
    """ultimos_pivots_confirmados: extrai os últimos N fundos/topos confirmados."""

    def test_df_menor_ou_igual_a_ordem_retorna_listas_vazias(self):
        df = pd.DataFrame({"Low": [10, 9, 8], "High": [11, 10, 9],
                            "is_fundo_local": [False, True, False],
                            "is_topo_local": [False, False, True]})
        fundos, topos = ultimos_pivots_confirmados(df, ordem=3, n=3)
        assert list(fundos) == []
        assert list(topos) == []

    def test_df_igual_a_ordem_retorna_listas_vazias(self):
        """len(df) == ordem também deve cair no caso base (<=)."""
        df = pd.DataFrame({"Low": [10, 9], "High": [11, 10],
                            "is_fundo_local": [True, False],
                            "is_topo_local": [False, True]})
        fundos, topos = ultimos_pivots_confirmados(df, ordem=2, n=3)
        assert list(fundos) == []
        assert list(topos) == []

    def test_extrai_ultimos_n_fundos_e_topos_confirmados(self):
        low  = [10, 9, 8, 9, 10, 11, 12, 11, 10]
        high = [11, 10, 9, 10, 11, 12, 13, 12, 11]
        df = pd.DataFrame({"Low": low, "High": high})
        is_fundo, is_topo = pivots_confirmados(df, ordem=1)
        df["is_fundo_local"] = is_fundo
        df["is_topo_local"] = is_topo
        fundos, topos = ultimos_pivots_confirmados(df, ordem=1, n=3)
        # fundo confirmado em low[2]=8; topo confirmado em high[6]=13.
        assert 8 in list(fundos)
        assert 13 in list(topos)

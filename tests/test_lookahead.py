"""Guarda permanente anti-look-ahead (Camada 0, Parte 0.1).

Prova que a decisão tomada no candle t NÃO usa informação de candles > t.
Os únicos gatilhos com risco de look-ahead são os de pivot (fundos/topos) e as
zonas de demanda/oferta — os demais indicadores (RSI, MACD, EMA…) são causais.
"""
import numpy as np
import pandas as pd

from backend.domain.indicators import (
    calcular_indicadores, ultimos_pivots_confirmados, encontrar_zonas_demanda_oferta,
)
from backend.core.config import CONFIG


def _ohlcv(seed: int, n: int = 150) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    base = 30 + np.cumsum(rng.normal(0, 0.4, n))
    close = np.maximum(base, 1.0)
    high = close * (1 + rng.uniform(0.003, 0.015, n))
    low = close * (1 - rng.uniform(0.003, 0.015, n))
    openp = close + rng.normal(0, 0.05, n)
    vol = rng.uniform(2_000_000, 5_000_000, n)
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    df = pd.DataFrame({"Open": openp, "High": high, "Low": low,
                       "Close": close, "Volume": vol}, index=idx)
    return calcular_indicadores(df).dropna()


def test_consumo_de_pivots_ignora_flag_contaminado_na_borda():
    """Mesmo que is_fundo_local seja True nas últimas `ordem` linhas (como ocorre
    no backtest com indicadores pré-calculados), o consumo deve ignorá-las."""
    df = _ohlcv(1)
    ordem = CONFIG["pivot_ordem"]
    df = df.copy()
    df.iloc[-1, df.columns.get_loc("is_fundo_local")] = True
    df.iloc[-1, df.columns.get_loc("Low")] = -999.0
    fundos, _ = ultimos_pivots_confirmados(df, ordem, n=3)
    assert -999.0 not in list(fundos)


def test_decisao_em_t_invariante_a_candles_futuros():
    """Os gatilhos de pivot/zona avaliados no candle t batem quer o df termine em
    t, quer continue além — desde que os indicadores sejam recalculados por janela."""
    full = _ohlcv(2, n=150)
    ordem = CONFIG["pivot_ordem"]
    for t in (110, 120, 130):
        df_t = full.iloc[: t + 1]
        df_future_cut = full.iloc[: t + 1 + 12].iloc[: t + 1]
        f_t, tp_t = ultimos_pivots_confirmados(df_t, ordem, n=3)
        f_f, tp_f = ultimos_pivots_confirmados(df_future_cut, ordem, n=3)
        assert list(f_t) == list(f_f)
        assert list(tp_t) == list(tp_f)
        assert encontrar_zonas_demanda_oferta(df_t) == encontrar_zonas_demanda_oferta(df_future_cut)

import pandas as pd
from backend.domain.setups import SetupResult, _tendencia_ema9, larry_91


def _df(rows):
    """rows: list of (open, high, low, close). Volume fixo, ema9 adicionada à parte."""
    df = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"])
    df["Volume"] = 1_000_000.0
    return df


def _with_ema9(df, ema9_vals):
    df = df.copy()
    df["ema9"] = ema9_vals
    return df


class TestTendenciaEma9:
    def test_up_quando_ema9_sobe(self):
        df = _with_ema9(_df([(1, 1, 1, 1)] * 5), [10, 11, 12, 13, 14])
        assert _tendencia_ema9(df) == "up"

    def test_down_quando_ema9_cai(self):
        df = _with_ema9(_df([(1, 1, 1, 1)] * 5), [14, 13, 12, 11, 10])
        assert _tendencia_ema9(df) == "down"


class TestLarry91:
    def test_compra_ativa_rompe_maxima_anterior_em_tendencia_alta(self):
        # ema9 subindo; último close (12) > high anterior (11)
        df = _df([(9, 10, 8, 9), (10, 11, 9, 10), (10, 13, 10, 12)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_91(df)
        assert r.status == "ativo"
        assert r.vies == "alta"

    def test_inativo_quando_nao_rompe(self):
        df = _df([(9, 10, 8, 9), (10, 11, 9, 10), (10, 10.5, 10, 10.2)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_91(df)
        assert r.status == "inativo"

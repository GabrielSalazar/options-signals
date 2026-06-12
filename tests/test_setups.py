import pandas as pd
from backend.domain.setups import SetupResult, _tendencia_ema9, larry_91
from backend.domain.setups import larry_92, larry_93
from backend.domain.setups import inside_bar, rompimento
from backend.domain.setups import engolfo, pin_bar, doji


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


class TestLarry92:
    def test_armado_em_alta_com_pullback(self):
        # ema9 up; último candle faz mínima menor que a anterior
        df = _df([(10, 11, 9, 10), (11, 12, 10, 11), (10, 11, 8, 9)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_92(df)
        assert r.status == "armado"
        assert r.vies == "alta"

    def test_disparado_em_alta(self):
        # anterior foi pullback (low[-2] < low[-3]); atual rompe a máxima anterior
        df = _df([(10, 12, 10, 11), (10, 11, 8, 9), (9, 13, 9, 12)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_92(df)
        assert r.status == "ativo"
        assert r.vies == "alta"


class TestLarry93:
    def test_armado_apos_duas_minimas_decrescentes_em_alta(self):
        df = _df([(10, 12, 11, 11), (10, 11, 10, 10), (9, 10, 9, 9)])
        df = _with_ema9(df, [9, 10, 11])
        r = larry_93(df)
        assert r.status == "armado"
        assert r.vies == "alta"


class TestInsideBar:
    def test_ativo_quando_candle_dentro_do_anterior(self):
        df = _df([(10, 14, 8, 12), (11, 13, 9, 10)])
        df = _with_ema9(df, [10, 11])
        r = inside_bar(df)
        assert r.status == "ativo"

    def test_inativo_quando_rompe(self):
        df = _df([(10, 13, 9, 12), (11, 14, 9, 13)])
        df = _with_ema9(df, [10, 11])
        assert inside_bar(df).status == "inativo"


class TestRompimento:
    def test_rompe_resistencia(self):
        df = _df([(10, 11, 9, 10)] * 3)
        df["resistencia_20"] = [10.5, 10.5, 10.5]
        df["suporte_20"] = [8, 8, 8]
        df.loc[df.index[-1], "Close"] = 11.0  # close > resistencia anterior 10.5
        r = rompimento(df)
        assert r.status == "ativo" and r.vies == "alta"


class TestCandles:
    def test_engolfo_de_alta(self):
        # anterior vermelho (open10>close9); atual verde engole (open8<=close9, close12>=open10)
        df = _df([(10, 10, 9, 9), (8, 13, 8, 12)])
        df = _with_ema9(df, [10, 9])
        r = engolfo(df)
        assert r.status == "ativo" and r.vies == "alta"

    def test_martelo(self):
        # corpo pequeno no topo, sombra inferior longa
        df = _df([(10, 10, 8, 9.8)])
        df = _with_ema9(df, [9])
        r = pin_bar(df)
        assert r.status == "ativo" and r.vies == "alta"

    def test_doji(self):
        df = _df([(10, 11, 9, 10.02)])
        df = _with_ema9(df, [10])
        assert doji(df).status == "ativo"

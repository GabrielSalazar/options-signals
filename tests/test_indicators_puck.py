"""Indicadores da camada PUCK: HC institucional, CLV, cmf_norm, cmf_z,
absorção e persistência de fluxo."""
import numpy as np
import pandas as pd
import pytest

from backend.domain.indicators import (
    _clv,
    _high_candle_zones,
    calcular_indicadores,
)


def _df_sintetico(n=60, seed=42):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.2, 1.0, n)
    low = close - rng.uniform(0.2, 1.0, n)
    vol = rng.uniform(1e6, 2e6, n)
    return pd.DataFrame({
        "Open": close, "High": high, "Low": low, "Close": close, "Volume": vol,
    })


def test_clv_fechamento_na_maxima():
    """Fechou na máxima → CLV = +1; na mínima → -1; range zero → 0."""
    h = pd.Series([10.0, 10.0, 10.0])
    l = pd.Series([9.0, 9.0, 10.0])
    c = pd.Series([10.0, 9.0, 10.0])
    clv = _clv(h, l, c)
    assert clv.iloc[0] == pytest.approx(1.0)
    assert clv.iloc[1] == pytest.approx(-1.0)
    assert clv.iloc[2] == 0.0  # High == Low → sem pressão


def test_high_candle_atualiza_somente_com_volume_institucional():
    """HC só atualiza com novo máximo de volume E volume > fator × média20."""
    n = 30
    vol = pd.Series([1e6] * n)
    vol.iloc[25] = 2e6   # 2x a média → institucional
    vol.iloc[27] = 1.1e6 # acima da média mas < 1.5x → NÃO vira HC
    high = pd.Series([10.0] * n); high.iloc[25] = 12.0; high.iloc[27] = 15.0
    low = pd.Series([9.0] * n);  low.iloc[25] = 11.0;  low.iloc[27] = 14.0

    hc_max, hc_min = _high_candle_zones(high, low, vol, fator=1.5)

    assert hc_max.iloc[26] == 12.0   # HC definido pela barra 25
    assert hc_min.iloc[26] == 11.0
    assert hc_max.iloc[29] == 12.0   # barra 27 não substituiu o HC


def test_high_candle_novo_maximo_abaixo_do_fator_nao_vira_hc():
    """Novo recorde de volume, mas < fator × média20 → NÃO institucional (isola o filtro)."""
    n = 30
    vol = pd.Series([1e6] * n)
    vol.iloc[25] = 1.2e6  # novo máximo absoluto, mas < 1.5x a média ~1e6
    high = pd.Series([10.0] * n); high.iloc[25] = 12.0
    low = pd.Series([9.0] * n); low.iloc[25] = 11.0
    hc_max, hc_min = _high_candle_zones(high, low, vol, fator=1.5)
    assert hc_max.iloc[29] == np.inf
    assert hc_min.iloc[29] == -np.inf


def test_high_candle_sem_lookahead():
    """O HC do dia i não pode usar dados de i+1..n."""
    df = _df_sintetico(60)
    hc_full, _ = _high_candle_zones(df["High"], df["Low"], df["Volume"], 1.5)
    hc_parcial, _ = _high_candle_zones(
        df["High"].iloc[:40], df["Low"].iloc[:40], df["Volume"].iloc[:40], 1.5)
    # Mesmo valor na barra 39 calculado com 40 ou com 60 barras
    assert (hc_full.iloc[39] == hc_parcial.iloc[39]) or (
        np.isnan(hc_full.iloc[39]) and np.isnan(hc_parcial.iloc[39]))


def test_calcular_indicadores_adiciona_colunas_puck():
    df = calcular_indicadores(_df_sintetico(80))
    for col in ("ema50", "clv", "hc_max", "hc_min", "cmf_norm", "cmf_z",
                "absorcao", "fluxo_persist_pos", "fluxo_persist_neg"):
        assert col in df.columns, f"coluna {col} ausente"


def test_cmf_z_escala_de_zscore():
    """cmf_z deve ser ~N(0,1): média próxima de 0 no df sintético."""
    df = calcular_indicadores(_df_sintetico(120))
    z = df["cmf_z"].dropna()
    assert len(z) > 30
    assert abs(z.mean()) < 1.0  # sanity: não explodiu de escala


def test_fluxo_persistencia_conta_dias_consecutivos():
    df = _df_sintetico(60)
    # Força 4 dias consecutivos fechando na máxima (CLV=1) no fim da série
    for i in range(56, 60):
        df.loc[i, "Close"] = df.loc[i, "High"]
    out = calcular_indicadores(df)
    assert out["fluxo_persist_pos"].iloc[-1] >= 4
    assert out["fluxo_persist_neg"].iloc[-1] == 0


def test_absorcao_detectada():
    """High tocou o HC, fechou abaixo, CLV neutro → absorção."""
    df = _df_sintetico(60)
    # Barra 40 vira HC institucional (volume 3x)
    df.loc[40, "Volume"] = df["Volume"].mean() * 3
    df.loc[40, "High"] = 200.0
    df.loc[40, "Low"] = 100.0
    # Última barra: testa o topo do HC e falha com fluxo neutro
    df.loc[59, "High"] = 201.0             # >= hc_max (200)
    df.loc[59, "Low"] = 197.0
    df.loc[59, "Close"] = 199.0            # < hc_max e CLV = (2-2)/4 = 0
    out = calcular_indicadores(df)
    assert bool(out["absorcao"].iloc[-1]) is True

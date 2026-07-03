"""Gatilhos PUCK: G20/B20 (rompimento HC) e G21/B21 (divergência de fluxo)."""
import pandas as pd

from backend.core.config import CONFIG
from backend.services.core_engine import _avaliar_gatilhos_v2


def _df_base(n=10):
    return pd.DataFrame({
        "Open": [100.0] * n, "High": [101.0] * n, "Low": [99.0] * n,
        "Close": [100.0] * n, "Volume": [1e6] * n,
    })


def _ultimo(**kwargs):
    """Linha de indicadores com defaults neutros; override por kwargs."""
    base = {
        "cci": None, "mfi": None, "cmf": None, "supertrend_dir": None,
        "ema21": None, "adx": None, "bb_width": None,
        "hc_max": None, "hc_min": None, "ema50": None, "cmf_z": None,
        "Low": 100.0, "High": 100.0,
    }
    base.update(kwargs)
    return pd.Series(base)


def test_g20_rompimento_hc_dispara():
    """Low > hc_max + z-fluxo >= 1 + Close>EMA21>EMA50 → G20 na lista v2."""
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=1.5, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" in v2["ids_alta_v2"]


def test_g20_nao_dispara_sem_fluxo():
    """Rompimento geométrico sem z-fluxo (cmf_z=0.2) → não dispara (FIX 4 do PUCK)."""
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=0.2, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" not in v2["ids_alta_v2"]


def test_g20_nao_dispara_contra_tendencia():
    """EMAs desalinhadas (EMA21 < EMA50) → não dispara."""
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=1.5, ema21=92.0, ema50=94.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" not in v2["ids_alta_v2"]


def test_g20_sentinela_inf_nao_dispara():
    """hc_max=+inf (sem candle institucional ainda) → nunca dispara."""
    ultimo = _ultimo(hc_max=float("inf"), Low=96.0, cmf_z=1.5, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" not in v2["ids_alta_v2"]


def test_b20_rompimento_baixista():
    ultimo = _ultimo(hc_min=105.0, High=104.0, cmf_z=-1.5, ema21=106.0, ema50=108.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=103.5)
    assert "B20" in v2["ids_baixa_v2"]


def test_g21_divergencia_de_fluxo():
    """CMF negativo + preço subiu vs. barra anterior → G21 (venda absorvida)."""
    df = _df_base()
    df.loc[len(df) - 2, "Close"] = 99.0  # penúltimo fechamento abaixo
    ultimo = _ultimo(cmf=-0.15)
    v2 = _avaliar_gatilhos_v2(df, ultimo, stoch_k=50, rsi=50, preco=100.0)
    assert "G21" in v2["ids_alta_v2"]


def test_b21_divergencia_de_fluxo_baixista():
    df = _df_base()
    df.loc[len(df) - 2, "Close"] = 101.0  # penúltimo fechamento acima
    ultimo = _ultimo(cmf=0.15)
    v2 = _avaliar_gatilhos_v2(df, ultimo, stoch_k=50, rsi=50, preco=100.0)
    assert "B21" in v2["ids_baixa_v2"]


def test_puck_shadow_nao_pontua():
    """Em modo shadow (default), G20 aparece na lista mas contribui 0 pontos.

    Atenção: o fixture arma também o G17 (preço > EMA21, +1) — inevitável,
    pois o G20 exige preço > EMA21 > EMA50. Então o score esperado é
    exatamente 1 (só o G17); se o G20 pontuasse, seria 4.
    """
    assert CONFIG.get("puck_gatilhos_mode", "shadow") == "shadow"
    ultimo = _ultimo(hc_max=95.0, Low=96.0, cmf_z=1.5, ema21=94.0, ema50=92.0)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.5)
    assert "G20" in v2["ids_alta_v2"]
    assert v2["score_alta_v2"] == 1  # apenas o G17; G20 em shadow = 0 pontos


def test_indicador_ausente_fail_safe():
    """hc_max/cmf_z None (df antigo) → nunca dispara, sem exceção."""
    ultimo = _ultimo()  # tudo None
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=100.0)
    for gid in ("G20", "B20", "G21", "B21"):
        assert gid not in v2["ids_alta_v2"] + v2["ids_baixa_v2"]

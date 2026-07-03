"""Gatilhos PUCK: G20/B20 (rompimento HC) e G21/B21 (divergência de fluxo)."""
import pandas as pd

from backend.core.config import CONFIG
from backend.services import core_engine
from backend.services.core_engine import (
    _aplicar_modificadores_classe_puck,
    _avaliar_gatilhos,
    _avaliar_gatilhos_v2,
    _filtrar_ids_puck_shadow,
)


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
        "cmf_acel_pos": None, "cmf_acel_neg": None,
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


def test_filtro_puck_shadow_remove_ids_e_sinais(monkeypatch):
    """Em shadow, o filtro remove IDs PUCK e textos pareados; em ativo, mantém."""
    ids = ["G12", "G20", "G17", "G21"]
    sinais = ["s12", "s20", "s17", "s21"]
    monkeypatch.setitem(core_engine.CONFIG, "puck_gatilhos_mode", "shadow")
    assert _filtrar_ids_puck_shadow(ids, sinais) == (["G12", "G17"], ["s12", "s17"])
    monkeypatch.setitem(core_engine.CONFIG, "puck_gatilhos_mode", "ativo")
    assert _filtrar_ids_puck_shadow(ids, sinais) == (ids, sinais)


def test_matriz_v2_ativa_nao_vaza_puck_shadow_para_listas_principais(monkeypatch):
    """matriz_v2 ativo + puck shadow: G20 fica só na telemetria v2, não em ids_alta."""
    monkeypatch.setitem(core_engine.CONFIG, "matriz_v2_gatilhos_mode", "ativo")
    monkeypatch.setitem(core_engine.CONFIG, "puck_gatilhos_mode", "shadow")
    n = 30
    idx = pd.date_range("2026-01-01", periods=n, freq="B")
    df = pd.DataFrame({
        "Open": [100.0] * n, "High": [101.0] * n, "Low": [99.0] * n,
        "Close": [100.0] * n, "Volume": [3e6] * n, "rsi": [50.0] * n,
        "is_fundo_local": [False] * n, "is_topo_local": [False] * n,
        "atr": [2.0] * n,
    }, index=idx)
    base = dict(stoch_k=50, stoch_d=50, rsi=50, ema9=100, ema21=94.0,
                macd_diff=0, atr=2.0, suporte_20=90, resistencia_20=110,
                bb_lower=0, hc_max=95.0, hc_min=None, Low=96.0, High=96.5,
                cmf_z=1.5, ema50=92.0, cmf=None)
    ultimo = pd.Series(base)
    penult = pd.Series(base)
    g = _avaliar_gatilhos(df, ultimo, penult, preco=96.5,
                          vol_med=3e6, volume=3e6)
    assert "G20" in g["v2"]["ids_alta_v2"]   # telemetria preservada
    assert "G20" not in g["ids_alta"]        # não vaza para famílias/classe


def test_indicador_ausente_fail_safe():
    """hc_max/cmf_z None (df antigo) → nunca dispara, sem exceção."""
    ultimo = _ultimo()  # tudo None
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=100.0)
    for gid in ("G20", "B20", "G21", "B21", "G22", "B22"):
        assert gid not in v2["ids_alta_v2"] + v2["ids_baixa_v2"]


def test_absorcao_registra_razao_sem_mudar_classe_em_shadow():
    classe, razoes = _aplicar_modificadores_classe_puck(
        classe_v2="A", razoes=[], absorcao=True, persist=0, tipo_sinal="CALL")
    assert classe == "A"  # shadow: não rebaixa
    assert any("absorção" in r for r in razoes)


def test_persistencia_registra_candidato_a_upgrade():
    classe, razoes = _aplicar_modificadores_classe_puck(
        classe_v2="C", razoes=[], absorcao=False, persist=4, tipo_sinal="CALL")
    assert classe == "C"  # shadow: não sobe
    assert any("upgrade" in r for r in razoes)


def test_sem_absorcao_nem_persistencia_nao_altera():
    classe, razoes = _aplicar_modificadores_classe_puck(
        classe_v2="B", razoes=["x"], absorcao=False, persist=1, tipo_sinal="CALL")
    assert classe == "B"
    assert razoes == ["x"]


def test_g22_teste_do_hc_dispara():
    """Low tocou hc_max, Close fechou acima, z-fluxo ok, acelerando, acima da EMA21."""
    ultimo = _ultimo(hc_max=95.0, Low=94.5, cmf_z=1.5, ema21=90.0, ema50=88.0,
                     cmf_acel_pos=True, cmf_acel_neg=False)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.0)
    assert "G22" in v2["ids_alta_v2"]


def test_g22_nao_dispara_sem_aceleracao():
    ultimo = _ultimo(hc_max=95.0, Low=94.5, cmf_z=1.5, ema21=90.0, ema50=88.0,
                     cmf_acel_pos=False, cmf_acel_neg=False)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.0)
    assert "G22" not in v2["ids_alta_v2"]


def test_g22_nao_dispara_se_fechou_dentro_da_zona():
    """Close <= hc_max (não defendeu) → sem sinal."""
    ultimo = _ultimo(hc_max=95.0, Low=93.0, cmf_z=1.5, ema21=90.0, ema50=88.0,
                     cmf_acel_pos=True, cmf_acel_neg=False)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=94.0)
    assert "G22" not in v2["ids_alta_v2"]


def test_g22_sentinela_inf_nao_dispara():
    """hc_max=+inf → Close > inf é False → nunca dispara."""
    ultimo = _ultimo(hc_max=float("inf"), Low=94.5, cmf_z=1.5, ema21=90.0, ema50=88.0,
                     cmf_acel_pos=True, cmf_acel_neg=False)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.0)
    assert "G22" not in v2["ids_alta_v2"]


def test_b22_teste_baixista():
    ultimo = _ultimo(hc_min=105.0, High=105.5, cmf_z=-1.5, ema21=110.0, ema50=112.0,
                     cmf_acel_pos=False, cmf_acel_neg=True)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=104.0)
    assert "B22" in v2["ids_baixa_v2"]


def test_g20_e_g22_mutuamente_exclusivos():
    """Rompimento (Low>hc_max) e teste (Low<=hc_max) não coexistem na mesma barra."""
    # Cenário de teste do HC: G22 arma, G20 não
    ultimo = _ultimo(hc_max=95.0, Low=94.5, cmf_z=1.5, ema21=90.0, ema50=88.0,
                     cmf_acel_pos=True, cmf_acel_neg=False)
    v2 = _avaliar_gatilhos_v2(_df_base(), ultimo, stoch_k=50, rsi=50, preco=96.0)
    assert "G22" in v2["ids_alta_v2"] and "G20" not in v2["ids_alta_v2"]

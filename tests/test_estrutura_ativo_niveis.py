"""Níveis ATR no ativo subjacente (PUCK §12): stop 1.5×ATR, TP1 1.5×, TP2 3×."""

from backend.services.core_engine import _niveis_ativo_atr


def test_niveis_call():
    n = _niveis_ativo_atr(preco=100.0, atr=2.0, tipo_sinal="CALL")
    assert n["ativo_entrada"] == 100.0
    assert n["ativo_stop"] == 97.0    # 100 - 1.5×2
    assert n["ativo_tp1"] == 103.0    # 100 + 1.5×2
    assert n["ativo_tp2"] == 106.0    # 100 + 3×2 → R:R 2:1


def test_niveis_put_espelhados():
    n = _niveis_ativo_atr(preco=100.0, atr=2.0, tipo_sinal="PUT")
    assert n["ativo_stop"] == 103.0
    assert n["ativo_tp1"] == 97.0
    assert n["ativo_tp2"] == 94.0


def test_atr_invalido_usa_fallback_2pct():
    """ATR NaN/zero → fallback 2% do preço (fail-safe)."""
    n = _niveis_ativo_atr(preco=100.0, atr=0.0, tipo_sinal="CALL")
    assert n["ativo_stop"] == 97.0    # 100 - 1.5×(2% de 100)
    n2 = _niveis_ativo_atr(preco=100.0, atr=float("nan"), tipo_sinal="CALL")
    assert n2["ativo_stop"] == 97.0

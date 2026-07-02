"""Teste de integração: core_engine consulta option_liquidity e aplica vetos shadow."""
from datetime import date
from unittest.mock import MagicMock

import backend.services.core_engine as ce
from backend.services.core_engine import obter_option_liquidity
from backend.domain.scoring import avaliar_filtro_liquidez_shadow


def test_obter_option_liquidity_sucesso(monkeypatch):
    """Consulta option_liquidity retorna dados."""
    mock_supabase = MagicMock()
    (mock_supabase.table.return_value
     .select.return_value
     .eq.return_value
     .eq.return_value
     .single.return_value
     .execute.return_value) = MagicMock(
        data={"oi": 5000, "bid": 1.43, "ask": 1.55, "spread_pct": 8.4,
              "vxbr": 18.5, "evento_label": None}
    )
    monkeypatch.setattr(ce, "get_supabase", lambda: mock_supabase)

    resultado = obter_option_liquidity("PETR", date(2026, 7, 2))

    assert resultado["oi"] == 5000
    assert resultado["spread_pct"] == 8.4
    assert resultado["vxbr"] == 18.5


def test_obter_option_liquidity_indisponivel(monkeypatch):
    """Consulta com erro (linha inexistente / Supabase fora) retorna None."""
    mock_supabase = MagicMock()
    (mock_supabase.table.return_value
     .select.return_value
     .eq.return_value
     .eq.return_value
     .single.return_value
     .execute.side_effect) = Exception("Not found")
    monkeypatch.setattr(ce, "get_supabase", lambda: mock_supabase)

    assert obter_option_liquidity("PETR", date(2026, 7, 2)) is None

    # Sem cliente Supabase configurado também retorna None (fail-safe)
    monkeypatch.setattr(ce, "get_supabase", lambda: None)
    assert obter_option_liquidity("PETR", date(2026, 7, 2)) is None


def test_avaliar_filtro_liquidez_shadow_normal():
    """Liquidez viável retorna 'normal'."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=8.4, vxbr=18.5,
                                               evento_label=None, score=10)

    assert resultado["decisao"] == "normal"
    assert resultado["motivo"] == "execução viável"
    assert resultado["modo"] == "shadow"


def test_avaliar_filtro_liquidez_shadow_oi_baixo():
    """OI < 500 gera atenção."""
    resultado = avaliar_filtro_liquidez_shadow(oi=300, spread_pct=8.4, vxbr=18.5,
                                               evento_label=None, score=10)

    assert resultado["decisao"] == "atencao"
    assert "OI baixo" in resultado["motivo"]


def test_avaliar_filtro_liquidez_shadow_spread_alto():
    """Spread > 15% bloqueia."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=16.0, vxbr=18.5,
                                               evento_label=None, score=10)

    assert resultado["decisao"] == "bloquear"
    assert "spread inviável" in resultado["motivo"]


def test_avaliar_filtro_liquidez_shadow_vxbr_elevado():
    """VXBR > 30 gera atenção."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=8.4, vxbr=32.0,
                                               evento_label=None, score=10)

    assert resultado["decisao"] == "atencao"
    assert "VXBR elevado" in resultado["motivo"]


def test_avaliar_filtro_liquidez_shadow_evento():
    """Evento no DTE gera atenção."""
    resultado = avaliar_filtro_liquidez_shadow(oi=5000, spread_pct=8.4, vxbr=18.5,
                                               evento_label="COPOM", score=10)

    assert resultado["decisao"] == "atencao"
    assert "evento COPOM" in resultado["motivo"]

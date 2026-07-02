"""Teste de integração: core_engine consulta option_liquidity e aplica vetos shadow."""
from datetime import date
from unittest.mock import MagicMock

import backend.services.core_engine as ce
from backend.domain.scoring import avaliar_filtro_liquidez_shadow
from backend.services.core_engine import obter_option_liquidity


def _mock_supabase_liquidity(rows):
    """Mock da cadeia select/eq/lte/gte/order/limit/execute de option_liquidity."""
    mock_supabase = MagicMock()
    (mock_supabase.table.return_value
     .select.return_value
     .eq.return_value
     .lte.return_value
     .gte.return_value
     .order.return_value
     .limit.return_value
     .execute.return_value) = MagicMock(data=rows)
    return mock_supabase


def test_obter_option_liquidity_sucesso(monkeypatch):
    """Consulta retorna a linha mais recente <= data (dado do pregão anterior)."""
    mock_supabase = _mock_supabase_liquidity(
        [{"oi": 5000, "bid": 1.43, "ask": 1.55, "spread_pct": 8.4,
          "vxbr": 18.5, "evento_label": None}]
    )
    monkeypatch.setattr(ce, "get_supabase", lambda: mock_supabase)

    resultado = obter_option_liquidity("PETR", date(2026, 7, 2))

    assert resultado["oi"] == 5000
    assert resultado["spread_pct"] == 8.4
    assert resultado["vxbr"] == 18.5


def test_obter_option_liquidity_sem_linhas_retorna_none(monkeypatch):
    """Sem linha na janela de max_idade_dias retorna None (desconhecido)."""
    mock_supabase = _mock_supabase_liquidity([])
    monkeypatch.setattr(ce, "get_supabase", lambda: mock_supabase)

    assert obter_option_liquidity("PETR", date(2026, 7, 2)) is None


def test_obter_option_liquidity_indisponivel(monkeypatch):
    """Consulta com erro (Supabase fora) retorna None."""
    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = Exception("Not found")
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

"""Testes do event_service (calendário Copom — Fase 3 Matriz v2)."""
from datetime import date
from unittest.mock import MagicMock

import backend.services.event_service as es
from backend.services.event_service import (
    COPOM_DATAS_2026,
    obter_evento_na_data,
    registrar_copom_datas,
)


def test_registrar_sem_supabase_nao_explode(monkeypatch):
    """Sem Supabase, registrar é no-op fail-safe."""
    monkeypatch.setattr(es, "get_supabase", lambda: None)
    registrar_copom_datas(ano=2026)  # não deve levantar


def test_registrar_faz_upsert_das_datas(monkeypatch):
    """Registrar faz um upsert idempotente por data Copom."""
    mock_supabase = MagicMock()
    monkeypatch.setattr(es, "get_supabase", lambda: mock_supabase)

    registrar_copom_datas(ano=2026)

    upsert = mock_supabase.table.return_value.upsert
    assert upsert.call_count == len(COPOM_DATAS_2026)
    _, kwargs = upsert.call_args
    assert kwargs["on_conflict"] == "data,label"
    payload = upsert.call_args[0][0]
    assert payload["label"] == "COPOM"


def test_registrar_ano_desconhecido_nao_upserta(monkeypatch):
    """Ano sem datas conhecidas não gera upserts."""
    mock_supabase = MagicMock()
    monkeypatch.setattr(es, "get_supabase", lambda: mock_supabase)

    registrar_copom_datas(ano=2027)

    mock_supabase.table.return_value.upsert.assert_not_called()


def test_obter_evento_na_data_acha_label(monkeypatch):
    """Consulta retorna label quando há evento na data."""
    mock_supabase = MagicMock()
    (mock_supabase.table.return_value
     .select.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[{"label": "COPOM"}])
    monkeypatch.setattr(es, "get_supabase", lambda: mock_supabase)

    assert obter_evento_na_data(date(2026, 7, 15)) == "COPOM"


def test_obter_evento_na_data_sem_dado_ou_supabase(monkeypatch):
    """Sem linha ou sem Supabase, retorna None (fail-safe)."""
    mock_supabase = MagicMock()
    (mock_supabase.table.return_value
     .select.return_value
     .eq.return_value
     .execute.return_value) = MagicMock(data=[])
    monkeypatch.setattr(es, "get_supabase", lambda: mock_supabase)
    assert obter_evento_na_data(date(2026, 7, 2)) is None

    monkeypatch.setattr(es, "get_supabase", lambda: None)
    assert obter_evento_na_data(date(2026, 7, 2)) is None


def test_obter_evento_na_data_erro_supabase(monkeypatch):
    """Exceção na consulta retorna None (fail-safe)."""
    mock_supabase = MagicMock()
    (mock_supabase.table.return_value
     .select.return_value
     .eq.return_value
     .execute.side_effect) = Exception("boom")
    monkeypatch.setattr(es, "get_supabase", lambda: mock_supabase)

    assert obter_evento_na_data(date(2026, 7, 2)) is None

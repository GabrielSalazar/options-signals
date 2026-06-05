"""Testes de integração HTTP via TestClient (P1-3).

Exercitam o contrato real dos endpoints (status code + shape do JSON), sem
disparar o lifespan (scheduler/Telegram/Supabase) — instanciamos o TestClient
sem o context manager, então os eventos de startup não rodam. Sem Supabase no
ambiente de teste, os endpoints caem para o estado em memória.
"""
import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.config import ATIVOS_B3

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "redis" in body and "components" in body


def test_signals_lista_sem_supabase_usa_memoria():
    r = client.get("/signals")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body and isinstance(body["data"], list)
    assert body["source"] in ("memory", "supabase", "memory_fallback")


def test_signals_respeita_limit():
    r = client.get("/signals?limit=5")
    assert r.status_code == 200
    assert len(r.json()["data"]) <= 5


def test_signals_limit_acima_do_teto_rejeitado():
    r = client.get("/signals?limit=999")  # le=200
    assert r.status_code == 422


def test_watchlist_curada():
    r = client.get("/signals/watchlist")
    assert r.status_code == 200
    body = r.json()
    assert body["universe"] == "curated"
    assert body["count"] == len(ATIVOS_B3)
    assert "PETR4" in body["watchlist"]


def test_strategies_lista():
    r = client.get("/signals/strategies")
    assert r.status_code == 200
    assert isinstance(r.json()["strategies"], list)


def test_history_sem_supabase():
    r = client.get("/signals/history?limit=10")
    assert r.status_code == 200
    assert "data" in r.json()


def test_outcomes_sem_supabase():
    r = client.get("/signals/outcomes?days=30")
    assert r.status_code == 200
    body = r.json()
    assert "sinais_avaliados" in body  # sem Supabase → 0, mas shape válido


def test_outcomes_valida_days():
    r = client.get("/signals/outcomes?days=999")  # le=365
    assert r.status_code == 422

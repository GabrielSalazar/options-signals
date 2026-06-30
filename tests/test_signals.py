"""Testes do router backend/api/routers/signals.py.

Cobre:
  - GET /signals: fallback em memória (com filtros tipo/min_score) e caminho
    Supabase (sucesso e exceção → memory_fallback).
  - GET /signals/history: fallback em memória (com filtros ticker/tipo_sinal)
    e caminho Supabase (sucesso e exceção → memory_fallback).
  - GET /signals/watchlist: universo curado vs all-b3.
  - GET /signals/analytics/{ticker}: 503 sem Supabase, sucesso com dados,
    sucesso vazio (avg_score=0), e 500 em exceção.
  - GET /signals/performance: sem Supabase, sem dados, com dados (agregação
    por ticker, deltas, ponderado), e erro do Supabase.
  - GET /signals/outcomes: delega a avaliar_sinais.
  - GET /signals/strategies: lista estática.

Estratégia: monkeypatch de get_supabase (retorna None ou um fake com
table().select()...execute()) e de signal_service.last_scan_signals,
seguindo o padrão de tests/test_outcome_service.py e test_signal_service.py.
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services import signal_service

client = TestClient(app)

_MOD = "backend.api.routers.signals"


class _FakeQuery:
    """Fake de query-builder do Supabase: encadeia métodos e retorna dados
    fixos (ou levanta exceção) em execute()."""

    def __init__(self, data=None, count=None, raise_exc=None):
        self._data = data if data is not None else []
        self._count = count
        self._raise_exc = raise_exc

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def range(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        if self._raise_exc:
            raise self._raise_exc
        return type("R", (), {"data": self._data, "count": self._count})()


class _FakeSupabase:
    def __init__(self, data=None, count=None, raise_exc=None):
        self._data = data
        self._count = count
        self._raise_exc = raise_exc

    def table(self, nome):
        return _FakeQuery(self._data, self._count, self._raise_exc)


def _sinal(**over):
    base = {
        "ticker": "PETR4", "tipo_sinal": "CALL", "score": 8,
        "timestamp": "2026-05-20T13:00:00+00:00",
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# GET /signals
# ---------------------------------------------------------------------------

def test_get_signals_sem_supabase_usa_memoria(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    monkeypatch.setattr(
        signal_service, "last_scan_signals",
        lambda: [_sinal(ticker="PETR4", score=9), _sinal(ticker="VALE3", score=3)],
    )
    resp = client.get("/signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "memory"
    assert body["count"] == 2
    assert len(body["data"]) == 2


def test_get_signals_memoria_filtra_tipo_e_min_score(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    monkeypatch.setattr(
        signal_service, "last_scan_signals",
        lambda: [
            _sinal(ticker="PETR4", tipo_sinal="CALL", score=9),
            _sinal(ticker="VALE3", tipo_sinal="PUT", score=9),
            _sinal(ticker="ITUB4", tipo_sinal="CALL", score=2),
        ],
    )
    resp = client.get("/signals", params={"tipo": "CALL", "min_score": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["data"][0]["ticker"] == "PETR4"


def test_get_signals_memoria_respeita_paginacao(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    sinais = [_sinal(ticker=f"T{i}3") for i in range(5)]
    monkeypatch.setattr(signal_service, "last_scan_signals", lambda: sinais)
    resp = client.get("/signals", params={"limit": 2, "offset": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 5
    assert len(body["data"]) == 2
    assert body["data"][0]["ticker"] == "T13"


def test_get_signals_supabase_sucesso(monkeypatch):
    fake = _FakeSupabase(data=[_sinal(ticker="PETR4")], count=1)
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals", params={"tipo": "CALL", "min_score": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "supabase"
    assert body["count"] == 1
    assert body["data"][0]["ticker"] == "PETR4"


def test_get_signals_supabase_exception_cai_para_memory_fallback(monkeypatch):
    fake = _FakeSupabase(raise_exc=RuntimeError("conexão falhou"))
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    monkeypatch.setattr(
        signal_service, "last_scan_signals", lambda: [_sinal(ticker="PETR4")]
    )
    resp = client.get("/signals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "memory_fallback"
    assert body["count"] == 1


# ---------------------------------------------------------------------------
# GET /signals/history
# ---------------------------------------------------------------------------

def test_get_history_sem_supabase_filtra_em_memoria(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    monkeypatch.setattr(
        signal_service, "last_scan_signals",
        lambda: [
            _sinal(ticker="PETR4", tipo_sinal="CALL"),
            _sinal(ticker="VALE3", tipo_sinal="PUT"),
        ],
    )
    resp = client.get("/signals/history", params={"ticker": "petr4"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "memory"
    assert len(body["data"]) == 1
    assert body["data"][0]["ticker"] == "PETR4"


def test_get_history_filtra_por_tipo_sinal(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    monkeypatch.setattr(
        signal_service, "last_scan_signals",
        lambda: [
            _sinal(ticker="PETR4", tipo_sinal="CALL"),
            _sinal(ticker="VALE3", tipo_sinal="PUT"),
        ],
    )
    resp = client.get("/signals/history", params={"tipo_sinal": "put"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["ticker"] == "VALE3"


def test_get_history_supabase_sucesso(monkeypatch):
    fake = _FakeSupabase(data=[_sinal(ticker="VALE3", tipo_sinal="PUT")])
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    monkeypatch.setattr(signal_service, "last_scan_signals", lambda: [])
    resp = client.get("/signals/history", params={"ticker": "VALE3", "tipo_sinal": "PUT"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "supabase"
    assert body["data"][0]["ticker"] == "VALE3"


def test_get_history_supabase_exception_cai_para_memory_fallback(monkeypatch):
    fake = _FakeSupabase(raise_exc=RuntimeError("timeout"))
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    monkeypatch.setattr(
        signal_service, "last_scan_signals", lambda: [_sinal(ticker="ITUB4")]
    )
    resp = client.get("/signals/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "memory_fallback"
    assert body["data"][0]["ticker"] == "ITUB4"


# ---------------------------------------------------------------------------
# GET /signals/watchlist
# ---------------------------------------------------------------------------

def test_get_watchlist_curada_por_padrao():
    resp = client.get("/signals/watchlist")
    assert resp.status_code == 200
    body = resp.json()
    assert body["universe"] == "curated"
    assert body["count"] > 0
    assert all(".SA" not in t for t in body["watchlist"])


def test_get_watchlist_all_b3(monkeypatch):
    monkeypatch.setattr(
        f"{_MOD}.get_all_b3_assets", lambda: {"XPTO3.SA": "Xpto", "ABCD4.SA": "Abcd"}
    )
    resp = client.get("/signals/watchlist", params={"all_b3": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body["universe"] == "all-b3"
    assert body["count"] == 2
    assert set(body["watchlist"]) == {"XPTO3", "ABCD4"}


# ---------------------------------------------------------------------------
# GET /signals/analytics/{ticker}
# ---------------------------------------------------------------------------

def test_analytics_sem_supabase_retorna_503(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    resp = client.get("/signals/analytics/PETR4")
    assert resp.status_code == 503


def test_analytics_sucesso_com_dados(monkeypatch):
    fake = _FakeSupabase(data=[
        _sinal(ticker="PETR4", tipo_sinal="CALL", score=8),
        _sinal(ticker="PETR4", tipo_sinal="CALL", score=6),
        _sinal(ticker="PETR4", tipo_sinal="PUT", score=4),
    ])
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals/analytics/petr4.sa")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "PETR4"
    assert body["total"] == 3
    assert body["calls"] == 2
    assert body["puts"] == 1
    assert body["avg_score"] == 6.0


def test_analytics_sem_sinais_avg_score_zero(monkeypatch):
    fake = _FakeSupabase(data=[])
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals/analytics/VALE3")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["avg_score"] == 0


def test_analytics_exception_retorna_500(monkeypatch):
    fake = _FakeSupabase(raise_exc=RuntimeError("erro supabase"))
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals/analytics/PETR4")
    assert resp.status_code == 500
    assert "erro supabase" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /signals/performance
# ---------------------------------------------------------------------------

def test_performance_sem_supabase(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: None)
    resp = client.get("/signals/performance")
    assert resp.status_code == 200
    assert resp.json() == {"error": "Supabase indisponível"}


def test_performance_sem_dados(monkeypatch):
    fake = _FakeSupabase(data=[])
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals/performance", params={"days": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"period_days": 7, "total_signals": 0, "by_ticker": [], "summary": {}}


def test_performance_exception_retorna_erro(monkeypatch):
    fake = _FakeSupabase(raise_exc=RuntimeError("supabase down"))
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals/performance")
    assert resp.status_code == 200
    assert resp.json() == {"error": "supabase down"}


def test_performance_com_dados_agrega_por_ticker(monkeypatch):
    rows = [
        {
            "ticker": "PETR4", "tipo_sinal": "CALL", "score": 8,
            "score_ponderado": 70, "ponderado_passou": True,
            "greeks": {"delta": 0.45},
        },
        {
            "ticker": "PETR4", "tipo_sinal": "PUT", "score": 6,
            "score_ponderado": None, "ponderado_passou": False,
            "greeks": {"delta": -0.3},
        },
        {
            "ticker": "VALE3", "tipo_sinal": "CALL", "score": 9,
            "score_ponderado": 80, "ponderado_passou": True,
            "greeks": None,
        },
    ]
    fake = _FakeSupabase(data=rows)
    monkeypatch.setattr(f"{_MOD}.get_supabase", lambda: fake)
    resp = client.get("/signals/performance", params={"days": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_signals"] == 3
    assert body["calls"] == 2
    assert body["puts"] == 1

    by_ticker = {b["ticker"]: b for b in body["by_ticker"]}
    petr4 = by_ticker["PETR4"]
    assert petr4["count"] == 2
    assert petr4["call"] == 1
    assert petr4["put"] == 1
    assert petr4["avg_score"] == 7.0
    # avg_abs_delta = média de |0.45| e |-0.3| = 0.375
    assert petr4["avg_abs_delta"] == 0.375

    vale3 = by_ticker["VALE3"]
    assert vale3["avg_abs_delta"] is None  # sem greeks.delta válido

    # ordenado por count desc → PETR4 (2) antes de VALE3 (1)
    assert [b["ticker"] for b in body["by_ticker"]] == ["PETR4", "VALE3"]

    assert body["ponderado_concordancia_pct"] == round(2 / 3 * 100, 1)


# ---------------------------------------------------------------------------
# GET /signals/outcomes
# ---------------------------------------------------------------------------

def test_outcomes_delega_para_avaliar_sinais():
    with patch(
        "backend.services.outcome_service.avaliar_sinais",
        return_value={"resolvidos": 3, "dias": 15},
    ) as mock_avaliar:
        resp = client.get("/signals/outcomes", params={"days": 15})
    assert resp.status_code == 200
    assert resp.json() == {"resolvidos": 3, "dias": 15}
    mock_avaliar.assert_called_once_with(dias=15)


# ---------------------------------------------------------------------------
# GET /signals/strategies
# ---------------------------------------------------------------------------

def test_strategies_retorna_lista_estatica():
    resp = client.get("/signals/strategies")
    assert resp.status_code == 200
    body = resp.json()
    assert body["strategies"] == ["CALL OTM", "PUT OTM", "CALL ATM", "PUT ATM"]

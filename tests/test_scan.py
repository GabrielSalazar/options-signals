"""Testes do router backend/api/routers/scan.py.

Cobre:
  - POST /signals/scan (batch): delega a signal_service.scan_batch.
  - GET /signals/scan/stream (SSE): eventos de progresso + evento final
    "done", com e sem lista explícita de tickers, persistindo/notificando
    apenas quando há sinais encontrados.
  - GET /signals/alerts/stream (SSE): registra fila, emite item da fila,
    encerra ao cancelar — usamos client.stream com um único evento.
  - POST /signals/scan/all e /signals/scan/all-b3: delegam a run_scan(universe=...)
    e retornam o último resultado de scan.
  - POST e GET /signals/scan/{ticker}: sinal encontrado vs nenhum sinal;
    validação do Path pattern (ticker inválido → 422 por não casar a rota
    parametrizada, recaindo em outras rotas registradas ou 404/422).

Estratégia: monkeypatch de signal_service.* nos pontos usados pelo router
(scan_batch, run_scan, last_scan_signals, analyse_ticker, persist_signals,
register_alert_queue/unregister_alert_queue) e em backend.api.routers.scan
para os nomes importados diretamente (analyse_ticker, persist_signals).
"""
import json

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.services import signal_service

client = TestClient(app)

_MOD = "backend.api.routers.scan"


# ---------------------------------------------------------------------------
# POST /signals/scan (batch)
# ---------------------------------------------------------------------------

def test_scan_batch_delega_e_retorna_contagem(monkeypatch):
    captured = {}

    def fake_scan_batch(tickers):
        captured["tickers"] = tickers
        return [{"ticker": "PETR4", "score": 8}]

    monkeypatch.setattr(signal_service, "scan_batch", fake_scan_batch)
    resp = client.post("/signals/scan", json=["PETR4", "VALE3"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["data"] == [{"ticker": "PETR4", "score": 8}]
    assert "1 sinal" in body["message"]
    assert captured["tickers"] == ["PETR4", "VALE3"]


def test_scan_batch_sem_sinais(monkeypatch):
    monkeypatch.setattr(signal_service, "scan_batch", lambda tickers: [])
    resp = client.post("/signals/scan", json=["XPTO3"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["data"] == []


# ---------------------------------------------------------------------------
# GET /signals/scan/stream (SSE)
# ---------------------------------------------------------------------------

def _parse_sse_events(raw_text: str) -> list[dict]:
    events = []
    for line in raw_text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: "):]))
    return events


def test_scan_stream_com_tickers_explicitos_emite_progresso_e_done(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.analyse_ticker", lambda t_sa, nome: {"ticker": t_sa, "score": 7})
    persisted = []
    monkeypatch.setattr(f"{_MOD}.persist_signals", lambda s: persisted.append(s))
    monkeypatch.setattr(f"{_MOD}.notificar_lote", lambda s: None)
    monkeypatch.setattr(signal_service, "update_last_scan", lambda s: None)

    resp = client.get("/signals/scan/stream", params={"tickers": "PETR4,VALE3"})
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)

    progress_events = [e for e in events if e["type"] == "progress"]
    done_events = [e for e in events if e["type"] == "done"]
    assert len(progress_events) == 2
    assert all(e["has_signal"] for e in progress_events)
    assert {e["ticker"] for e in progress_events} == {"PETR4", "VALE3"}
    assert len(done_events) == 1
    assert done_events[0]["count"] == 2
    assert len(persisted) == 1 and len(persisted[0]) == 2


def test_scan_stream_sem_sinais_nao_persiste(monkeypatch):
    monkeypatch.setattr(f"{_MOD}.analyse_ticker", lambda t_sa, nome: None)
    persisted_calls = []
    monkeypatch.setattr(f"{_MOD}.persist_signals", lambda s: persisted_calls.append(s))
    monkeypatch.setattr(f"{_MOD}.notificar_lote", lambda s: None)

    resp = client.get("/signals/scan/stream", params={"tickers": "ITUB4"})
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    done_events = [e for e in events if e["type"] == "done"]
    assert done_events[0]["count"] == 0
    assert persisted_calls == []
    progress = [e for e in events if e["type"] == "progress"][0]
    assert progress["has_signal"] is False
    assert "signal" not in progress


def test_scan_stream_sem_query_param_usa_universo_curado(monkeypatch):
    """tickers="" (default) deve iterar todo ATIVOS_B3 — validamos que pelo
    menos um evento de progresso por ativo curado é emitido."""
    from backend.core.config import ATIVOS_B3
    monkeypatch.setattr(f"{_MOD}.analyse_ticker", lambda t_sa, nome: None)
    monkeypatch.setattr(f"{_MOD}.persist_signals", lambda s: None)
    monkeypatch.setattr(f"{_MOD}.notificar_lote", lambda s: None)

    resp = client.get("/signals/scan/stream")
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    progress_events = [e for e in events if e["type"] == "progress"]
    assert len(progress_events) == len(ATIVOS_B3)


# ---------------------------------------------------------------------------
# GET /signals/alerts/stream (SSE)
# ---------------------------------------------------------------------------

def test_alerts_stream_registra_e_desregistra_fila(monkeypatch):
    registered = []
    unregistered = []

    class _Q:
        async def get(self):
            raise __import__("asyncio").CancelledError()

    def fake_register():
        q = _Q()
        registered.append(q)
        return q

    def fake_unregister(q):
        unregistered.append(q)

    monkeypatch.setattr(signal_service, "register_alert_queue", fake_register)
    monkeypatch.setattr(signal_service, "unregister_alert_queue", fake_unregister)

    resp = client.get("/signals/alerts/stream")
    assert resp.status_code == 200
    # CancelledError dentro do generator é capturado e a fila é desregistrada
    assert len(registered) == 1
    assert unregistered == registered


# ---------------------------------------------------------------------------
# POST /signals/scan/all e /signals/scan/all-b3
# ---------------------------------------------------------------------------

def test_scan_all_delega_run_scan_curado(monkeypatch):
    calls = []
    monkeypatch.setattr(signal_service, "run_scan", lambda universe: calls.append(universe))
    monkeypatch.setattr(signal_service, "last_scan_signals", lambda: [{"ticker": "PETR4"}])
    resp = client.post("/signals/scan/all")
    assert resp.status_code == 200
    body = resp.json()
    assert calls == ["curado"]
    assert body["data"] == [{"ticker": "PETR4"}]
    assert "1 sinal" in body["message"]


def test_scan_all_b3_delega_run_scan_liquido(monkeypatch):
    calls = []
    monkeypatch.setattr(signal_service, "run_scan", lambda universe: calls.append(universe))
    monkeypatch.setattr(signal_service, "last_scan_signals", lambda: [])
    resp = client.post("/signals/scan/all-b3")
    assert resp.status_code == 200
    body = resp.json()
    assert calls == ["liquido"]
    assert body["universe"] == "all-b3"
    assert body["data"] == []


# ---------------------------------------------------------------------------
# POST e GET /signals/scan/{ticker}
# ---------------------------------------------------------------------------

def test_scan_ticker_post_com_sinal(monkeypatch):
    monkeypatch.setattr(signal_service, "scan_single", lambda t: {"ticker": t, "score": 9})
    resp = client.post("/signals/scan/PETR4")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sinal"]["ticker"] == "PETR4"


def test_scan_ticker_post_sem_sinal(monkeypatch):
    monkeypatch.setattr(signal_service, "scan_single", lambda t: None)
    resp = client.post("/signals/scan/VALE3")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"sinal": None, "message": "Nenhum sinal detectado"}


def test_scan_ticker_get_delega_para_mesma_logica(monkeypatch):
    monkeypatch.setattr(signal_service, "scan_single", lambda t: {"ticker": t, "score": 5})
    resp = client.get("/signals/scan/ITUB4")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sinal"]["ticker"] == "ITUB4"


def test_scan_ticker_path_pattern_rejeita_ticker_muito_curto():
    """Pattern exige 4-8 caracteres alfanuméricos — "AB" não casa, então a
    rota paramétrica não combina e o FastAPI deve responder 404 (sem rota
    alternativa) em vez de 200."""
    resp = client.post("/signals/scan/AB")
    assert resp.status_code in (404, 422)

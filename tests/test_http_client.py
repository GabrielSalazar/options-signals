import pytest
import requests

from backend.services.http_client import get_with_retry


def test_get_with_retry_retorna_resposta_no_sucesso_imediato(monkeypatch):
    class _FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"ok": True}

    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResp())
    resp = get_with_retry("http://exemplo.com", timeout=5)
    assert resp.json() == {"ok": True}


def test_get_with_retry_tenta_3_vezes_antes_de_desistir(monkeypatch):
    chamadas = {"n": 0}

    def _falha(*a, **k):
        chamadas["n"] += 1
        raise requests.exceptions.ConnectionError("falhou")

    monkeypatch.setattr(requests, "get", _falha)
    monkeypatch.setattr("backend.services.http_client.time.sleep", lambda *a: None)

    with pytest.raises(requests.exceptions.ConnectionError):
        get_with_retry("http://exemplo.com", timeout=5, tentativas=3)

    assert chamadas["n"] == 3


def test_get_with_retry_recupera_na_segunda_tentativa(monkeypatch):
    chamadas = {"n": 0}

    class _FakeResp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self): return {"ok": True}

    def _falha_depois_recupera(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise requests.exceptions.Timeout("timeout")
        return _FakeResp()

    monkeypatch.setattr(requests, "get", _falha_depois_recupera)
    monkeypatch.setattr("backend.services.http_client.time.sleep", lambda *a: None)

    resp = get_with_retry("http://exemplo.com", timeout=5, tentativas=3)
    assert resp.json() == {"ok": True}
    assert chamadas["n"] == 2

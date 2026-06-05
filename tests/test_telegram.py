"""Testes do telegram_service — lote com throttle e quebras de linha reais."""
from backend.services import telegram_service as ts


def test_notificar_lote_envia_todos_com_throttle(monkeypatch):
    enviados, slept = [], []
    monkeypatch.setattr(ts, "enviar_telegram", lambda s: enviados.append(s["ticker"]))
    monkeypatch.setattr(ts.time, "sleep", lambda s: slept.append(s))
    ts.notificar_lote([{"ticker": "A"}, {"ticker": "B"}, {"ticker": "C"}], throttle_s=0.1)
    assert enviados == ["A", "B", "C"]
    assert slept == [0.1, 0.1]   # 2 sleeps entre 3 mensagens


def test_notificar_lote_vazio_nao_quebra(monkeypatch):
    monkeypatch.setattr(ts, "enviar_telegram", lambda s: None)
    monkeypatch.setattr(ts.time, "sleep", lambda s: None)
    ts.notificar_lote([])  # não deve levantar


def test_enviar_telegram_usa_quebras_reais(monkeypatch):
    capt = {}
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "y")

    def fake_post(url, data=None, timeout=None):
        capt["text"] = data["text"]
        return object()

    monkeypatch.setattr(ts.requests, "post", fake_post)
    ts.enviar_telegram({"ticker": "PETR4", "nome": "Petrobras", "tipo_sinal": "CALL",
                        "mes_venc": 6, "ano_venc": 2026, "gatilhos": ["g1"]})
    assert "\\n" not in capt["text"]   # sem barra-n literal
    assert "\n" in capt["text"]         # quebras de linha reais

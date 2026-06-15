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


def test_formatter_separa_score_tecnico_e_bonus(monkeypatch):
    import backend.services.telegram_service as tg
    capturado = {}
    monkeypatch.setitem(tg.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(tg.CONFIG, "telegram_chat_id", "y")
    monkeypatch.setattr(tg.requests, "post",
                        lambda *a, **k: capturado.update(k.get("data", {})) or type("R", (), {})())
    tg.enviar_telegram({
        "ticker": "PETR4", "nome": "Petrobras", "tipo_sinal": "CALL",
        "mes_venc": 6, "ano_venc": 2026, "strike_ref": 40.0, "dist_otm_pct": 6.0,
        "iv_hist": 35.0, "dte": 30, "entrada_min": 0.5, "entrada_max": 0.6,
        "alvo1": 0.7, "alvo2": 1.0, "alvo_final": 2.0, "stop": 0.3,
        "rr_alvo1": 0.5, "rr_alvo2": 1.0, "rr_final": 2.0,
        "score_tecnico": 9, "bonus_sessao": 3, "score": 9, "gatilhos": ["x"],
    })
    assert "Score técnico:* 9" in capturado["text"]
    assert "Bônus sessão:* +3" in capturado["text"]


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


def test_save_telegram_config_grava_no_supabase(monkeypatch):
    import backend.services.telegram_service as tg
    capturado = {}
    class _Tbl:
        def upsert(self, row): capturado.update(row); return self
        def execute(self): return type("R", (), {})()
    class _Sb:
        def table(self, _): return _Tbl()
    monkeypatch.setattr(tg, "get_supabase", lambda: _Sb())
    tg.save_telegram_config("tok", "cid")
    assert capturado.get("token") == "tok" and capturado.get("chat_id") == "cid"

"""Testes do telegram_service — lote com throttle e quebras de linha reais."""
from backend.services import telegram_service as ts


class _FakeResp:
    def __init__(self, ok=True, payload=None, status=200):
        self.ok = ok
        self.status_code = status
        self._payload = payload if payload is not None else {"ok": True}

    def json(self):
        return self._payload


def test_enviar_mensagem_teste_sem_config_retorna_erro(monkeypatch):
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "")
    resultado = ts.enviar_mensagem_teste()
    assert resultado["ok"] is False
    assert "não configurado" in resultado["erro"]


def test_enviar_mensagem_teste_sucesso(monkeypatch):
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "tok")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "123")
    monkeypatch.setattr(ts.requests, "post", lambda *a, **k: _FakeResp(ok=True, payload={"ok": True}))
    assert ts.enviar_mensagem_teste() == {"ok": True}


def test_enviar_mensagem_teste_erro_do_telegram(monkeypatch):
    """Telegram responde ok=false com description → propaga o motivo."""
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "tok")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "123")
    monkeypatch.setattr(ts.requests, "post",
                        lambda *a, **k: _FakeResp(ok=False, status=400,
                                                  payload={"ok": False, "description": "chat not found"}))
    resultado = ts.enviar_mensagem_teste()
    assert resultado == {"ok": False, "erro": "chat not found"}


def test_enviar_mensagem_teste_excecao_nao_propaga(monkeypatch):
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "tok")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "123")
    def _boom(*a, **k):
        raise RuntimeError("timeout")
    monkeypatch.setattr(ts.requests, "post", _boom)
    resultado = ts.enviar_mensagem_teste()
    assert resultado["ok"] is False
    assert "timeout" in resultado["erro"]


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
        "hv_20d": 35.0, "dte": 30, "entrada_min": 0.5, "entrada_max": 0.6,
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


# ── enviar_telegram: sem config ─────────────────────────────────────────────────

def test_enviar_telegram_sem_token_nao_chama_requests(monkeypatch):
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "y")
    chamou = []
    monkeypatch.setattr(ts.requests, "post", lambda *a, **k: chamou.append(1))
    ts.enviar_telegram({"ticker": "PETR4"})
    assert chamou == []


def test_enviar_telegram_sem_chat_id_nao_chama_requests(monkeypatch):
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "")
    chamou = []
    monkeypatch.setattr(ts.requests, "post", lambda *a, **k: chamou.append(1))
    ts.enviar_telegram({"ticker": "PETR4"})
    assert chamou == []


def test_enviar_telegram_excecao_no_post_e_logada(monkeypatch, caplog):
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "y")

    def _boom(*a, **k):
        raise ConnectionError("timeout")

    monkeypatch.setattr(ts.requests, "post", _boom)
    with caplog.at_level("ERROR"):
        ts.enviar_telegram({"ticker": "PETR4", "gatilhos": ["g1"]})
    assert "Erro ao enviar Telegram" in caplog.text


def test_enviar_telegram_formata_put_e_mes_desconhecido(monkeypatch):
    capt = {}
    monkeypatch.setitem(ts.CONFIG, "telegram_token", "x")
    monkeypatch.setitem(ts.CONFIG, "telegram_chat_id", "y")
    monkeypatch.setattr(ts.requests, "post",
                         lambda url, data=None, timeout=None: capt.update(data) or object())
    ts.enviar_telegram({
        "ticker": "VALE3", "nome": "Vale", "tipo_sinal": "PUT",
        "mes_venc": 99, "ano_venc": 2026,  # mês inválido → NOMES_MESES.get retorna ""
        "strike_ref": 60.0, "dist_otm_pct": 4.5, "hv_20d": 28.0, "dte": 21,
        "entrada_min": 1.1, "entrada_max": 1.3, "alvo1": 1.5, "alvo2": 2.0,
        "stop": 0.8, "rr_alvo1": 0.6, "rr_alvo2": 1.2, "score_tecnico": 6,
        "bonus_sessao": 0, "score": 6, "gatilhos": ["queda", "rsi baixo"],
    })
    assert "PUT" in capt["text"]
    assert "queda" in capt["text"] and "rsi baixo" in capt["text"]


# ── load_telegram_config ────────────────────────────────────────────────────────

def test_load_telegram_config_prioriza_env_vars(monkeypatch):
    import backend.services.telegram_service as tg
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "env-chat")
    monkeypatch.setattr(tg, "get_supabase", lambda: None)
    tg.load_telegram_config()
    assert tg.CONFIG["telegram_token"] == "env-token"
    assert tg.CONFIG["telegram_chat_id"] == "env-chat"


def test_load_telegram_config_supabase_disponivel_sobrepoe_arquivo(monkeypatch):
    import backend.services.telegram_service as tg
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    class _FakeQuery:
        def select(self, *a, **k):
            return self
        def eq(self, *a, **k):
            return self
        def limit(self, *a, **k):
            return self
        def execute(self):
            return type("R", (), {"data": [{"token": "sb-token", "chat_id": "sb-chat"}]})()

    class _FakeTable:
        def select(self, *a, **k):
            return _FakeQuery()

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(tg, "get_supabase", lambda: _FakeSupabase())
    tg.load_telegram_config()
    assert tg.CONFIG["telegram_token"] == "sb-token"
    assert tg.CONFIG["telegram_chat_id"] == "sb-chat"


def test_load_telegram_config_supabase_excecao_cai_para_arquivo(monkeypatch, tmp_path, caplog):
    import backend.services.telegram_service as tg
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    class _FakeTable:
        def select(self, *a, **k):
            raise RuntimeError("falhou select")

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(tg, "get_supabase", lambda: _FakeSupabase())

    config_file = tmp_path / "telegram_config.json"
    config_file.write_text('{"token": "file-token", "chat_id": "file-chat"}')
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", str(config_file))

    with caplog.at_level("WARNING"):
        tg.load_telegram_config()

    assert "Falha ao ler telegram_config do Supabase" in caplog.text
    assert tg.CONFIG["telegram_token"] == "file-token"
    assert tg.CONFIG["telegram_chat_id"] == "file-chat"


def test_load_telegram_config_sem_supabase_le_arquivo_json(monkeypatch, tmp_path):
    import backend.services.telegram_service as tg
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(tg, "get_supabase", lambda: None)

    config_file = tmp_path / "telegram_config.json"
    config_file.write_text('{"token": "json-token", "chat_id": "json-chat"}')
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", str(config_file))

    tg.load_telegram_config()
    assert tg.CONFIG["telegram_token"] == "json-token"
    assert tg.CONFIG["telegram_chat_id"] == "json-chat"


def test_load_telegram_config_arquivo_ausente_nao_quebra(monkeypatch, tmp_path):
    import backend.services.telegram_service as tg
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(tg, "get_supabase", lambda: None)

    arquivo_inexistente = tmp_path / "nao-existe.json"
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", str(arquivo_inexistente))

    tg.load_telegram_config()  # FileNotFoundError tratado — não deve levantar


def test_load_telegram_config_arquivo_corrompido_loga_warning(monkeypatch, tmp_path, caplog):
    import backend.services.telegram_service as tg
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setattr(tg, "get_supabase", lambda: None)

    config_file = tmp_path / "telegram_config.json"
    config_file.write_text("{nao e json valido")
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", str(config_file))

    with caplog.at_level("WARNING"):
        tg.load_telegram_config()
    assert "Erro ao carregar telegram_config.json" in caplog.text


# ── save_telegram_config: fallback para arquivo ─────────────────────────────────

def test_save_telegram_config_sem_supabase_grava_arquivo(monkeypatch, tmp_path):
    import json

    import backend.services.telegram_service as tg
    monkeypatch.setattr(tg, "get_supabase", lambda: None)

    config_file = tmp_path / "telegram_config.json"
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", str(config_file))

    tg.save_telegram_config("tok2", "cid2")

    data = json.loads(config_file.read_text())
    assert data == {"token": "tok2", "chat_id": "cid2"}


def test_save_telegram_config_supabase_excecao_cai_para_arquivo(monkeypatch, tmp_path, caplog):
    import json

    import backend.services.telegram_service as tg

    class _FakeTable:
        def upsert(self, row):
            raise RuntimeError("falhou upsert")

    class _FakeSupabase:
        def table(self, nome):
            return _FakeTable()

    monkeypatch.setattr(tg, "get_supabase", lambda: _FakeSupabase())

    config_file = tmp_path / "telegram_config.json"
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", str(config_file))

    with caplog.at_level("WARNING"):
        tg.save_telegram_config("tok3", "cid3")

    assert "Falha ao gravar telegram_config no Supabase" in caplog.text
    data = json.loads(config_file.read_text())
    assert data == {"token": "tok3", "chat_id": "cid3"}


def test_save_telegram_config_falha_ao_escrever_arquivo_e_logada(monkeypatch, tmp_path, caplog):
    import backend.services.telegram_service as tg

    monkeypatch.setattr(tg, "get_supabase", lambda: None)
    # diretório inexistente como "arquivo" → open() levanta erro de I/O
    caminho_invalido = str(tmp_path / "pasta-inexistente" / "telegram_config.json")
    monkeypatch.setattr(tg, "_TELEGRAM_CONFIG_FILE", caminho_invalido)

    with caplog.at_level("WARNING"):
        tg.save_telegram_config("tokX", "cidX")  # não deve levantar

    assert "Erro ao salvar telegram_config.json" in caplog.text

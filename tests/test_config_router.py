"""
Testes do router backend/api/routers/config.py (endpoints GET/POST /config/telegram).

Cobre:
  - GET /config/telegram: shape booleano da resposta, refletindo presença/ausência
    de token e chat_id em CONFIG (linha 12).
  - POST /config/telegram: grava token/chat_id em CONFIG e delega persistência a
    save_telegram_config (linhas 17-22), sem tocar em I/O real (Supabase/arquivo).
"""
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.config import CONFIG

client = TestClient(app)

_MOD = "backend.api.routers.config"


def _snapshot_telegram_config():
    return CONFIG.get("telegram_token"), CONFIG.get("telegram_chat_id")


def _restore_telegram_config(token, chat_id):
    CONFIG["telegram_token"] = token
    CONFIG["telegram_chat_id"] = chat_id


def test_get_telegram_retorna_false_quando_nao_configurado():
    """Sem token/chat_id em CONFIG, GET deve retornar {token: false, chat_id: false}."""
    saved = _snapshot_telegram_config()
    try:
        CONFIG["telegram_token"] = ""
        CONFIG["telegram_chat_id"] = ""
        response = client.get("/config/telegram")
    finally:
        _restore_telegram_config(*saved)

    assert response.status_code == 200
    assert response.json() == {"token": False, "chat_id": False}


def test_get_telegram_retorna_true_quando_configurado():
    """Com token/chat_id não vazios em CONFIG, GET deve retornar ambos True
    — o endpoint expõe apenas a presença da config, nunca o valor (segurança)."""
    saved = _snapshot_telegram_config()
    try:
        CONFIG["telegram_token"] = "123456:ABC-DEF"
        CONFIG["telegram_chat_id"] = "-100123456"
        response = client.get("/config/telegram")
    finally:
        _restore_telegram_config(*saved)

    assert response.status_code == 200
    data = response.json()
    assert data == {"token": True, "chat_id": True}
    # Garante que o valor real do token nunca é exposto na resposta.
    assert "123456:ABC-DEF" not in response.text


def test_get_telegram_parcialmente_configurado():
    """Apenas token setado, sem chat_id → token=True, chat_id=False."""
    saved = _snapshot_telegram_config()
    try:
        CONFIG["telegram_token"] = "123456:ABC-DEF"
        CONFIG["telegram_chat_id"] = ""
        response = client.get("/config/telegram")
    finally:
        _restore_telegram_config(*saved)

    assert response.status_code == 200
    assert response.json() == {"token": True, "chat_id": False}


def test_post_telegram_atualiza_config_e_persiste():
    """POST deve gravar token/chat_id em CONFIG e chamar save_telegram_config
    com os mesmos valores recebidos no payload (linhas 17-21)."""
    saved = _snapshot_telegram_config()
    try:
        with patch(f"{_MOD}.save_telegram_config") as mock_save:
            response = client.post(
                "/config/telegram",
                json={"token": "novo-token-999", "chat_id": "55512345"},
            )

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert CONFIG["telegram_token"] == "novo-token-999"
        assert CONFIG["telegram_chat_id"] == "55512345"
        mock_save.assert_called_once_with("novo-token-999", "55512345")
    finally:
        _restore_telegram_config(*saved)


def test_post_telegram_payload_vazio_usa_strings_vazias():
    """Payload sem 'token'/'chat_id' não deve quebrar — defaults são strings
    vazias (config.get('token', ''))."""
    saved = _snapshot_telegram_config()
    try:
        with patch(f"{_MOD}.save_telegram_config") as mock_save:
            response = client.post("/config/telegram", json={})

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert CONFIG["telegram_token"] == ""
        assert CONFIG["telegram_chat_id"] == ""
        mock_save.assert_called_once_with("", "")
    finally:
        _restore_telegram_config(*saved)


def test_post_telegram_test_delega_para_enviar_mensagem_teste():
    """POST /config/telegram/test delega a enviar_mensagem_teste e devolve o
    dict de status como está (sucesso)."""
    with patch(f"{_MOD}.enviar_mensagem_teste", return_value={"ok": True}) as mock_env:
        response = client.post("/config/telegram/test")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_env.assert_called_once_with()


def test_post_telegram_test_propaga_erro():
    """Falha (ex.: credencial inválida) volta como {ok: false, erro: ...}."""
    with patch(f"{_MOD}.enviar_mensagem_teste",
               return_value={"ok": False, "erro": "token/chat_id não configurado"}):
        response = client.post("/config/telegram/test")

    assert response.status_code == 200
    assert response.json() == {"ok": False, "erro": "token/chat_id não configurado"}


def test_post_telegram_test_card_delega_para_enviar_card_exemplo():
    """POST /config/telegram/test-card delega a enviar_card_exemplo."""
    with patch(f"{_MOD}.enviar_card_exemplo", return_value={"ok": True}) as mock_card:
        response = client.post("/config/telegram/test-card")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    mock_card.assert_called_once_with()


def test_post_telegram_get_reflete_atualizacao():
    """Fluxo ponta a ponta: POST grava config; GET subsequente reflete a
    mudança (token/chat_id passam a True) sem persistência real."""
    saved = _snapshot_telegram_config()
    try:
        with patch(f"{_MOD}.save_telegram_config"):
            post_resp = client.post(
                "/config/telegram",
                json={"token": "abc", "chat_id": "xyz"},
            )
        assert post_resp.status_code == 200

        get_resp = client.get("/config/telegram")
        assert get_resp.status_code == 200
        assert get_resp.json() == {"token": True, "chat_id": True}
    finally:
        _restore_telegram_config(*saved)

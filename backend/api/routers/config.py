"""Endpoints de configuração (Telegram)."""
from fastapi import APIRouter

from backend.core.config import CONFIG
from backend.services.telegram_service import enviar_mensagem_teste, save_telegram_config

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/telegram")
def get_telegram():
    return {"token": bool(CONFIG.get("telegram_token")), "chat_id": bool(CONFIG.get("telegram_chat_id"))}


@router.post("/telegram")
def set_telegram(config: dict):
    token = config.get("token", "")
    chat_id = config.get("chat_id", "")
    CONFIG["telegram_token"] = token
    CONFIG["telegram_chat_id"] = chat_id
    save_telegram_config(token, chat_id)
    return {"ok": True}


@router.post("/telegram/test")
def test_telegram():
    """Dispara uma mensagem de teste ao chat configurado para validar as
    credenciais na hora (sem esperar o próximo scan). Retorna {ok: true} ou
    {ok: false, erro: <motivo>} — nunca expõe o token."""
    return enviar_mensagem_teste()

"""Endpoints de configuração (Telegram)."""
from fastapi import APIRouter

from backend.core.config import CONFIG
from backend.services.telegram_service import save_telegram_config

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

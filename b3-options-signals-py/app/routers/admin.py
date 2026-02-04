from fastapi import APIRouter, HTTPException
from app.services.alerts import alert_service
import os

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/test-alert")
async def test_telegram_alert():
    """
    Send a test alert to verify Telegram bot configuration.
    Public endpoint for testing (no auth required).
    """
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        raise HTTPException(
            status_code=400, 
            detail="Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
        )
    
    # Sample signal for testing
    test_signal = {
        "ticker": "PETR4",
        "strategy": "Compra a Seco de Call",
        "option_symbol": "PETRA3800",
        "spot_price": 37.52,
        "signal_type": "BUY",
        "reason": "🧪 TESTE: Verificando configuração do bot",
        "recommendation": "Este é um alerta de teste",
        "timestamp": "Agora",
        "risk_info": {
            "level": "HIGH",
            "icon": "🔴",
            "max_loss": "Prêmio Pago (100%)",
            "description": "Teste de alerta"
        }
    }
    
    await alert_service.send_signal(test_signal)
    
    return {
        "message": "Test alert sent! Check your Telegram.",
        "signal": test_signal
    }

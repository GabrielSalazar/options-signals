import asyncio
from unittest.mock import MagicMock, patch
import os

# Set dummy env vars before importing service
os.environ["TELEGRAM_BOT_TOKEN"] = "dummy_token"
os.environ["TELEGRAM_CHAT_ID"] = "123456"

from app.services.alerts import alert_service

async def test_rich_alert():
    print("🚀 Testando Formatação de Alerta Rico (Telegram)...")
    
    # Mock para não enviar de verdade
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        
        # Dados de exemplo completos (como viria do scanner + filters)
        signal_data = {
            "strategy": "Venda de Put (Cash Secured)",
            "ticker": "PETR4",
            "spot_price": 34.50,
            "signal_type": "SELL PUT",
            "confidence_score": 85,
            "risk_level": "LOW",
            "risk_info": {
                "icon": "🟢",
                "max_loss": "Strike x 100 - Prêmio",
                "level": "LOW"
            },
            "risk_flags": ["⚠️ Baixa Liquidez", "⏰ Expira em Breve"],
            "recommendation": "Vender Put OTM",
            "reason": "RSI sobrevendido e Suporte forte",
            "technicals": {
                "rsi": 28.5,
                "iv": 0.45
            },
            "option_symbol": "PETRO330",
            "legs": [
                {"type": "put", "strike": 33.00, "action": "SELL", "delta": -0.25}
            ]
        }
        
        await alert_service.send_signal(signal_data)
        
        # Captura o payload enviado
        if mock_post.called:
            kwargs = mock_post.call_args[1]
            json_body = kwargs['json']
            print("\n---------- PAYLOAD HTML GERADO ----------")
            print(json_body['text'])
            print("-----------------------------------------")
            
            # Validações básicas
            assert "🚨 <b>B3 OPTIONS SIGNAL</b> 🚨" in json_body['text']
            assert "🟢 EXCELENTE (85/100)" in json_body['text']
            assert "RSI 28" in json_body['text']
            assert "• ⚠️ Baixa Liquidez" in json_body['text']
            print("\n✅ Validações de conteúdo passaram!")
        else:
            print("❌ O método post não foi chamado!")

if __name__ == "__main__":
    asyncio.run(test_rich_alert())

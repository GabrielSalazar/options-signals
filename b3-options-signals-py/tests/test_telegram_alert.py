import pytest
from unittest.mock import AsyncMock, patch
from app.services.alerts import alert_service

@pytest.mark.asyncio
async def test_send_telegram_signal():
    # Mock data
    signal_data = {
        "ticker": "PETR4",
        "strategy": "High IV Reversal",
        "option_symbol": "PETRA300",
        "strike": 30.00,
        "spot_price": 28.50,
        "type": "CALL",
        "recommended_action": "Venda Coberta",
        "entry_price": 1.50,
        "explanation": "Test explanation"
    }
    
    # Mock environment variables for the test
    with patch("os.getenv") as mock_env:
        mock_env.return_value = "fake_token"
        
        # Manually set attributes since __init__ might have run before patch
        alert_service.bot_token = "fake_token"
        alert_service.chat_id = "fake_chat_id"
        
        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value.status_code = 200
            
            await alert_service.send_signal(signal_data)
            
            # Assertions
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            url = call_args[0][0]
            payload = call_args[1]['json']
            
            assert "api.telegram.org/botfake_token/sendMessage" in url
            assert payload['chat_id'] == "fake_chat_id"
            assert "PETR4" in payload['text']
            assert "High IV Reversal" in payload['text']
            assert "PETRA300" in payload['text']
            assert "HTML" == payload['parse_mode']
            print("\nTest Passed: Telegram API called correctly with expected payload.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_send_telegram_signal())

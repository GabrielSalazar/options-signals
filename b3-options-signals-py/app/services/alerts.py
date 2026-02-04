import os
import logging
import httpx
import asyncio

class MultiChannelAlertService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Telegram Config
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        # WhatsApp Config (Generic API)
        self.whatsapp_url = os.getenv("WHATSAPP_API_URL")
        self.whatsapp_key = os.getenv("WHATSAPP_API_KEY")
        self.whatsapp_phone = os.getenv("WHATSAPP_TARGET_PHONE")

    async def send_signal(self, signal_data: dict):
        """
        Dispatch signal to all configured channels.
        """
        tasks = []
        
        if self.telegram_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(signal_data))
        else:
            self.logger.warning("Telegram not configured. Skipping.")

        if self.whatsapp_url and self.whatsapp_phone:
            tasks.append(self._send_whatsapp(signal_data))
        else:
             # Log only if both are missing to avoid spamming logs if user only wants one
             if not (self.telegram_token and self.telegram_chat_id):
                 print(f"[NO ALERTS CONFIGURED]: {signal_data['ticker']} - {signal_data['strategy']}")
        
        if tasks:
            await asyncio.gather(*tasks)

    async def _send_telegram(self, signal_data: dict):
        try:
            type_emoji = "🟢" if signal_data.get('type') == 'CALL' else "🔴"
            message = (
                f"<b>🚨 SINAL DETECTADO {type_emoji}</b>\n\n"
                f"📈 <b>Ativo:</b> {signal_data['ticker']}\n"
                f"🎯 <b>Estratégia:</b> {signal_data['strategy']}\n"
                f"🏷️ <b>Opção:</b> <code>{signal_data['option_symbol']}</code>\n"
                f"💰 <b>Strike:</b> R$ {signal_data['strike']:.2f}\n"
                f"💵 <b>Preço Spot:</b> R$ {signal_data['spot_price']:.2f}\n\n"
                f"💡 <b>Recomendação:</b> {signal_data.get('recommended_action', 'N/A')}\n"
                f"⚠️ <b>Sugestão de Entrada:</b> R$ {signal_data.get('entry_price', 0):.2f}\n\n"
                f"<i>{signal_data.get('explanation', '')}</i>"
            )

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "HTML"}

            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, timeout=10.0)
                if res.status_code == 200:
                    print(f"[TELEGRAM SENT]: {signal_data['ticker']}")
                else:
                    print(f"[TELEGRAM ERROR]: {res.text}")
        except Exception as e:
            self.logger.error(f"Telegram failed: {e}")

    async def _send_whatsapp(self, signal_data: dict):
        try:
            # WhatsApp usually doesn't support HTML, using basic formatting
            message = (
                f"🚨 *SINAL DETECTADO* 🚨\n\n"
                f"📈 *Ativo:* {signal_data['ticker']}\n"
                f"🎯 *Estratégia:* {signal_data['strategy']}\n\n"
                f"💡 *Recomendação:* {signal_data.get('recommended_action', 'N/A')}\n"
                f"💰 *Preço Spot:* R$ {signal_data['spot_price']:.2f}\n"
                f"🏷️ *Opção:* {signal_data['option_symbol']} (Strike: {signal_data['strike']:.2f})\n"
                f"⚠️ *Entrada Sugerida:* R$ {signal_data.get('entry_price', 0):.2f}\n"
            )
            
            payload = {
                "number": self.whatsapp_phone,
                "text": message,
                "options": {"delay": 1200, "presence": "composing"}
            }
            headers = {"apikey": self.whatsapp_key} if self.whatsapp_key else {}
            
            async with httpx.AsyncClient() as client:
                res = await client.post(self.whatsapp_url, json=payload, headers=headers, timeout=10.0)
                if res.status_code in [200, 201]:
                    print(f"[WHATSAPP SENT]: {signal_data['ticker']}")
                else:
                    print(f"[WHATSAPP ERROR]: {res.text}")
        except Exception as e:
            self.logger.error(f"WhatsApp failed: {e}")

alert_service = MultiChannelAlertService()



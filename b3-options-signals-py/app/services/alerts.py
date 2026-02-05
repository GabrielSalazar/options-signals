import os
import logging
import httpx
import asyncio
from datetime import datetime
import pytz

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
        
        if tasks:
            await asyncio.gather(*tasks)

    def _format_confidence(self, score: int) -> str:
        if score >= 80: return f"🟢 EXCELENTE ({score}/100)"
        if score >= 60: return f"🟡 BOM ({score}/100)"
        return f"⚪ NEUTRO ({score}/100)"

    async def _send_telegram(self, signal_data: dict):
        """
        Send rich signal alert to Telegram.
        """
        max_retries = 3
        retry_delay = 1
        
        try:
            # Extract Data
            risk_info = signal_data.get('risk_info', {})
            technicals = signal_data.get('technicals', {})
            risk_flags = signal_data.get('risk_flags', [])
            score = signal_data.get('confidence_score', 50)
            
            # Icons
            risk_icon = risk_info.get('icon', '🟡')
            
            # Format Flags
            flags_html = ""
            if risk_flags:
                flags_html = "\n<b>⚠️ Atenção:</b>\n" + "\n".join([f"• {flag}" for flag in risk_flags]) + "\n"

            # Format Legs (if strategy is structural)
            legs = signal_data.get('legs', [])
            legs_html = ""
            if len(legs) > 1:
                legs_formatted = []
                for leg in legs:
                    action = "Compra" if 'BUY' in leg.get('action', '').upper() else "Venda"
                    legs_formatted.append(f"• {action} {leg['type'].upper()} Strike {leg['strike']}")
                legs_html = f"<b>🛠️ Estrutura:</b>\n" + "\n".join(legs_formatted) + "\n"
            
            # Timestamp (Brasília)
            tz = pytz.timezone('America/Sao_Paulo')
            time_now = datetime.now(tz).strftime('%H:%M:%S')

            # Message Template
            message = (
                f"🚨 <b>B3 OPTIONS SIGNAL</b> 🚨\n\n"
                
                f"🎯 <b>{signal_data['strategy']}</b>\n"
                f"📊 <b>{signal_data['ticker']}</b> • R$ {signal_data['spot_price']:.2f}\n\n"
                
                f"🔥 <b>Confiança:</b> {self._format_confidence(score)}\n"
                f"{risk_icon} <b>Risco:</b> {signal_data.get('risk_level', 'MEDIO')}\n"
                f"⚖️ <b>Max Loss:</b> {risk_info.get('max_loss', 'N/A')}\n\n"
                
                f"🏷️ <b>Sinal:</b> {signal_data.get('signal_type', 'ACTION')}\n"
                f"📦 <b>Opção Principal:</b> <code>{signal_data.get('option_symbol', 'N/A')}</code>\n"
                f"💡 <b>Motivo:</b> {signal_data.get('reason', 'N/A')}\n\n"
                
                f"📉 <b>Técnicos:</b> RSI {technicals.get('rsi', 0):.0f} • IV {technicals.get('iv', 0):.2f}\n"
                f"{flags_html}\n"
                f"{legs_html}\n"
                
                f"<i>🕒 {time_now} • B3 Real-Time Scan</i>"
            )

            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id, 
                "text": message, 
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }

            async with httpx.AsyncClient() as client:
                for attempt in range(max_retries):
                    res = await client.post(url, json=payload, timeout=10.0)
                    if res.status_code == 200:
                        self.logger.info(f"Telegram sent for {signal_data['ticker']}")
                        return
                    else:
                        self.logger.warning(f"Telegram failed ({res.status_code}). Retry {attempt+1}...")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        
        except Exception as e:
            self.logger.error(f"Error sending telegram alert: {e}")

    async def _send_whatsapp(self, signal: dict):
        pass # Not implemented yet

alert_service = MultiChannelAlertService()

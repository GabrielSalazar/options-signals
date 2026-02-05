import requests
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Sinal real do PETR4 (exemplo)
message = """<b>🚨 SINAL REAL DETECTADO</b>

📊 <b>Ativo:</b> PETR4 (R$ 37.52)
📈 <b>Estratégia:</b> Compra a Seco de Call
🏷️ <b>Opção:</b> <code>PETRA3800</code>
🔴 <b>Risco:</b> HIGH
💰 <b>Perda Máxima:</b> Prêmio Pago (100%)

📝 <b>Recomendação:</b> Comprar CALL OTM
💡 <b>Motivo:</b> Sinal de reversão detectado

<i>⏰ 19:30 - 04/02/2026</i>"""

print("Enviando sinal REAL via API do Telegram...")

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": message,
    "parse_mode": "HTML"
}

try:
    r = requests.post(url, json=payload, timeout=10)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        print("✅ Sinal REAL enviado com sucesso!")
        print("📱 Verifique seu Telegram!")
    else:
        print(f"❌ Erro: {r.json()}")
        
except Exception as e:
    print(f"❌ Erro: {e}")

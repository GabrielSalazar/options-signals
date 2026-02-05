import requests
import os
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"Token: {token[:20]}...")
print(f"Chat ID: {chat_id}")
print("\nTestando envio direto para API do Telegram...")

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": "🧪 TESTE DIRETO - Se você recebeu esta mensagem, o bot está funcionando!",
    "parse_mode": "HTML"
}

try:
    r = requests.post(url, json=payload, timeout=10)
    print(f"\nStatus: {r.status_code}")
    print(f"Response: {r.json()}")
    
    if r.status_code == 200:
        print("\n✅ Mensagem enviada com sucesso!")
        print("📱 Verifique seu Telegram!")
    else:
        print(f"\n❌ Erro: {r.json()}")
        if "description" in r.json():
            print(f"Descrição: {r.json()['description']}")
            
except Exception as e:
    print(f"\n❌ Exceção: {e}")

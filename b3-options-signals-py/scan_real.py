import requests
import time

print("🔍 Iniciando scan REAL do PETR4...")
print("Isso vai buscar dados do mercado e enviar alertas para o Telegram!\n")

try:
    r = requests.post(
        'http://127.0.0.1:8000/signals/scan/PETR4',
        headers={'Authorization': 'Bearer dev-mode'},
        timeout=60
    )
    
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"\n✅ Scan completado!")
        print(f"📊 Sinais encontrados: {data['signals_found']}")
        print(f"📱 Alertas enviados para o Telegram!")
        print(f"\nVerifique seu Telegram - você deve ter recebido {data['signals_found']} mensagens!")
    else:
        print(f"❌ Erro: {r.text}")
        
except Exception as e:
    print(f"❌ Erro: {e}")

import requests

print("Enviando alerta de teste para o Telegram...")

try:
    r = requests.post('http://127.0.0.1:8000/admin/test-alert', timeout=10)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        print("✅ Alerta enviado com sucesso!")
        print("📱 Verifique seu Telegram agora!")
    else:
        print(f"Erro: {r.text}")
except Exception as e:
    print(f"Erro: {e}")

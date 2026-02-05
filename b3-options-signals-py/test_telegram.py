import requests

print("Iniciando scan do PETR4...")

response = requests.post(
    'http://127.0.0.1:8000/signals/scan/PETR4',
    headers={'Authorization': 'Bearer dev-mode'}
)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"Sinais encontrados: {data['signals_found']}")
    print(f"Ticker: {data['message']}")
    print("\nAlertas enviados para o Telegram!")
    print("Verifique seu Telegram agora!")
else:
    print(f"Erro: {response.text}")

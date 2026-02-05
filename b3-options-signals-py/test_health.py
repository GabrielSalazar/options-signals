import requests

try:
    print("Testing server health...")
    r = requests.get('http://127.0.0.1:8000/health', timeout=5)
    print(f"Health check: {r.status_code} - {r.json()}")
    
    print("\nTesting strategies endpoint...")
    r2 = requests.get('http://127.0.0.1:8000/signals/strategies', timeout=5)
    print(f"Strategies: {r2.status_code}")
    if r2.status_code == 200:
        print(f"Found {len(r2.json()['active_strategies'])} strategies")
    
except Exception as e:
    print(f"Error: {e}")

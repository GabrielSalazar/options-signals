import requests
import json

try:
    print("Testing /signals/strategies...")
    r = requests.get('http://127.0.0.1:8000/signals/strategies', timeout=10)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"Success! Found {len(data['active_strategies'])} strategies")
        print(f"First strategy: {data['active_strategies'][0]['name']}")
    else:
        print(f"Error response: {r.text}")
        
except Exception as e:
    print(f"Exception: {e}")

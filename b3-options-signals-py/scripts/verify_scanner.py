import sys
import os
import asyncio

# Fix path to include app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.scanner import scanner

async def main():
    print("--- Verifying Strategy Scanner ---")
    print(f"Loaded {len(scanner.strategies)} strategies.")
    
    ticker = "PETR4"
    print(f"\nScanning {ticker} with mock data...")
    
    signals = await scanner.scan_ticker(ticker)
    
    print(f"\nFound {len(signals)} signals:")
    for i, s in enumerate(signals, 1):
        print(f"{i}. [{s['strategy']}] {s['signal_type']} @ {s['option_symbol']}")
        print(f"   Reason: {s['reason']}")
        print(f"   Rec: {s.get('recommended_action', 'N/A')}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())

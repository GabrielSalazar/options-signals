import sys
import os
import asyncio

# Fix path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.backtester import VectorizedBacktester
from app.core.strategies_vectorized import RSIStrategy

async def main():
    print("--- Running Backtest ---")
    ticker = "PETR4"
    strategy = RSIStrategy()
    
    bt = VectorizedBacktester()
    print(f"Strategy: {strategy.name}")
    print(f"Ticker: {ticker}")
    print("Simulating last 90 days...")
    
    result = await bt.run_backtest(strategy, ticker, days=90)
    
    print("\n--- Results ---")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Win Rate: {result['win_rate']}%")
    print(f"Est. Return: {result['total_return']} (Normalized)" if 'total_return' in result else f"Est. Return: {result.get('total_return_pct')}%")
    
    if result.get('trades_log'):
        print("\nLast 5 Trades:")
        for t in result['trades_log']:
            print(f"  {t['entry_date'].date()} -> {t['exit_date'].date()} | {t['type']} | PnL: {round(t['pnl_option']*100, 1)}% ({t['reason']})")

if __name__ == "__main__":
    asyncio.run(main())

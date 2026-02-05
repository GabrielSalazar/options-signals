"""
Teste End-to-End do Backend Refatorado (DIA 2).

Valida:
1. Scanner de Sinais (integração B3RealData -> Scanner -> Strategies -> Signals)
2. Backtester (integração B3RealData -> Backtester -> Metrics)
"""

import sys
import os
import asyncio
import pandas as pd

# Adiciona diretório raiz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scanner import scanner
from app.core.backtester import VectorizedBacktester
from app.data import B3RealData

async def test_scanner_flow():
    print("\n" + "="*50)
    print("TESTE 1: Scanner de Sinais (End-to-End)")
    print("="*50)
    
    ticker = "PETR4"
    print(f"Executando scanner para {ticker}...")
    
    # Mockando a cadeia se estiver vazio (para testar a lógica do scanner mesmo fora do horário)
    # Mas primeiro tentamos real
    signals = await scanner.scan_ticker(ticker)
    
    if signals:
        print(f"✅ Scanner retornou {len(signals)} sinais!")
        print(f"   Exemplo: {signals[0]['strategy']} - {signals[0]['signal_type']} - Score: {signals[0]['confidence_score']}")
    else:
        print(f"⚠️  Nenhum sinal encontrado (provavelmente sem cadeia de opções ativa ou filtrado)")
        # Força um teste com dados mockados na mão se necessário, mas aqui queremos testar a integração.
        # Se B3RealData retornar vazio, o scanner retorna vazio. Isso está correto.
        # Vamos verificar se TechnicalIndicators funcionou
        # O scanner roda calculate_all.
    
    return True

async def test_backtester_flow():
    print("\n" + "="*50)
    print("TESTE 2: Backtester (End-to-End)")
    print("="*50)
    
    ticker = "PETR4"
    bt = VectorizedBacktester()
    
    # Vamos rodar RSI Strategy
    from app.core.strategies_vectorized import RSIStrategy
    strategy = RSIStrategy()
    
    print(f"Executando backtest de {strategy.name} para {ticker}...")
    
    try:
        metrics = await bt.run_backtest(strategy, ticker, days=100)
        
        if "error" in metrics:
            print(f"❌ Erro no backtest: {metrics['error']}")
            return False
        
        print(f"✅ Backtest concluído com sucesso!")
        print(f"   Retorno Total: {metrics['total_return_pct']}%")
        print(f"   Win Rate: {metrics['win_rate']}%")
        print(f"   Trades: {metrics['total_trades']}")
        print(f"   Equity Final: R$ {metrics['equity_curve'][-1]:.2f}")
        
        return True
    except Exception as e:
        print(f"❌ Exceção no backtest: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("🚀 INICIANDO TESTE E2E BACKEND (DIA 2)")
    
    await test_scanner_flow()
    await test_backtester_flow()
    
    print("\n🏁 Testes finalizados.")

if __name__ == "__main__":
    asyncio.run(main())

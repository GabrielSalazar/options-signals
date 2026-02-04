from app.services.b3_service import B3Service
from app.services.alerts import alert_service
# Import the new Vectorized Strategies
from app.core.strategies_vectorized import (
    HighIVStrategy, DeltaHedgeStrategy, RSIStrategy, CoveredCallStrategy,
    LongCallStrategy, LongPutStrategy, CashSecuredPutStrategy,
    BullCallSpreadStrategy, BearPutSpreadStrategy,
    LongStraddleStrategy, IronCondorStrategy,
    StrangleStrategy, ButterflyStrategy, IronButterflyStrategy,
    CalendarSpreadStrategy, DiagonalSpreadStrategy, CollarStrategy,
    ProtectivePutStrategy, JadeLizardStrategy, ShortStrangleStrategy
)
import asyncio
import pandas as pd
import numpy as np

class SignalScanner:
    def __init__(self):
        self.strategies = [
            HighIVStrategy(),
            DeltaHedgeStrategy(),
            RSIStrategy(),
            CoveredCallStrategy(),
            LongCallStrategy(),
            LongPutStrategy(),
            CashSecuredPutStrategy(),
            BullCallSpreadStrategy(),
            BearPutSpreadStrategy(),
            LongStraddleStrategy(),
            IronCondorStrategy(),
            StrangleStrategy(),
            ButterflyStrategy(),
            IronButterflyStrategy(),
            CalendarSpreadStrategy(),
            DiagonalSpreadStrategy(),
            CollarStrategy(),
            ProtectivePutStrategy(),
            JadeLizardStrategy(),
            ShortStrangleStrategy()
        ]
        
        
    async def scan_ticker(self, ticker: str):
        """
        Executa todas as estratégias vetorizadas para um único ticker.
        """
        # 1. Busca Dados de Mercado (B3Service/B3Client Real)
        from app.services.b3_data import B3Client
        
        spot_price = B3Client.get_spot_price(ticker)
        print(f"Scanning {ticker}... Spot: {spot_price}")
        
        if spot_price == 0:
             print(f"Warning: Could not fetch spot price for {ticker}")
             # Em último caso, evita crash se não conseguir cotação
             import random
             spot_price = round(random.uniform(20.0, 40.0), 2)
        
        # Mock de RSI para teste da estratégia (TODO: Implementar RSI Real via PandasTA no B3Client)
        rsi = 25.0 
        ticker_data = {"ticker": ticker, "price": spot_price, "rsi": rsi}
        
        # 2. Gera DataFrame da Cadeia de Opções (REAL)
        chain_df = B3Client.get_option_chain(ticker)
        
        if chain_df.empty:
            print(f"No option chain found for {ticker}")
            return []

        all_signals = []
        
        # 3. Aplica Estratégias (Vetorizado)
        if not chain_df.empty:
            for strategy in self.strategies:
                try:
                    # Retorna DataFrame com sinais
                    signal_df = strategy.analyze(ticker_data, chain_df)
                    
                    if not signal_df.empty:
                        # Converte de volta para lista de dicts para o AlertService / API
                        # Iteramos apenas sobre os sinais encontrados (muito rápido)
                        for _, row in signal_df.iterrows():
                            signal_dict = {
                                "strategy": row.get('strategy', strategy.name),
                                "ticker": ticker,
                                "option_symbol": row['symbol'],
                                "spot_price": spot_price,
                                "signal_type": row.get('signal_type', 'SIGNAL'),
                                "reason": row.get('reason', 'Sinal detectado'),
                                "timestamp": "Now",
                                "recommendation": row.get('recommended_action', ''),
                                "risk_level": row.get('risk_level', strategy.risk_level)
                            }
                            
                            all_signals.append(signal_dict)
                            # Envia alerta (Fire and Forget)
                            await alert_service.send_signal(signal_dict)
                except Exception as e:
                    print(f"Error running strategy {strategy.name} on {ticker}: {e}")
                    continue
                    
        return all_signals

scanner = SignalScanner()

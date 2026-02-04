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
        # 1. Busca Dados de Mercado (B3Service)
        spot_price = B3Service.get_spot_price(ticker)
        if spot_price == 0:
             import random
             spot_price = round(random.uniform(20.0, 40.0), 2)
        
        # Mock de RSI para teste da estratégia
        rsi = 25.0 
        ticker_data = {"ticker": ticker, "price": spot_price, "rsi": rsi}
        
        # 2. Gera DataFrame da Cadeia de Opções (Simulado)
        # Em produção, isso viria da API da B3/Cedro/Nelogica
        chain_df = self._generate_mock_chain_df(ticker, spot_price)
        
        all_signals = []
        
        # 3. Aplica Estratégias (Vetorizado)
        if not chain_df.empty:
            for strategy in self.strategies:
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
                    
        return all_signals

    def _generate_mock_chain_df(self, ticker: str, spot_price: float) -> pd.DataFrame:
        """
        Gera um Pandas DataFrame representando a Cadeia de Opções.
        Simula strikes, preços e gregas básicos.
        """
        import random
        
        # Geração Vetorizada (Simulada)
        # Criamos ranges de strikes ao redor do preço spot
        start_strike = round(spot_price * 0.8, 2)
        end_strike = round(spot_price * 1.2, 2)
        strikes = np.arange(start_strike, end_strike, 0.50)
        
        n = len(strikes)
        
        # Cria DataFrames para Calls e Puts
        calls = pd.DataFrame({
            'symbol': [f"{ticker}A{int(k*10)}" for k in strikes],
            'type': 'call',
            'strike': strikes,
        })
        
        puts = pd.DataFrame({
            'symbol': [f"{ticker}M{int(k*10)}" for k in strikes],
            'type': 'put',
            'strike': strikes,
        })
        
        # Combina tudo em um único DF
        df = pd.concat([calls, puts], ignore_index=True)
        
        # Adiciona colunas comuns (Simulação)
        df['time_to_expiry'] = random.randint(15, 45) / 365.0
        df['bid'] = 1.0 # Mock
        df['ask'] = 1.1 # Mock
        
        return df
        """
        Generates a realistic mock option chain around the spot price.
        """
        import random
        chain = []
        
        # Generate strikes from -10% to +10%
        start_strike = round(spot_price * 0.9, 2)
        end_strike = round(spot_price * 1.1, 2)
        step = 0.50
        
        current_strike = start_strike
        while current_strike <= end_strike:
            # Randomize time to expiry (between 15 and 45 days)
            days_to_expiry = random.randint(15, 45)
            time_to_expiry_years = days_to_expiry / 365.0
            
            # Call Option
            chain.append({
                "symbol": f"{ticker}A{int(current_strike * 10)}", # Ex: PETRA300
                "type": "call",
                "strike": current_strike,
                "time_to_expiry_years": time_to_expiry_years
            })
            
            # Put Option
            chain.append({
                "symbol": f"{ticker}M{int(current_strike * 10)}", # Ex: PETRM300
                "type": "put",
                "strike": current_strike,
                "time_to_expiry_years": time_to_expiry_years
            })
            
            current_strike += step
            current_strike = round(current_strike, 2)
            
        return chain

scanner = SignalScanner()

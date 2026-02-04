from app.services.b3_service import B3Service
from app.services.alerts import alert_service
from app.core.strategies import HighIVStrategy, DeltaHedgeStrategy
import asyncio

class SignalScanner:
    def __init__(self):
        self.strategies = [
            HighIVStrategy(),
            DeltaHedgeStrategy()
        ]
        
    async def scan_ticker(self, ticker: str):
        """
        Run all strategies for a single ticker.
        """
        # 1. Fetch Market Data (Real or Mocked)
        spot_price = B3Service.get_spot_price(ticker)
        if spot_price == 0:
             # Fallback mock for demo if market is closed/unavailable
             import random
             spot_price = round(random.uniform(20.0, 40.0), 2)
        
        ticker_data = {"ticker": ticker, "price": spot_price}
        
        # 2. Fetch Option Chain (Mocked for now as we don't have a live B3 scraper yet)
        option_chain = self._generate_mock_chain(ticker, spot_price)
        
        all_signals = []
        
        # 3. Apply Strategies
        for strategy in self.strategies:
            signals = strategy.analyze(ticker_data, option_chain)
            if signals:
                for signal in signals:
                    all_signals.append(signal)
                    # 4. Send Alerts
                    await alert_service.send_signal(signal)
                    
        return all_signals

    def _generate_mock_chain(self, ticker: str, spot_price: float):
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

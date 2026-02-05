import yfinance as yf
import pandas as pd
from datetime import datetime

class B3Service:
    @staticmethod
    def get_spot_price(ticker: str) -> float:
        """
        Fetches real-time spot price from B3 via yfinance.
        """
        if not ticker.endswith(".SA"):
            ticker = f"{ticker}.SA"
            
        try:
            stock = yf.Ticker(ticker)
            # Fast fetch
            price = stock.fast_info['last_price']
            if price is None or str(price) == 'nan':
                 # Fallback to history
                 hist = stock.history(period="1d")
                 if not hist.empty:
                     price = hist['Close'].iloc[-1]
                 else:
                     return 0.0
            return round(price, 2)
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return 0.0

    @staticmethod
    def get_rsi(ticker: str, period: int = 14) -> float:
        """
        Calculates the Relative Strength Index (RSI) for a given ticker.
        """
        if not ticker.endswith(".SA"):
            ticker = f"{ticker}.SA"
            
        try:
            stock = yf.Ticker(ticker)
            # Fetch enough history for RSI (at least period + a bit more for smoothing)
            hist = stock.history(period="1mo")
            
            if hist.empty or len(hist) < period + 1:
                return 50.0 # Neutral fallback
                
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi.iloc[-1], 2)
        except Exception as e:
            print(f"Error calculating RSI for {ticker}: {e}")
            return 50.0 # Neutral fallback

    @staticmethod
    def get_option_chain_stub(ticker: str):
        """
        Placeholder for fetching option chain.
        In a real scenario, this would scrape B3 site or use an authorized API.
        Reference: https://github.com/Megas-MDN/Api-Series-Autorizadas-B3
        """
        # TODO: Implement scraper or connect to external API
        return []

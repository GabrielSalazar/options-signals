import yfinance as yf
import pandas as pd
from datetime import datetime

class B3Service:
    @staticmethod
    def get_spot_price(ticker: str) -> float:
        """
        Fetch current spot price from Yahoo Finance.
        Ex: ticker 'PETR4.SA'
        """
        try:
            full_ticker = f"{ticker}.SA" if not ticker.endswith(".SA") else ticker
            stock = yf.Ticker(full_ticker)
            # Fast fetch of recent data
            history = stock.history(period="1d")
            if not history.empty:
                return history['Close'].iloc[-1]
            return 0.0
        except Exception as e:
            print(f"Error fetching spot price for {ticker}: {e}")
            return 0.0

    @staticmethod
    def get_option_chain_stub(ticker: str):
        """
        Placeholder for fetching option chain.
        In a real scenario, this would scrape B3 site or use an authorized API.
        Reference: https://github.com/Megas-MDN/Api-Series-Autorizadas-B3
        """
        # TODO: Implement scraper or connect to external API
        return []

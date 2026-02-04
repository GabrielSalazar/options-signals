import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import re
import json

class B3Client:
    """
    Client for fetching B3 market data.
    Primary source for Options: Yahoo Finance -> StatusInvest -> Enhanced Mock
    Primary source for Spot: Yahoo Finance
    """
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    @staticmethod
    def get_spot_price(ticker: str) -> float:
        """
        Fetches the latest spot price for a ticker (e.g. PETR4)
        """
        try:
            # Try Yahoo Finance first (Fast & Reliable for delayed quotes)
            t = yf.Ticker(f"{ticker}.SA")
            # Get fast info
            price = t.fast_info.last_price
            if price and price > 0:
                return round(price, 2)
            
            # Fallback to history
            hist = t.history(period="1d")
            if not hist.empty:
                return round(hist['Close'].iloc[-1], 2)
                
            return 0.0
        except Exception as e:
            print(f"Error fetching spot price for {ticker}: {e}")
            return 0.0

    @staticmethod
    def get_option_chain(ticker: str) -> pd.DataFrame:
        """
        Fetches the full option chain for a ticker.
        Returns DataFrame with columns: 
        [symbol, type, strike, time_to_expiry, last, bid, ask]
        """
        try:
            print(f"Fetching option chain for {ticker}...")
            
            # ATTEMPT 1: Yahoo Finance (Cleanest API if data exists)
            yf_ticker = yf.Ticker(f"{ticker}.SA")
            expirations = yf_ticker.options
            
            if expirations:
                print(f"Found {len(expirations)} expiries in Yahoo Finance.")
                all_opts_clean = []
                today = datetime.now()
                
                # Fetch nearest 2 expiries to save time
                target_expiries = expirations[:2] 
                
                for expiry in target_expiries:
                    try:
                        opt = yf_ticker.option_chain(expiry)
                        expiry_date = pd.to_datetime(expiry)
                        dte = (expiry_date - today).days / 365.0
                        
                        for opt_type, data in [('call', opt.calls), ('put', opt.puts)]:
                            if data is not None and not data.empty:
                                temp = data.copy()
                                temp['type'] = opt_type
                                temp['expiry'] = expiry_date
                                temp['time_to_expiry'] = dte
                                all_opts_clean.append(temp)
                    except Exception as e:
                        print(f"Error fetching expiry {expiry}: {e}")
                        continue
                
                if all_opts_clean:
                    df = pd.concat(all_opts_clean)
                    df = df.rename(columns={'contractSymbol': 'symbol', 'lastPrice': 'last'})
                    df['symbol'] = df['symbol'].str.replace('.SA', '', regex=False)
                    
                    # Ensure bid/ask are valid
                    df['bid'] = df['bid'].fillna(df['last'])
                    df['ask'] = df['ask'].fillna(df['last'])
                    
                    return df[['symbol', 'type', 'strike', 'time_to_expiry', 'last', 'bid', 'ask']].reset_index(drop=True)
            
            print("Yahoo Finance options empty/failed. Trying StatusInvest scraping...")
            return B3Client._scrape_statusinvest(ticker)

        except Exception as e:
            print(f"Error in B3Client.get_option_chain: {e}")
            return B3Client._generate_enhanced_mock(ticker)

    @staticmethod
    def _scrape_statusinvest(ticker: str) -> pd.DataFrame:
        """
        Scrapes option chain from StatusInvest (API endpoint).
        """
        try:
            print(f"Scraping StatusInvest for {ticker}...")
            
            url = f"https://statusinvest.com.br/opcoes/e/{ticker.lower()}"
            response = requests.get(url, headers=B3Client.HEADERS, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    df = pd.DataFrame(data)
                    # Normalize columns (StatusInvest format)
                    df = df.rename(columns={
                        'osym': 'symbol',
                        'strikePrice': 'strike',
                        'price': 'last',
                        'saleExpirationDate': 'expiry',
                        'type': 'type'
                    })
                    return df
            
            print("StatusInvest Scraping failed (likely Cloudflare or API change). Reverting to Enhanced Mock.")
            return B3Client._generate_enhanced_mock(ticker)
            
        except Exception as e:
            print(f"Scraping error: {e}")
            return B3Client._generate_enhanced_mock(ticker)

    @staticmethod
    def _generate_enhanced_mock(ticker: str) -> pd.DataFrame:
        """
        Generates sensible mock data if APIs fail. 
        Uses real spot price from YFinance to center the strikes.
        """
        spot = B3Client.get_spot_price(ticker)
        if spot == 0: spot = 30.00
        
        strikes = np.arange(round(spot*0.8), round(spot*1.2), 0.5)
        chain = []
        for k in strikes:
            # Mock Call
            chain.append({
                'symbol': f"{ticker}A{int(k*100)}", 
                'type': 'call', 'strike': k, 
                'time_to_expiry': 20/365, 'last': max(0, spot-k)*0.5 + 0.1, 
                'bid': max(0, spot-k)*0.5, 'ask': max(0, spot-k)*0.5 + 0.2
            })
            # Mock Put
            chain.append({
                'symbol': f"{ticker}M{int(k*100)}", 
                'type': 'put', 'strike': k, 
                'time_to_expiry': 20/365, 'last': max(0, k-spot)*0.5 + 0.1, 
                'bid': max(0, k-spot)*0.5, 'ask': max(0, k-spot)*0.5 + 0.2
            })
        
        return pd.DataFrame(chain)

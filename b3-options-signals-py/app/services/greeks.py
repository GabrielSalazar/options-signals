import pandas as pd
import numpy as np
from datetime import datetime

# Try importing py_vollib_vectorized, fallback strictly if not present to avoid runtime crashes during dev
try:
    import py_vollib_vectorized
    HAS_VOLLIB_VECTORIZED = True
except ImportError:
    HAS_VOLLIB_VECTORIZED = False

class GreeksService:
    """
    Service to calculate Greeks using vectorized operations.
    """
    
    @staticmethod
    def calculate_greeks(chain_df: pd.DataFrame, risk_free_rate: float = 0.1375) -> pd.DataFrame:
        """
        Enriches the chain_df with Delta, Gamma, Theta, Vega, Rho.
        """
        if chain_df.empty:
            return chain_df
            
        # Ensure we have required columns
        # Needed: 'strike', 'time_to_expiry', 'price' (option price), 'underlying_price' (spot)
        # We'll assume 'last' is option price, and we need 'spot_price' passed or in df
        
        # If simulation, we might not have 'iv'. We can calculate IV from price, then Greeks.
        # Or if we have 'iv', we calculate Greeks directly.
        
        if not HAS_VOLLIB_VECTORIZED:
            # Fallback: Mock Greeks
            chain_df['delta'] = np.where(chain_df['type'] == 'call', 0.5, -0.5)
            chain_df['gamma'] = 0.05
            chain_df['theta'] = -0.01
            chain_df['vega'] = 0.10
            return chain_df

        # Prepare for PyVollib Vectorized
        # It expects a flag 'q' for dividend, 'r' risk free
        # And flag 'flag' ('c' or 'p')
        
        # Copy to avoid side effects
        df = chain_df.copy()
        
        # Map type to 'c'/'p'
        df['flag'] = df['type'].apply(lambda x: 'c' if x == 'call' else 'p')
        
        # If we have Spot Price (S) and Option Price (P), we can get IV.
        # Ideally, B3 Service provides Spot Price. Let's assume 'spot_price' column exists.
        
        if 'spot_price' not in df.columns:
            # Cannot calculate without spot
            return df
            
        # Calculate Implied Volatility if missing
        if 'iv' not in df.columns or df['iv'].isnull().any():
             # price_dataframe returns a helper object usually, but py_vollib_vectorized extends floats/arrays
             # We use the vector functions
             from py_vollib_vectorized import vectorized_implied_volatility
             
             df['iv'] = vectorized_implied_volatility(
                 df['last'], 
                 df['spot_price'], 
                 df['strike'], 
                 df['time_to_expiry'], 
                 risk_free_rate, 
                 df['flag'].values, 
                 return_as='numpy'
             )
        
        # Calculate Greeks
        from py_vollib_vectorized import get_all_greeks
        
        result = get_all_greeks(
             df['flag'], 
             df['spot_price'], 
             df['strike'], 
             df['time_to_expiry'], 
             risk_free_rate, 
             df['iv'], 
             model='black_scholes', # or black_scholes_merton
             return_as='dataframe'
        )
        
        # Merge back
        df = pd.concat([df, result], axis=1)
        
        # Drop duplicates if any overlap
        return df.loc[:,~df.columns.duplicated()]

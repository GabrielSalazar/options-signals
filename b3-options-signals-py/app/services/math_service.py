from py_vollib.black_scholes import black_scholes as bs
from py_vollib.black_scholes.greeks.analytical import delta, gamma, theta, vega, rho
import numpy as np

class OptionMath:
    @staticmethod
    def calculate_price(flag: str, S: float, K: float, t: float, r: float, sigma: float) -> float:
        """
        Calculate Black-Scholes price.
        flag: 'c' for call, 'p' for put
        S: Underlying Asset Price
        K: Strike Price
        t: Time to expiration (in years)
        r: Risk-free interest rate (decimal)
        sigma: Volatility (decimal)
        """
        try:
            return bs(flag.lower(), S, K, t, r, sigma)
        except Exception as e:
            print(f"Error calculating price: {e}")
            return 0.0

    @staticmethod
    def calculate_greeks(flag: str, S: float, K: float, t: float, r: float, sigma: float):
        """
        Calculate all main Greeks.
        """
        try:
            d = delta(flag.lower(), S, K, t, r, sigma)
            g = gamma(flag.lower(), S, K, t, r, sigma)
            th = theta(flag.lower(), S, K, t, r, sigma)
            v = vega(flag.lower(), S, K, t, r, sigma)
            rh = rho(flag.lower(), S, K, t, r, sigma)
            
            return {
                "delta": d,
                "gamma": g,
                "theta": th,
                "vega": v,
                "rho": rh
            }
        except Exception as e:
            print(f"Error calculating greeks: {e}")
            return None

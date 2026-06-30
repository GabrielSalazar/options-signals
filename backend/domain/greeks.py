"""
Greeks de Black-Scholes para opções B3.

Fornece Delta, Gamma, Theta (diário), Vega, Rho, POP (probabilidade de exercício)
e volatilidade implícita via Newton-Raphson.

Nota: como o preço da opção neste projeto é frequentemente ESTIMADO via Black-Scholes
(quando opcoes.net não retorna book real), a IV converge para a HV usada como input.
A função implied_volatility() está pronta para quando houver preço de mercado REAL.
"""
import math

from scipy.stats import norm

RISK_FREE_RATE_DEFAULT = 0.135  # Selic ~13,5% a.a.


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple:
    if sigma <= 0 or T <= 0 or S <= 0 or K <= 0:
        return 0.0, 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return d1, d2


def bs_call_price(S: float, K: float, T: float, r: float = RISK_FREE_RATE_DEFAULT,
                  sigma: float = 0.5) -> float:
    if T <= 0:
        return max(S - K, 0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    return float(S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2))


def bs_put_price(S: float, K: float, T: float, r: float = RISK_FREE_RATE_DEFAULT,
                 sigma: float = 0.5) -> float:
    if T <= 0:
        return max(K - S, 0.0)
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    return float(K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1))


def calculate_greeks(S: float, K: float, T: float, sigma: float,
                     opt_type: str = "CALL",
                     r: float = RISK_FREE_RATE_DEFAULT) -> dict:
    """
    Retorna Delta, Gamma, Theta (por dia), Vega (por 1% de IV), Rho (por 1% de r)
    e POP (probabilidade neutra de exercício).
    """
    if T <= 0 or sigma <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0,
                "vega": 0.0, "rho": 0.0, "prob_profit": 0.0}

    d1, d2 = _d1_d2(S, K, T, r, sigma)
    sqrt_T = math.sqrt(T)
    pdf_d1 = norm.pdf(d1)

    gamma = pdf_d1 / (S * sigma * sqrt_T)
    vega  = S * pdf_d1 * sqrt_T / 100  # por 1% de IV

    if opt_type.upper() == "CALL":
        delta = norm.cdf(d1)
        theta = (-(S * pdf_d1 * sigma) / (2 * sqrt_T)
                 - r * K * math.exp(-r * T) * norm.cdf(d2)) / 365
        rho   = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
        prob  = norm.cdf(d2)
    else:
        delta = norm.cdf(d1) - 1
        theta = (-(S * pdf_d1 * sigma) / (2 * sqrt_T)
                 + r * K * math.exp(-r * T) * norm.cdf(-d2)) / 365
        rho   = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100
        prob  = norm.cdf(-d2)

    return {
        "delta": round(float(delta), 4),
        "gamma": round(float(gamma), 6),
        "theta": round(float(theta), 6),
        "vega":  round(float(vega), 6),
        "rho":   round(float(rho), 6),
        "prob_profit": round(float(prob), 4),
    }


def implied_volatility(S: float, K: float, T: float, market_price: float,
                       opt_type: str = "CALL",
                       r: float = RISK_FREE_RATE_DEFAULT,
                       sigma_init: float = 0.5,
                       max_iter: int = 100, tol: float = 1e-6) -> float:
    """IV via Newton-Raphson. Útil quando há preço de mercado REAL."""
    if T <= 0 or market_price <= 0:
        return sigma_init
    sigma = sigma_init
    pricer = bs_call_price if opt_type.upper() == "CALL" else bs_put_price
    for _ in range(max_iter):
        price = pricer(S, K, T, r, sigma)
        d1, _ = _d1_d2(S, K, T, r, sigma)
        vega = S * norm.pdf(d1) * math.sqrt(T)
        if abs(vega) < 1e-10:
            break
        sigma -= (price - market_price) / vega
        sigma = max(0.01, min(sigma, 5.0))
        if abs(price - market_price) < tol:
            break
    return float(sigma)

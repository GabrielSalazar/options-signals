"""Generic option pricing engine using Black-Scholes.

This module provides parameterized pricing for ANY equity option,
independent of underlying ticker. All calculations use pure Black-Scholes
implemented with scipy and numpy.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from scipy.optimize import brentq
from scipy.stats import norm
import numpy as np

logger = logging.getLogger("option_pricing")


class OptionType(Enum):
    """Option type enum."""
    CALL = "C"
    PUT = "P"


@dataclass
class OptionInput:
    """Generic option parameters (ticker-agnostic)."""
    spot_price: float  # Current asset price
    strike_price: float  # Strike price
    time_to_expiry: float  # Years (e.g., 0.025 = 9 days)
    volatility: float  # Annualized (0.20 = 20%)
    risk_free_rate: float  # Annual rate (0.10 = 10%)
    dividend_yield: float = 0.0  # Annual dividend yield
    option_type: OptionType = OptionType.CALL


@dataclass
class OptionOutput:
    """Generic option pricing output."""
    premium: float  # Option price
    delta: float  # Delta
    gamma: float  # Gamma
    vega: float  # Vega (per 1% vol change)
    theta: float  # Theta (per day)
    rho: float  # Rho
    intrinsic_value: float  # Intrinsic value
    time_value: float  # Time value
    moneyness: float  # Spot / Strike


class OptionPricer:
    """
    Generic option pricing engine.

    Works with ANY underlying asset (stocks, indices, etc).
    Uses Black-Scholes-Merton model for vanilla options.

    Example:
        pricer = OptionPricer()

        # Price ANY CALL option
        result = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=105.0,
                time_to_expiry=0.025,  # 9 days
                volatility=0.25,  # 25% IV
                risk_free_rate=0.10,
                option_type=OptionType.CALL
            )
        )
        print(f"Premium: {result.premium:.2f}, Delta: {result.delta:.3f}")
    """

    def price(self, option_input: OptionInput) -> OptionOutput:
        """
        Price a vanilla option using Black-Scholes.

        Args:
            option_input: Generic option parameters

        Returns:
            OptionOutput with price and Greeks
        """
        S = option_input.spot_price
        K = option_input.strike_price
        T = option_input.time_to_expiry
        sigma = option_input.volatility
        r = option_input.risk_free_rate
        q = option_input.dividend_yield
        option_type = option_input.option_type

        # Handle edge cases
        if T <= 0:
            # Option expired
            if option_type == OptionType.CALL:
                intrinsic = max(S - K, 0)
            else:
                intrinsic = max(K - S, 0)
            return OptionOutput(
                premium=intrinsic,
                delta=1.0 if option_type == OptionType.CALL and S > K else 0.0,
                gamma=0.0,
                vega=0.0,
                theta=0.0,
                rho=0.0,
                intrinsic_value=intrinsic,
                time_value=0.0,
                moneyness=S / K if K > 0 else 1.0,
            )

        if sigma <= 0:
            logger.warning(f"Volatility <= 0: {sigma}, using 0.01 fallback")
            sigma = 0.01

        # Black-Scholes calculation
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        Nd1 = norm.cdf(d1)
        Nd2 = norm.cdf(d2)
        nd1 = norm.pdf(d1)
        n_minus_d2 = norm.cdf(-d2)
        n_minus_d1 = norm.pdf(-d1)

        # Premium
        if option_type == OptionType.CALL:
            premium = S * np.exp(-q * T) * Nd1 - K * np.exp(-r * T) * Nd2
        else:
            premium = K * np.exp(-r * T) * n_minus_d2 - S * np.exp(-q * T) * n_minus_d1

        # Greeks
        if option_type == OptionType.CALL:
            delta = np.exp(-q * T) * Nd1
            theta = (
                -S * np.exp(-q * T) * nd1 * sigma / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * Nd2
                + q * S * np.exp(-q * T) * Nd1
            ) / 365  # Per day
        else:
            delta = -np.exp(-q * T) * n_minus_d1
            theta = (
                -S * np.exp(-q * T) * nd1 * sigma / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * n_minus_d2
                - q * S * np.exp(-q * T) * n_minus_d1
            ) / 365  # Per day

        gamma = np.exp(-q * T) * nd1 / (S * sigma * np.sqrt(T))
        vega = S * np.exp(-q * T) * nd1 * np.sqrt(T) / 100  # Per 1% change
        rho = K * T * np.exp(-r * T) * Nd2 / 100  # Per 1% change (CALL)

        # Intrinsic and time values
        if option_type == OptionType.CALL:
            intrinsic = max(S - K, 0)
        else:
            intrinsic = max(K - S, 0)

        time_value = max(premium - intrinsic, 0)
        moneyness = S / K if K > 0 else 1.0

        return OptionOutput(
            premium=premium,
            delta=delta,
            gamma=gamma,
            vega=vega,
            theta=theta,
            rho=rho,
            intrinsic_value=intrinsic,
            time_value=time_value,
            moneyness=moneyness,
        )

    def implied_volatility(
        self,
        market_price: float,
        option_input: OptionInput,
        initial_guess: float = 0.30,
    ) -> Optional[float]:
        """
        Calculate implied volatility (IV) by inverting Black-Scholes.

        Uses Brent's method to find IV that matches market price.

        Args:
            market_price: Observed option market price
            option_input: Option parameters (volatility field ignored)
            initial_guess: Initial IV guess for solver

        Returns:
            Implied volatility, or None if solver fails
        """
        def objective(sigma):
            """Objective function: predicted price - market price."""
            modified_input = OptionInput(
                spot_price=option_input.spot_price,
                strike_price=option_input.strike_price,
                time_to_expiry=option_input.time_to_expiry,
                volatility=sigma,
                risk_free_rate=option_input.risk_free_rate,
                dividend_yield=option_input.dividend_yield,
                option_type=option_input.option_type,
            )
            predicted_price = self.price(modified_input).premium
            return predicted_price - market_price

        try:
            # Brent's method: robust root finder
            iv = brentq(objective, 0.001, 3.0, xtol=1e-6)
            return max(0.001, min(3.0, iv))  # Clamp to [0.1%, 300%]
        except ValueError:
            logger.warning(
                f"IV solver failed for market_price={market_price:.4f}, "
                f"spot={option_input.spot_price}, strike={option_input.strike_price}"
            )
            return None

    def calculate_pct_otm(self, option_input: OptionInput) -> float:
        """
        Calculate percentage out-of-the-money.

        For CALL: (Strike - Spot) / Spot * 100
        For PUT: (Spot - Strike) / Spot * 100

        Negative = ITM, Positive = OTM
        """
        S = option_input.spot_price
        K = option_input.strike_price

        if option_input.option_type == OptionType.CALL:
            return (K - S) / S * 100 if S > 0 else 0
        else:
            return (S - K) / S * 100 if S > 0 else 0

    def time_to_expiry_years(
        self,
        expiry_date: datetime,
        reference_date: Optional[datetime] = None,
    ) -> float:
        """
        Convert expiry date to years (decimal).

        Args:
            expiry_date: Option expiration datetime
            reference_date: Current datetime (default: now)

        Returns:
            Time in years (e.g., 0.025 = 9 business days ≈ 2.5% of year)
        """
        if reference_date is None:
            reference_date = datetime.now()

        delta = expiry_date - reference_date
        years = delta.total_seconds() / (365.25 * 24 * 3600)
        return max(0, years)

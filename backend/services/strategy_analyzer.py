"""Multi-leg option strategy analyzer and payoff calculator.

Análise de spreads, straddles, strangle, butterfly, iron condor.
Calcula P&L máximo, break-even, Greeks agregados.
Funciona com qualquer ativo subjacente (ticket-agnóstico).
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from backend.domain.option_pricing import OptionPricer, OptionInput, OptionType


class StrategyType(Enum):
    """Classificação de estratégia de múltiplas pernas."""
    CALL_SPREAD = "call_spread"  # Long call + short call OTM
    PUT_SPREAD = "put_spread"  # Long put + short put OTM
    STRADDLE = "straddle"  # Long call + long put (mesmo strike)
    STRANGLE = "strangle"  # Long call OTM + long put OTM
    IRON_CONDOR = "iron_condor"  # Sell call spread + sell put spread
    BUTTERFLY = "butterfly"  # Long + 2 shorts + long


@dataclass
class Leg:
    """Perna individual de uma estratégia multi-leg."""
    strike: float  # Strike price
    option_type: OptionType  # CALL ou PUT
    quantity: int  # +1 (long), -1 (short)
    premium: float  # Preço da opção (por unidade)
    dte: int  # Dias até expiração


@dataclass
class StrategyPayoff:
    """Payoff de uma estratégia em um ponto específico."""
    spot_price: float  # Preço do ativo
    strategy_pl: float  # P&L total (sem custo inicial)
    gross_pl: float  # P&L bruto (incluindo prêmios pagos/recebidos)


@dataclass
class StrategyMetrics:
    """Métricas agregadas de uma estratégia."""
    max_profit: float  # Lucro máximo possível
    max_loss: float  # Perda máxima possível
    breakeven: list[float]  # Pontos de break-even
    initial_cost: float  # Custo inicial (débit ou crédito)
    delta_at_spot: float  # Delta agregado no preço atual
    gamma_at_spot: float  # Gamma agregado no preço atual
    vega_at_spot: float  # Vega agregado no preço atual
    theta_at_spot: float  # Theta agregado no preço atual
    risk_reward_ratio: float  # Max reward / max risk


class StrategyAnalyzer:
    """Analisador de estratégias multi-leg de opções.

    Calcula payoff, Greeks, break-even e métricas de risco.
    """

    def __init__(self, spot_price: float, risk_free_rate: float = 0.10):
        """Inicializa analisador.

        Args:
            spot_price: Preço current do ativo subjacente
            risk_free_rate: Taxa livre de risco anual
        """
        self.spot_price = spot_price
        self.risk_free_rate = risk_free_rate
        self.pricer = OptionPricer()
        self.legs: list[Leg] = []

    def add_leg(
        self,
        strike: float,
        option_type: OptionType,
        quantity: int,
        premium: float,
        dte: int
    ) -> None:
        """Adiciona uma perna à estratégia.

        Args:
            strike: Strike price
            option_type: OptionType.CALL ou OptionType.PUT
            quantity: +1 para long, -1 para short
            premium: Preço pago/recebido por unidade
            dte: Dias até expiração
        """
        leg = Leg(
            strike=strike,
            option_type=option_type,
            quantity=quantity,
            premium=premium,
            dte=dte
        )
        self.legs.append(leg)

    def _price_leg_at_spot(self, leg: Leg, spot: float) -> float:
        """Calcula valor intrínseco de uma perna em um spot específico.

        Args:
            leg: Perna da estratégia
            spot: Preço do ativo

        Returns:
            Valor intrínseco (sem time value no vencimento)
        """
        if leg.option_type == OptionType.CALL:
            intrinsic = max(spot - leg.strike, 0)
        else:
            intrinsic = max(leg.strike - spot, 0)

        # Na expiração: tempo residual = 0
        return intrinsic * leg.quantity

    def payoff_at_expiration(self, spot_price: float) -> StrategyPayoff:
        """Calcula P&L da estratégia no vencimento.

        Args:
            spot_price: Preço do ativo no vencimento

        Returns:
            StrategyPayoff com P&L strategy e bruto
        """
        # P&L estratégico (intrínseco - prêmio pago)
        strategy_pl = sum(self._price_leg_at_spot(leg, spot_price) for leg in self.legs)

        # P&L bruto (estratégico + prêmios net iniciais)
        initial_cost = sum(leg.premium * leg.quantity for leg in self.legs)
        gross_pl = strategy_pl - initial_cost

        return StrategyPayoff(
            spot_price=spot_price,
            strategy_pl=strategy_pl,
            gross_pl=gross_pl
        )

    def calculate_breakevens(self) -> list[float]:
        """Calcula pontos de break-even da estratégia.

        Returns:
            Lista de break-even strikes
        """
        if not self.legs:
            return []

        # Busca break-even por método numérico (golden section search)
        breakevens = []

        # Range de busca: spot ± 3 * (strike range)
        strikes = [leg.strike for leg in self.legs]
        min_strike = min(strikes)
        max_strike = max(strikes)
        range_width = max_strike - min_strike or self.spot_price * 0.5

        search_min = min_strike - 2 * range_width
        search_max = max_strike + 2 * range_width

        # Busca break-evens
        def payoff_func(spot):
            return self.payoff_at_expiration(spot).gross_pl

        # Pontos candidatos: zeros aproximados
        test_points = np.linspace(search_min, search_max, 100)
        payoffs = [payoff_func(s) for s in test_points]

        for i in range(len(payoffs) - 1):
            # Se há mudança de sinal, há break-even
            if payoffs[i] * payoffs[i + 1] < 0:
                # Refina com interpolação linear
                s1, s2 = test_points[i], test_points[i + 1]
                p1, p2 = payoffs[i], payoffs[i + 1]
                be = s1 - p1 * (s2 - s1) / (p2 - p1)
                breakevens.append(be)

        return sorted(set(np.round(breakevens, 2)))  # Remove duplicates

    def compute_metrics(self, current_iv: float = 0.20, dividend_yield: float = 0.0) -> StrategyMetrics:
        """Computa métricas agregadas da estratégia.

        Args:
            current_iv: Volatilidade implícita para repricing
            dividend_yield: Dividend yield do ativo

        Returns:
            StrategyMetrics com análise completa
        """
        if not self.legs:
            raise ValueError("Strategy must have at least one leg")

        # Calcula P&L nos extremos
        min_strike = min(leg.strike for leg in self.legs)
        max_strike = max(leg.strike for leg in self.legs)
        range_width = max_strike - min_strike or self.spot_price * 0.5

        search_min = min_strike - 2 * range_width
        search_max = max_strike + 2 * range_width

        test_spots = np.linspace(search_min, search_max, 500)
        payoffs = [self.payoff_at_expiration(s).gross_pl for s in test_spots]

        max_profit = max(payoffs)
        max_loss = min(payoffs)

        # Break-evens
        breakevens = self.calculate_breakevens()

        # Initial cost (negative = credit spread, positive = debit spread)
        initial_cost = sum(leg.premium * leg.quantity for leg in self.legs)

        # Greeks agregados no spot current
        delta_agg = 0.0
        gamma_agg = 0.0
        vega_agg = 0.0
        theta_agg = 0.0

        for leg in self.legs:
            # Reprices each leg
            t_years = leg.dte / 365.0
            option_input = OptionInput(
                spot_price=self.spot_price,
                strike_price=leg.strike,
                time_to_expiry=t_years,
                volatility=current_iv,
                risk_free_rate=self.risk_free_rate,
                dividend_yield=dividend_yield,
                option_type=leg.option_type
            )

            pricing = self.pricer.price(option_input)

            # Acumula (lado do spread)
            delta_agg += pricing.delta * leg.quantity
            gamma_agg += pricing.gamma * leg.quantity
            vega_agg += pricing.vega * leg.quantity
            theta_agg += pricing.theta * leg.quantity

        # Risk/reward
        risk = max(abs(max_loss), 1e-6)
        reward = max(abs(max_profit), 1e-6)
        risk_reward_ratio = reward / risk if risk > 0 else 0.0

        return StrategyMetrics(
            max_profit=max_profit,
            max_loss=max_loss,
            breakeven=breakevens,
            initial_cost=initial_cost,
            delta_at_spot=delta_agg,
            gamma_at_spot=gamma_agg,
            vega_at_spot=vega_agg,
            theta_at_spot=theta_agg,
            risk_reward_ratio=risk_reward_ratio
        )

    def simulate_payoff_curve(
        self,
        spot_range_pct: float = 0.2
    ) -> tuple[list[float], list[float]]:
        """Simula curva de payoff ao redor do spot atual.

        Args:
            spot_range_pct: Percentual de range (0.2 = ±20%)

        Returns:
            Tuple de (spots, payoffs) para plotting
        """
        min_spot = self.spot_price * (1 - spot_range_pct)
        max_spot = self.spot_price * (1 + spot_range_pct)

        spots = np.linspace(min_spot, max_spot, 100)
        payoffs = [self.payoff_at_expiration(s).gross_pl for s in spots]

        return list(spots), list(payoffs)

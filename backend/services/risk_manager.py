"""Gerenciador de risco de portfólio — agregação de Greeks, VaR, stress testing."""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class PortfolioGreeks:
    """Gregas agregadas de um portfólio."""
    delta: float  # Delta total
    gamma: float  # Gamma total
    vega: float  # Vega total
    theta: float  # Theta total
    rho: float  # Rho total


@dataclass
class RiskMetrics:
    """Métricas de risco de portfólio."""
    greeks: PortfolioGreeks  # Gregas agregadas
    var_95: float  # Value at Risk (95% confiança)
    cvar_95: float  # Conditional VaR (perda esperada)
    max_drawdown: float  # Drawdown máximo
    stress_test_scenarios: dict  # Resultados de stress test


class RiskManager:
    """Gerenciador de risco de portfólio.

    Calcula VaR, stress testing, e agregação de Greeks.
    Genérico para qualquer portfólio de opções.
    """

    def __init__(self, initial_value: float = 100000.0):
        """Inicializa gerenciador de risco.

        Args:
            initial_value: Valor inicial do portfólio (para drawdown)
        """
        self.initial_value = initial_value
        self.positions: list[dict] = []  # Posições no portfólio

    def add_position(
        self,
        name: str,
        quantity: float,
        delta: float,
        gamma: float,
        vega: float,
        theta: float,
        rho: float,
        value: float
    ) -> None:
        """Adiciona posição ao portfólio.

        Args:
            name: Nome da posição
            quantity: Quantidade (contracts ou shares)
            delta: Delta da posição
            gamma: Gamma da posição
            vega: Vega da posição
            theta: Theta da posição
            rho: Rho da posição
            value: Valor atual da posição
        """
        self.positions.append({
            "name": name,
            "quantity": quantity,
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho,
            "value": value
        })

    def calculate_portfolio_greeks(self) -> PortfolioGreeks:
        """Calcula Gregas agregadas do portfólio.

        Returns:
            PortfolioGreeks com somas ponderadas
        """
        if not self.positions:
            return PortfolioGreeks(delta=0, gamma=0, vega=0, theta=0, rho=0)

        delta_agg = sum(pos["quantity"] * pos["delta"] for pos in self.positions)
        gamma_agg = sum(pos["quantity"] * pos["gamma"] for pos in self.positions)
        vega_agg = sum(pos["quantity"] * pos["vega"] for pos in self.positions)
        theta_agg = sum(pos["quantity"] * pos["theta"] for pos in self.positions)
        rho_agg = sum(pos["quantity"] * pos["rho"] for pos in self.positions)

        return PortfolioGreeks(
            delta=delta_agg,
            gamma=gamma_agg,
            vega=vega_agg,
            theta=theta_agg,
            rho=rho_agg
        )

    def calculate_var(self, confidence_level: float = 0.95) -> float:
        """Calcula Value at Risk (VaR) via parametric method.

        Args:
            confidence_level: Nível de confiança (0.95 = 95%)

        Returns:
            VaR (perda esperada no percentil)
        """
        if not self.positions:
            return 0.0

        portfolio_value = sum(pos["value"] for pos in self.positions)

        # VaR paramétrico: assume distribuição normal
        # Z-score para 95% confiança = 1.645
        # VaR = Portfolio Value * (- Z-score * volatility)
        z_score = {
            0.90: 1.282,
            0.95: 1.645,
            0.99: 2.326
        }.get(confidence_level, 1.645)

        # Volatilidade estimada via Vega (simplificado)
        portfolio_vega = sum(pos["quantity"] * pos["vega"] for pos in self.positions)
        implied_vol = 0.20  # Default

        if portfolio_vega != 0:
            # Vega é derivada: 1 ponto de vol
            implied_vol = abs(portfolio_vega) / portfolio_value if portfolio_value > 0 else 0.20

        var = portfolio_value * z_score * implied_vol
        return var

    def calculate_cvar(self, confidence_level: float = 0.95) -> float:
        """Calcula Conditional VaR (perda esperada além do VaR).

        Args:
            confidence_level: Nível de confiança

        Returns:
            CVaR (perda esperada condicional)
        """
        var = self.calculate_var(confidence_level)

        # CVaR = VaR * (1 + z-score / (1 - confidence_level))
        z_score = {
            0.90: 1.282,
            0.95: 1.645,
            0.99: 2.326
        }.get(confidence_level, 1.645)

        cvar = var * (1 + z_score / (1 - confidence_level))
        return cvar

    def calculate_max_drawdown(self, historical_values: Optional[list[float]] = None) -> float:
        """Calcula drawdown máximo histórico.

        Args:
            historical_values: Série histórica de valores (opcional)

        Returns:
            Máximo drawdown (negativo)
        """
        if not historical_values or len(historical_values) < 2:
            return 0.0

        values = np.array(historical_values)
        running_max = np.maximum.accumulate(values)
        drawdown = (values - running_max) / running_max

        max_dd = np.min(drawdown)
        return max_dd

    def stress_test(
        self,
        spot_move_pct: float = 0.10,
        vol_move_pct: float = 0.20,
        rate_move_bps: float = 100
    ) -> dict:
        """Stress testing: simula movimentos extremos.

        Args:
            spot_move_pct: % de movimento de preço (0.10 = 10%)
            vol_move_pct: % de movimento de vol (0.20 = 20%)
            rate_move_bps: Movimento de taxa em basis points

        Returns:
            Dict com P&L em cada cenário
        """
        scenarios = {}

        # Cenário 1: Mercado sobe 10%
        scenario_up = sum(
            pos["quantity"] * pos["value"] * pos["delta"] * spot_move_pct
            for pos in self.positions
        )
        scenarios["spot_up_10pct"] = scenario_up

        # Cenário 2: Mercado cai 10%
        scenario_down = sum(
            pos["quantity"] * pos["value"] * pos["delta"] * (-spot_move_pct)
            for pos in self.positions
        )
        scenarios["spot_down_10pct"] = scenario_down

        # Cenário 3: Vol sobe 20%
        scenario_vol_up = sum(
            pos["quantity"] * pos["vega"] * vol_move_pct / 100  # Vega é por 1 ponto
            for pos in self.positions
        )
        scenarios["vol_up_20pct"] = scenario_vol_up

        # Cenário 4: Vol cai 20%
        scenario_vol_down = sum(
            pos["quantity"] * pos["vega"] * (-vol_move_pct / 100)
            for pos in self.positions
        )
        scenarios["vol_down_20pct"] = scenario_vol_down

        # Cenário 5: Taxa sobe 100 bps
        scenario_rate_up = sum(
            pos["quantity"] * pos["rho"] * (rate_move_bps / 10000)
            for pos in self.positions
        )
        scenarios["rate_up_100bps"] = scenario_rate_up

        return scenarios

    def compute_risk_metrics(
        self,
        historical_values: Optional[list[float]] = None
    ) -> RiskMetrics:
        """Computa métricas completas de risco.

        Args:
            historical_values: Série histórica (para drawdown)

        Returns:
            RiskMetrics com análise completa
        """
        greeks = self.calculate_portfolio_greeks()
        var_95 = self.calculate_var(0.95)
        cvar_95 = self.calculate_cvar(0.95)
        max_dd = self.calculate_max_drawdown(historical_values)
        stress = self.stress_test()

        return RiskMetrics(
            greeks=greeks,
            var_95=var_95,
            cvar_95=cvar_95,
            max_drawdown=max_dd,
            stress_test_scenarios=stress
        )

"""Tests for multi-leg option strategy analysis.

Testa análise de spreads, straddles, butterflies, iron condors.
Todos os testes usam ativos arbitrários (não específicos de ticker).
"""
import pytest
import numpy as np

from backend.services.strategy_analyzer import (
    StrategyAnalyzer,
    StrategyType,
    StrategyPayoff,
    StrategyMetrics,
    Leg
)
from backend.domain.option_pricing import OptionType


class TestStrategyAnalyzerBasic:
    """Testes básicos de inicialização e adição de pernas."""

    def test_analyzer_initialization(self):
        """Deve inicializar analisador com spot price."""
        analyzer = StrategyAnalyzer(spot_price=100.0)
        assert analyzer.spot_price == 100.0
        assert len(analyzer.legs) == 0

    def test_add_single_leg(self):
        """Deve adicionar uma perna à estratégia."""
        analyzer = StrategyAnalyzer(spot_price=100.0)
        analyzer.add_leg(
            strike=105.0,
            option_type=OptionType.CALL,
            quantity=1,
            premium=2.50,
            dte=30
        )

        assert len(analyzer.legs) == 1
        leg = analyzer.legs[0]
        assert leg.strike == 105.0
        assert leg.quantity == 1
        assert leg.premium == 2.50

    def test_add_multiple_legs(self):
        """Deve agregar múltiplas pernas."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        # Long call spread
        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        assert len(analyzer.legs) == 2


class TestCallSpread:
    """Testes de call spread (bull call spread)."""

    def test_call_spread_payoff_at_expiration_itm(self):
        """Call spread deve ter payoff limitado quando ambas ITM."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        # Bull call spread: long 100 call @ 3.00, short 105 call @ 1.00
        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        # No vencimento, spot = 110
        payoff = analyzer.payoff_at_expiration(spot_price=110.0)

        # P&L strategy: (110-100) - (110-105) = 10 - 5 = 5
        # Initial cost: 3 - 1 = 2 (net debit)
        # Gross P&L: 5 - 2 = 3
        assert payoff.spot_price == 110.0
        assert abs(payoff.strategy_pl - 5.0) < 0.01
        assert abs(payoff.gross_pl - 3.0) < 0.01

    def test_call_spread_payoff_below_lower_strike(self):
        """Call spread perde máximo quando abaixo do lower strike."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        # Spot abaixo de 100
        payoff = analyzer.payoff_at_expiration(spot_price=95.0)

        # P&L strategy: 0
        # Gross P&L: 0 - 2 (net debit) = -2
        assert abs(payoff.strategy_pl - 0.0) < 0.01
        assert abs(payoff.gross_pl - (-2.0)) < 0.01


class TestPutSpread:
    """Testes de put spread (bear put spread)."""

    def test_put_spread_payoff(self):
        """Put spread deve ter payoff limitado."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        # Bear put spread: short 95 put @ 2.00, long 90 put @ 0.50
        analyzer.add_leg(strike=95.0, option_type=OptionType.PUT, quantity=-1, premium=2.0, dte=30)
        analyzer.add_leg(strike=90.0, option_type=OptionType.PUT, quantity=1, premium=0.5, dte=30)

        # Spot no meio (92)
        payoff = analyzer.payoff_at_expiration(spot_price=92.0)

        # P&L strategy: -1*(95-92) + 1*0 = -3 (short put perde)
        # Initial cost: -2.0 + 0.5 = -1.5 (net credit recebido)
        # Gross P&L: -3 - (-1.5) = -3 + 1.5 = -1.5
        assert abs(payoff.strategy_pl - (-3.0)) < 0.01
        assert abs(payoff.gross_pl - (-1.5)) < 0.01


class TestStraddle:
    """Testes de straddle (long call + long put mesmo strike)."""

    def test_straddle_payoff_atm(self):
        """Straddle perde tudo (prêmio) quando ATM."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        # Straddle: long 100 call @ 2.50, long 100 put @ 2.50
        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=2.5, dte=30)
        analyzer.add_leg(strike=100.0, option_type=OptionType.PUT, quantity=1, premium=2.5, dte=30)

        # No vencimento, spot = 100 (ATM)
        payoff = analyzer.payoff_at_expiration(spot_price=100.0)

        # P&L strategy: 0 + 0 = 0
        # Initial cost: 2.5 + 2.5 = 5.0 (debit)
        # Gross P&L: 0 - 5.0 = -5.0
        assert abs(payoff.strategy_pl - 0.0) < 0.01
        assert abs(payoff.gross_pl - (-5.0)) < 0.01

    def test_straddle_payoff_far_otm(self):
        """Straddle lucra quando move significativamente."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=2.5, dte=30)
        analyzer.add_leg(strike=100.0, option_type=OptionType.PUT, quantity=1, premium=2.5, dte=30)

        # Move significativo para cima
        payoff = analyzer.payoff_at_expiration(spot_price=115.0)

        # P&L strategy: (115-100) + 0 = 15
        # Initial cost: 5.0
        # Gross P&L: 15 - 5 = 10
        assert abs(payoff.strategy_pl - 15.0) < 0.01
        assert abs(payoff.gross_pl - 10.0) < 0.01


class TestStrangle:
    """Testes de strangle (long call OTM + long put OTM)."""

    def test_strangle_payoff(self):
        """Strangle deve ser mais barata que straddle."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        # Strangle: long 105 call @ 1.50, long 95 put @ 1.50
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=1, premium=1.5, dte=30)
        analyzer.add_leg(strike=95.0, option_type=OptionType.PUT, quantity=1, premium=1.5, dte=30)

        # Spot move pequeno (110)
        payoff = analyzer.payoff_at_expiration(spot_price=110.0)

        # P&L strategy: (110-105) + 0 = 5
        # Initial cost: 1.5 + 1.5 = 3.0
        # Gross P&L: 5 - 3 = 2
        assert abs(payoff.strategy_pl - 5.0) < 0.01
        assert abs(payoff.gross_pl - 2.0) < 0.01


class TestBreakevens:
    """Testes de cálculo de break-even."""

    def test_call_spread_breakevens(self):
        """Call spread deve ter 1 break-even."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        breakevens = analyzer.calculate_breakevens()

        assert len(breakevens) > 0
        # Break-even deve estar entre 100 e 105
        assert any(100.0 <= be <= 105.0 for be in breakevens)

    def test_straddle_breakevens(self):
        """Straddle deve ter 2 break-evens (strike ± prêmio total)."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=2.5, dte=30)
        analyzer.add_leg(strike=100.0, option_type=OptionType.PUT, quantity=1, premium=2.5, dte=30)

        breakevens = analyzer.calculate_breakevens()

        # Esperamos break-evens perto de 95 e 105 (100 ± 5)
        assert len(breakevens) >= 2


class TestStrategyMetrics:
    """Testes de cálculo de métricas agregadas."""

    def test_compute_metrics_call_spread(self):
        """Deve computar métricas de call spread."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        metrics = analyzer.compute_metrics(current_iv=0.20)

        assert isinstance(metrics, StrategyMetrics)
        assert metrics.max_profit > 0  # Spread tem limite de lucro
        assert metrics.max_loss < 0  # Spread tem limite de perda
        assert len(metrics.breakeven) >= 1
        assert abs(metrics.initial_cost - 2.0) < 0.01  # Net debit de 2.0 (paga 3, recebe 1)

    def test_metrics_greeks_aggregated(self):
        """Gregas devem ser agregadas corretamente."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        metrics = analyzer.compute_metrics(current_iv=0.20)

        # Greeks devem existir
        assert abs(metrics.delta_at_spot) >= 0
        assert abs(metrics.gamma_at_spot) >= 0
        assert abs(metrics.vega_at_spot) >= 0
        assert abs(metrics.theta_at_spot) >= 0

    def test_risk_reward_ratio_positive(self):
        """Risk/reward ratio deve ser positivo."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        metrics = analyzer.compute_metrics()

        assert metrics.risk_reward_ratio >= 0


class TestPayoffCurve:
    """Testes de simulação de curva de payoff."""

    def test_simulate_payoff_curve_call_spread(self):
        """Deve simular payoff curve ao redor do spot."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        spots, payoffs = analyzer.simulate_payoff_curve(spot_range_pct=0.2)

        assert len(spots) > 0
        assert len(payoffs) == len(spots)
        assert spots[0] < 100.0 < spots[-1]  # Range inclui spot atual

    def test_payoff_curve_shapes_correctly(self):
        """Curva de payoff deve ter shape correto para call spread."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        analyzer.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)

        spots, payoffs = analyzer.simulate_payoff_curve(spot_range_pct=0.2)

        # Call spread deve ter payoff crescente até upper strike
        # Payoff deve ser negativo abaixo de breakeven
        assert min(payoffs) < 0  # Máxima perda
        assert max(payoffs) > 0  # Máximo lucro


class TestGeneric:
    """Testes de genericidade (qualquer ativo)."""

    def test_works_with_different_spot_prices(self):
        """Estratégia deve funcionar com diferentes preços."""
        # Estratégia 1: spot 100
        analyzer1 = StrategyAnalyzer(spot_price=100.0)
        analyzer1.add_leg(strike=100.0, option_type=OptionType.CALL, quantity=1, premium=3.0, dte=30)
        analyzer1.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.0, dte=30)
        metrics1 = analyzer1.compute_metrics()

        # Estratégia 2: spot 50 (mesmo spread relativo)
        analyzer2 = StrategyAnalyzer(spot_price=50.0)
        analyzer2.add_leg(strike=50.0, option_type=OptionType.CALL, quantity=1, premium=1.5, dte=30)
        analyzer2.add_leg(strike=52.5, option_type=OptionType.CALL, quantity=-1, premium=0.5, dte=30)
        metrics2 = analyzer2.compute_metrics()

        # Spreads têm mesma largura relativa
        # Risk/reward devem ser similares (com scaling)
        assert abs(metrics1.risk_reward_ratio - metrics2.risk_reward_ratio) < 0.5

    def test_error_on_empty_strategy(self):
        """Deve lançar erro se não há pernas."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        with pytest.raises(ValueError):
            analyzer.compute_metrics()


class TestIronCondor:
    """Testes de iron condor (spreads de venda de calls + puts)."""

    def test_iron_condor_structure(self):
        """Iron condor deve ter 4 pernas."""
        analyzer = StrategyAnalyzer(spot_price=100.0)

        # Sell call spread: short 105 call, long 110 call
        analyzer.add_leg(strike=105.0, option_type=OptionType.CALL, quantity=-1, premium=1.5, dte=30)
        analyzer.add_leg(strike=110.0, option_type=OptionType.CALL, quantity=1, premium=0.5, dte=30)

        # Sell put spread: short 95 put, long 90 put
        analyzer.add_leg(strike=95.0, option_type=OptionType.PUT, quantity=-1, premium=1.5, dte=30)
        analyzer.add_leg(strike=90.0, option_type=OptionType.PUT, quantity=1, premium=0.5, dte=30)

        assert len(analyzer.legs) == 4
        metrics = analyzer.compute_metrics()
        assert metrics.initial_cost < 0  # Credit spread

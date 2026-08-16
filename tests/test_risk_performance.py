"""Tests for risk management and performance monitoring (Phase 5).

Testa RiskManager, PerformanceMonitor, HedgeOptimizer.
"""
from datetime import datetime, timedelta

import pytest

from backend.services.risk_manager import RiskManager, PortfolioGreeks, RiskMetrics
from backend.services.performance_monitor import PerformanceMonitor
from backend.services.hedge_optimizer import HedgeOptimizer


class TestRiskManager:
    """Testes do gerenciador de risco."""

    def test_risk_manager_initialization(self):
        """Deve inicializar com capital inicial."""
        rm = RiskManager(initial_value=100000.0)
        assert rm.initial_value == 100000.0
        assert len(rm.positions) == 0

    def test_add_position(self):
        """Deve adicionar posição ao portfólio."""
        rm = RiskManager()
        rm.add_position(
            name="CALL_100",
            quantity=10,
            delta=0.5,
            gamma=0.05,
            vega=0.1,
            theta=-0.02,
            rho=0.01,
            value=2000.0
        )
        assert len(rm.positions) == 1

    def test_portfolio_greeks_zero_if_empty(self):
        """Deve retornar gregas zero se sem posições."""
        rm = RiskManager()
        greeks = rm.calculate_portfolio_greeks()
        assert greeks.delta == 0
        assert greeks.gamma == 0
        assert greeks.vega == 0

    def test_portfolio_greeks_aggregation(self):
        """Deve agregar gregas de múltiplas posições."""
        rm = RiskManager()
        rm.add_position("CALL_100", 10, delta=0.5, gamma=0.05, vega=0.1, theta=-0.02, rho=0.01, value=2000)
        rm.add_position("PUT_95", 5, delta=-0.3, gamma=0.04, vega=0.08, theta=-0.01, rho=-0.01, value=500)

        greeks = rm.calculate_portfolio_greeks()
        assert greeks.delta == pytest.approx(10*0.5 + 5*(-0.3))
        assert greeks.gamma == pytest.approx(10*0.05 + 5*0.04)

    def test_var_calculation(self):
        """Deve calcular VaR 95%."""
        rm = RiskManager()
        rm.add_position("CALL_100", 10, delta=0.5, gamma=0.05, vega=0.1, theta=-0.02, rho=0.01, value=2000)

        var = rm.calculate_var(0.95)
        assert var > 0

    def test_cvar_calculation(self):
        """Deve calcular CVaR (maior que VaR)."""
        rm = RiskManager()
        rm.add_position("CALL_100", 10, delta=0.5, gamma=0.05, vega=0.1, theta=-0.02, rho=0.01, value=2000)

        var = rm.calculate_var(0.95)
        cvar = rm.calculate_cvar(0.95)
        assert cvar > var  # CVaR sempre > VaR

    def test_max_drawdown_calculation(self):
        """Deve calcular drawdown máximo."""
        rm = RiskManager()
        historical_values = [100000, 105000, 102000, 98000, 95000]
        dd = rm.calculate_max_drawdown(historical_values)
        assert dd < 0  # Drawdown é negativo

    def test_stress_test_scenarios(self):
        """Deve gerar cenários de stress test."""
        rm = RiskManager()
        rm.add_position("CALL_100", 10, delta=0.5, gamma=0.05, vega=0.1, theta=-0.02, rho=0.01, value=2000)

        scenarios = rm.stress_test(spot_move_pct=0.10, vol_move_pct=0.20, rate_move_bps=100)

        assert "spot_up_10pct" in scenarios
        assert "spot_down_10pct" in scenarios
        assert "vol_up_20pct" in scenarios

    def test_compute_risk_metrics(self):
        """Deve computar métricas de risco completas."""
        rm = RiskManager()
        rm.add_position("CALL_100", 10, delta=0.5, gamma=0.05, vega=0.1, theta=-0.02, rho=0.01, value=2000)

        metrics = rm.compute_risk_metrics()

        assert isinstance(metrics, RiskMetrics)
        assert metrics.var_95 > 0
        assert metrics.cvar_95 > metrics.var_95


class TestPerformanceMonitor:
    """Testes do monitor de performance."""

    def test_monitor_initialization(self):
        """Deve inicializar com capital inicial."""
        pm = PerformanceMonitor(starting_capital=100000.0)
        assert pm.starting_capital == 100000.0
        assert pm.current_value == 100000.0

    def test_record_winning_trade(self):
        """Deve registrar trade vencedor."""
        pm = PerformanceMonitor()
        now = datetime.now()

        trade = pm.record_trade(
            entry_price=100.0,
            exit_price=105.0,
            quantity=10,
            entry_time=now,
            exit_time=now + timedelta(minutes=30),
            commission=10.0
        )

        # P&L = (exit - entry) * qty - commission = (105-100)*10 - 10 = 40
        assert trade["pnl"] == pytest.approx(40.0)
        assert trade["is_win"] is True

    def test_record_losing_trade(self):
        """Deve registrar trade perdedor."""
        pm = PerformanceMonitor()
        now = datetime.now()

        trade = pm.record_trade(
            entry_price=100.0,
            exit_price=95.0,
            quantity=10,
            entry_time=now,
            exit_time=now + timedelta(minutes=30),
            commission=10.0
        )

        # P&L = (95-100)*10 - 10 = -60
        assert trade["pnl"] == pytest.approx(-60.0)
        assert trade["is_win"] is False

    def test_win_rate_calculation(self):
        """Deve calcular taxa de vitórias."""
        pm = PerformanceMonitor()
        now = datetime.now()

        # 2 vitórias
        pm.record_trade(100.0, 105.0, 10, now, now + timedelta(minutes=1))
        pm.record_trade(100.0, 105.0, 10, now, now + timedelta(minutes=1))

        # 1 derrota
        pm.record_trade(100.0, 95.0, 10, now, now + timedelta(minutes=1))

        win_rate = pm.calculate_win_rate()
        assert win_rate == pytest.approx(2/3)

    def test_profit_factor(self):
        """Deve calcular profit factor."""
        pm = PerformanceMonitor()
        now = datetime.now()

        # Ganho: $400
        pm.record_trade(100.0, 102.0, 200, now, now + timedelta(minutes=1))

        # Perda: $-200
        pm.record_trade(100.0, 99.0, 200, now, now + timedelta(minutes=1))

        pf = pm.calculate_profit_factor()
        assert pf == pytest.approx(400/200)  # 2.0

    def test_sharpe_ratio(self):
        """Deve calcular índice de Sharpe."""
        pm = PerformanceMonitor()

        # Simula daily P&Ls
        pm.daily_pnls = [100, 150, 120, 110, 200, 80, 130]

        sharpe = pm.calculate_sharpe_ratio()
        assert isinstance(sharpe, float)

    def test_sortino_ratio(self):
        """Deve calcular índice de Sortino."""
        pm = PerformanceMonitor()

        # Daily P&Ls com alguns dias negativos
        pm.daily_pnls = [100, -50, 120, -30, 200, 150, 100]

        sortino = pm.calculate_sortino_ratio()
        assert isinstance(sortino, float)

    def test_performance_metrics(self):
        """Deve computar métricas de performance."""
        pm = PerformanceMonitor(starting_capital=100000)
        now = datetime.now()

        pm.record_trade(100.0, 105.0, 10, now, now + timedelta(minutes=1))
        pm.daily_pnls = [50, 75, -25]

        metrics = pm.compute_performance_metrics()

        assert metrics.total_pnl > 0
        assert 0.0 <= metrics.win_rate <= 1.0


class TestHedgeOptimizer:
    """Testes do otimizador de hedge."""

    def test_hedge_optimizer_initialization(self):
        """Deve inicializar com targets."""
        ho = HedgeOptimizer(target_delta=0.0, delta_threshold=0.1)
        assert ho.target_delta == 0.0
        assert ho.delta_threshold == 0.1

    def test_recommend_hedge_long_position(self):
        """Deve recomendar venda de delta para posição long."""
        ho = HedgeOptimizer(target_delta=0.0, delta_threshold=0.1, rebalance_cost_threshold=100)

        recommendation = ho.recommend_hedge(
            current_delta=1.0,  # Muito long
            spot_price=100.0,
            call_delta=0.5
        )

        assert recommendation.delta_gap == 1.0
        # Custo estimado = qty * price * 0.01 = 2 * 100 * 0.01 = 2.0 < 100 (threshold)
        # Então rebalance_needed = False (custo muito baixo)
        assert recommendation.hedge_instrument == "sell_calls"

    def test_recommend_hedge_short_position(self):
        """Deve recomendar compra de delta para posição short."""
        ho = HedgeOptimizer(target_delta=0.0, delta_threshold=0.1, rebalance_cost_threshold=100)

        recommendation = ho.recommend_hedge(
            current_delta=-1.0,  # Muito short
            spot_price=100.0,
            call_delta=0.5
        )

        assert recommendation.delta_gap == -1.0
        assert recommendation.hedge_instrument == "buy_calls"
        # Custo estimado também baixo, então rebalance_needed = False

    def test_rebalance_not_needed_within_threshold(self):
        """Não deve recomendar se delta dentro de threshold."""
        ho = HedgeOptimizer(target_delta=0.0, delta_threshold=0.2)

        recommendation = ho.recommend_hedge(
            current_delta=0.05,  # Dentro da tolerância
            spot_price=100.0
        )

        assert recommendation.rebalance_needed is False

    def test_record_rebalance(self):
        """Deve registrar rebalanceamento."""
        ho = HedgeOptimizer()

        rebalance = ho.record_rebalance(
            instrument="sell_calls",
            quantity=10,
            price=2.5,
            reason="Delta hedge"
        )

        assert rebalance["instrument"] == "sell_calls"
        assert len(ho.rebalance_history) == 1

    def test_total_hedge_cost(self):
        """Deve calcular custo total de hedging."""
        ho = HedgeOptimizer()

        ho.record_rebalance("sell_calls", 10, 2.5, "Delta hedge")
        ho.record_rebalance("buy_puts", 5, 1.0, "Gamma hedge")

        total_cost = ho.get_total_hedge_cost()
        assert total_cost == pytest.approx(10*2.5 + 5*1.0)

    def test_rebalance_frequency(self):
        """Deve calcular frequência de rebalances."""
        ho = HedgeOptimizer()

        for i in range(10):
            ho.record_rebalance(f"rebalance_{i}", 1, 100, "Routine hedge")

        frequency = ho.get_rebalance_frequency(window_days=10)
        assert frequency == pytest.approx(1.0)  # 10 rebalances em 10 dias

    def test_hedge_efficiency(self):
        """Deve analisar eficiência do hedging."""
        ho = HedgeOptimizer(rebalance_cost_threshold=100)

        for i in range(5):
            ho.record_rebalance("hedge", 10, 50, "Routine")

        efficiency = ho.analyze_hedge_efficiency()

        assert efficiency["total_rebalances"] == 5
        assert efficiency["total_cost"] == 5 * (10*50)
        assert 0 <= efficiency["efficiency_score"] <= 1.0

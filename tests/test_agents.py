"""Tests for multiagent orchestration framework.

Testa agentes individuais, lógica de consenso, e integração end-to-end.
"""
import pytest

from backend.agents.agents import (
    TechnicalAnalyst,
    RiskManager,
    StrategySelector,
    Executor
)
from backend.agents.base import AgentDecision, AgentType
from backend.agents.orchestrator import AgentOrchestrator


class TestTechnicalAnalyst:
    """Testes do analista técnico."""

    def test_analyst_initialization(self):
        """Deve inicializar com tipo correto."""
        analyst = TechnicalAnalyst()
        assert analyst.agent_type == AgentType.TECHNICAL_ANALYST

    def test_analyst_call_signal_overbought(self):
        """CALL com RSI > 60 deve concordar."""
        analyst = TechnicalAnalyst()
        context = {
            "rsi": 70,
            "stoch_k": 75,
            "trend": "UP",
            "signal_type": "CALL_ALTA"
        }
        opinion = analyst.analyze(context)
        assert opinion.decision == AgentDecision.AGREE
        assert opinion.confidence > 0.5

    def test_analyst_put_signal_oversold(self):
        """PUT com RSI < 40 deve concordar."""
        analyst = TechnicalAnalyst()
        context = {
            "rsi": 30,
            "stoch_k": 25,
            "trend": "DOWN",
            "signal_type": "PUT_BAIXA"
        }
        opinion = analyst.analyze(context)
        assert opinion.decision == AgentDecision.AGREE
        assert opinion.confidence > 0.5

    def test_analyst_weak_signal(self):
        """Sinal fraco deve discordar."""
        analyst = TechnicalAnalyst()
        context = {
            "rsi": 50,  # Neutro
            "stoch_k": 50,  # Neutro
            "trend": "SIDEWAYS",
            "signal_type": "CALL_ALTA"
        }
        opinion = analyst.analyze(context)
        assert opinion.decision == AgentDecision.DISAGREE

    def test_analyst_caches_last_opinion(self):
        """Deve cachear última opinião."""
        analyst = TechnicalAnalyst()
        context = {"rsi": 70, "stoch_k": 75, "trend": "UP", "signal_type": "CALL_ALTA"}
        opinion = analyst.analyze(context)
        assert analyst.get_last_opinion() == opinion


class TestRiskManager:
    """Testes do gerenciador de risco."""

    def test_risk_manager_initialization(self):
        """Deve inicializar com tipo correto."""
        rm = RiskManager()
        assert rm.agent_type == AgentType.RISK_MANAGER

    def test_risk_manager_low_delta_agrees(self):
        """Delta baixo (< 0.2) deve concordar (baixo risco)."""
        rm = RiskManager()
        context = {
            "delta": 0.15,
            "gamma": 0.03,
            "vega": 0.05,
            "max_loss": -50,
            "account_size": 10000
        }
        opinion = rm.analyze(context)
        assert opinion.decision == AgentDecision.AGREE

    def test_risk_manager_high_delta_disagrees(self):
        """Delta alto (> 0.8) deve discordar (risco alto)."""
        rm = RiskManager()
        context = {
            "delta": 0.95,
            "gamma": 0.1,
            "vega": 0.15,
            "max_loss": -100,
            "account_size": 10000
        }
        opinion = rm.analyze(context)
        assert opinion.decision == AgentDecision.DISAGREE

    def test_risk_manager_excessive_loss_disagrees(self):
        """Perda > 5% da conta deve discordar."""
        rm = RiskManager()
        context = {
            "delta": 0.5,
            "gamma": 0.05,
            "vega": 0.1,
            "max_loss": -1000,  # 10% da conta
            "account_size": 10000
        }
        opinion = rm.analyze(context)
        assert opinion.decision == AgentDecision.DISAGREE

    def test_risk_manager_confidence_clipped(self):
        """Confiança deve estar entre 0 e 1."""
        rm = RiskManager()
        context = {
            "delta": 0.5,
            "gamma": 0.05,
            "vega": 0.1,
            "max_loss": -50,
            "account_size": 10000
        }
        opinion = rm.analyze(context)
        assert 0.0 <= opinion.confidence <= 1.0


class TestStrategySelector:
    """Testes do seletor de estratégia."""

    def test_selector_initialization(self):
        """Deve inicializar com tipo correto."""
        selector = StrategySelector()
        assert selector.agent_type == AgentType.STRATEGY_SELECTOR

    def test_selector_good_rr_agrees(self):
        """R/R > 2:1 deve concordar."""
        selector = StrategySelector()
        context = {
            "max_profit": 200,
            "max_loss": -80,
            "rr_ratio": 2.5,  # Muito bom
            "strategy_type": "call_spread"
        }
        opinion = selector.analyze(context)
        assert opinion.decision == AgentDecision.AGREE
        assert opinion.confidence > 0.5

    def test_selector_poor_rr_disagrees(self):
        """R/R < 0.5 deve discordar."""
        selector = StrategySelector()
        context = {
            "max_profit": 50,
            "max_loss": -200,
            "rr_ratio": 0.25,  # Ruim
            "strategy_type": "naked_call"
        }
        opinion = selector.analyze(context)
        assert opinion.decision == AgentDecision.DISAGREE

    def test_selector_spreads_preferred(self):
        """Spreads devem ter confiança maior."""
        selector = StrategySelector()

        # Naked
        naked_context = {
            "max_profit": 100,
            "max_loss": -500,
            "rr_ratio": 0.2,
            "strategy_type": "naked_call"
        }
        naked_opinion = selector.analyze(naked_context)

        # Spread
        spread_context = {
            "max_profit": 100,
            "max_loss": -500,
            "rr_ratio": 0.2,
            "strategy_type": "call_spread"
        }
        spread_opinion = selector.analyze(spread_context)

        assert spread_opinion.confidence > naked_opinion.confidence


class TestExecutor:
    """Testes do executor (gate final)."""

    def test_executor_initialization(self):
        """Deve inicializar com tipo correto."""
        executor = Executor()
        assert executor.agent_type == AgentType.EXECUTOR

    def test_executor_requires_3_4_consensus(self):
        """Requer consenso mínimo de 75%."""
        executor = Executor()

        # 3/4 concordam = OK
        context_go = {
            "agreement_count": 3,
            "total_agents": 4,
            "avg_confidence": 0.7,
            "liquidez": 0.8
        }
        opinion_go = executor.analyze(context_go)
        assert opinion_go.decision == AgentDecision.AGREE

        # 2/4 concordam = NO GO
        context_no_go = {
            "agreement_count": 2,
            "total_agents": 4,
            "avg_confidence": 0.7,
            "liquidez": 0.8
        }
        opinion_no_go = executor.analyze(context_no_go)
        assert opinion_no_go.decision == AgentDecision.DISAGREE

    def test_executor_requires_minimum_confidence(self):
        """Requer confiança mínima 0.5."""
        executor = Executor()
        context = {
            "agreement_count": 3,
            "total_agents": 4,
            "avg_confidence": 0.3,  # Muito baixa
            "liquidez": 0.5
        }
        opinion = executor.analyze(context)
        assert opinion.decision == AgentDecision.DISAGREE

    def test_executor_liquidity_weighted(self):
        """Confiança ponderada por liquidez."""
        executor = Executor()

        # Boa confiança, boa liquidez
        context_good = {
            "agreement_count": 3,
            "total_agents": 4,
            "avg_confidence": 0.8,
            "liquidez": 0.9
        }
        opinion_good = executor.analyze(context_good)

        # Boa confiança, baixa liquidez
        context_poor = {
            "agreement_count": 3,
            "total_agents": 4,
            "avg_confidence": 0.8,
            "liquidez": 0.2
        }
        opinion_poor = executor.analyze(context_poor)

        assert opinion_good.confidence > opinion_poor.confidence


class TestOrchestrator:
    """Testes do orchestrator de agentes."""

    def test_orchestrator_initialization(self):
        """Deve inicializar com 4 agentes."""
        orch = AgentOrchestrator()
        assert len(orch.agents) == 3  # Technical, Risk, Strategy (Executor é separado)
        assert orch.technical_analyst is not None
        assert orch.risk_manager is not None
        assert orch.strategy_selector is not None
        assert orch.executor is not None

    def test_orchestrator_strong_consensus(self):
        """Cenário com consenso forte deve go."""
        orch = AgentOrchestrator()
        context = {
            # Technical: bom
            "rsi": 70,
            "stoch_k": 75,
            "trend": "UP",
            "signal_type": "CALL_ALTA",
            # Risk: aceitável
            "delta": 0.5,
            "gamma": 0.05,
            "vega": 0.1,
            "max_loss": -50,
            "account_size": 10000,
            # Strategy: bom
            "max_profit": 200,
            "rr_ratio": 2.0,
            "strategy_type": "call_spread",
            # Liquidez
            "liquidez": 0.8,
        }
        result = orch.orchestrate(context)
        assert result.final_decision == AgentDecision.AGREE
        assert result.consensus_pct >= 0.75
        assert len(result.opinions) == 4  # 3 agentes + executor

    def test_orchestrator_weak_consensus(self):
        """Cenário com consenso fraco deve no-go."""
        orch = AgentOrchestrator()
        context = {
            # Technical: fraco
            "rsi": 50,
            "stoch_k": 50,
            "trend": "SIDEWAYS",
            "signal_type": "CALL_ALTA",
            # Risk: alto
            "delta": 0.9,
            "gamma": 0.1,
            "vega": 0.2,
            "max_loss": -500,
            "account_size": 10000,
            # Strategy: fraco
            "max_profit": 50,
            "rr_ratio": 0.1,
            "strategy_type": "naked_call",
            # Liquidez
            "liquidez": 0.3,
        }
        result = orch.orchestrate(context)
        assert result.final_decision == AgentDecision.DISAGREE
        assert result.consensus_pct < 0.75

    def test_orchestrator_reasoning(self):
        """Reasoning deve ser legível."""
        orch = AgentOrchestrator()
        context = {
            "rsi": 65,
            "stoch_k": 70,
            "trend": "UP",
            "signal_type": "CALL_ALTA",
            "delta": 0.4,
            "gamma": 0.05,
            "vega": 0.1,
            "max_loss": -60,
            "account_size": 10000,
            "max_profit": 180,
            "rr_ratio": 1.8,
            "strategy_type": "call_spread",
            "liquidez": 0.75,
        }
        result = orch.orchestrate(context)
        assert "Consenso" in result.reasoning
        assert "%" in result.reasoning
        assert "Confiança" in result.reasoning

    def test_orchestrator_average_confidence(self):
        """Deve calcular confiança média corretamente."""
        orch = AgentOrchestrator()
        context = {
            "rsi": 65,
            "stoch_k": 70,
            "trend": "UP",
            "signal_type": "CALL_ALTA",
            "delta": 0.4,
            "gamma": 0.05,
            "vega": 0.1,
            "max_loss": -60,
            "account_size": 10000,
            "max_profit": 180,
            "rr_ratio": 1.8,
            "strategy_type": "call_spread",
            "liquidez": 0.75,
        }
        result = orch.orchestrate(context)
        assert 0.0 <= result.avg_confidence <= 1.0
        # Confidence média deve estar próxima das opiniões
        assert len(result.opinions) == 4

    def test_orchestrator_executor_can_veto(self):
        """Executor pode vetar mesmo com consenso se risco alto."""
        orch = AgentOrchestrator()
        context = {
            # Todos concordam (bons sinais técnicos)
            "rsi": 70,
            "stoch_k": 75,
            "trend": "UP",
            "signal_type": "CALL_ALTA",
            # Mas risco muito alto
            "delta": 0.95,
            "gamma": 0.15,
            "vega": 0.25,
            "max_loss": -5000,  # 50% da conta!
            "account_size": 10000,
            "max_profit": 200,
            "rr_ratio": 0.04,
            "strategy_type": "naked_call",
            # Sem liquidez
            "liquidez": 0.1,
        }
        result = orch.orchestrate(context)
        # Executor deve vetar
        assert result.final_decision == AgentDecision.DISAGREE

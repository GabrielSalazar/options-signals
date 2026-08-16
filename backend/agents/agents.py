"""Implementações concretas dos 4 agentes especializados.

Technical Analyst: análise de tendências e confluências técnicas
Risk Manager: avaliação de risco (VaR, drawdown, Greeks)
Strategy Selector: seleção e ranking de estratégias
Executor: validação final e sinais de execução
"""
import numpy as np

from backend.agents.base import (
    Agent,
    AgentType,
    AgentDecision,
    AgentOpinion
)


class TechnicalAnalyst(Agent):
    """Analista técnico — avalia tendências, suporte/resistência, confluências."""

    def __init__(self):
        super().__init__(AgentType.TECHNICAL_ANALYST)

    def analyze(self, context: dict) -> AgentOpinion:
        """Analisa contexto técnico.

        Context esperado:
        - rsi: RSI (0-100)
        - stoch_k: Estocástico K (0-100)
        - trend: "UP", "DOWN", "SIDEWAYS"
        - signal_type: "CALL_ALTA", "PUT_BAIXA", etc
        """
        self.last_opinion = self._evaluate(context)
        return self.last_opinion

    def _evaluate(self, context: dict) -> AgentOpinion:
        """Avalia indicadores técnicos."""
        rsi = context.get("rsi", 50)
        stoch_k = context.get("stoch_k", 50)
        trend = context.get("trend", "SIDEWAYS")
        signal_type = context.get("signal_type", "CALL_ALTA")

        # Scoring baseado em confluência de indicadores
        score = 0.0
        confidence = 0.5

        # RSI extremos indicam momentum
        if "CALL" in signal_type and rsi > 60:  # Sobre-comprado é bom para CALL
            score += 0.3
            confidence = min(1.0, confidence + 0.15)
        elif "PUT" in signal_type and rsi < 40:  # Sobre-vendido é bom para PUT
            score += 0.3
            confidence = min(1.0, confidence + 0.15)

        # Estocástico confirma
        if "CALL" in signal_type and stoch_k > 70:
            score += 0.2
            confidence = min(1.0, confidence + 0.1)
        elif "PUT" in signal_type and stoch_k < 30:
            score += 0.2
            confidence = min(1.0, confidence + 0.1)

        # Trend confirmação
        if "CALL" in signal_type and trend == "UP":
            score += 0.2
            confidence = min(1.0, confidence + 0.1)
        elif "PUT" in signal_type and trend == "DOWN":
            score += 0.2
            confidence = min(1.0, confidence + 0.1)

        # Decisão
        decision = AgentDecision.AGREE if score > 0.4 else AgentDecision.DISAGREE

        return AgentOpinion(
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            reasoning=f"RSI={rsi:.1f}, Stoch={stoch_k:.1f}, Trend={trend}, Score={score:.2f}",
            score=score
        )


class RiskManager(Agent):
    """Gerenciador de risco — avalia Greeks, VaR, drawdown."""

    def __init__(self):
        super().__init__(AgentType.RISK_MANAGER)

    def analyze(self, context: dict) -> AgentOpinion:
        """Analisa contexto de risco.

        Context esperado:
        - delta: Delta da estratégia
        - gamma: Gamma da estratégia
        - vega: Vega da estratégia
        - max_loss: Perda máxima possível
        - account_size: Tamanho da conta (para % de risco)
        """
        self.last_opinion = self._evaluate(context)
        return self.last_opinion

    def _evaluate(self, context: dict) -> AgentOpinion:
        """Avalia risco."""
        delta = abs(context.get("delta", 0.5))
        gamma = abs(context.get("gamma", 0.05))
        vega = abs(context.get("vega", 0.1))
        max_loss = context.get("max_loss", -100)
        account_size = context.get("account_size", 10000)

        # Risco de perda percentual
        loss_pct = abs(max_loss) / account_size if account_size > 0 else 0.0

        # Scoring: quanto menor o risco, melhor
        confidence = 0.7  # Default alto para risk manager

        # Delta muito alto = risco direcional alto
        if delta > 0.8:
            decision = AgentDecision.DISAGREE
            confidence -= 0.2
        # Delta muito baixo = risco muito baixo
        elif delta < 0.2:
            decision = AgentDecision.AGREE
            confidence += 0.2
        else:
            decision = AgentDecision.AGREE
            confidence = 0.8

        # Gamma alto = risco de rehedge frequente
        if gamma > 0.1:
            confidence -= 0.1

        # Vega alto = risco de volatilidade
        if vega > 0.2:
            confidence -= 0.1

        # Perda > 5% da conta = muito arriscado
        if loss_pct > 0.05:
            decision = AgentDecision.DISAGREE
            confidence = 0.4

        confidence = np.clip(confidence, 0.0, 1.0)

        return AgentOpinion(
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            reasoning=f"Delta={delta:.2f}, Gamma={gamma:.3f}, VegA={vega:.2f}, Loss%={loss_pct*100:.1f}%",
        )


class StrategySelector(Agent):
    """Seletor de estratégia — ranking e filtro de estratégias viáveis."""

    def __init__(self):
        super().__init__(AgentType.STRATEGY_SELECTOR)

    def analyze(self, context: dict) -> AgentOpinion:
        """Analisa estratégias.

        Context esperado:
        - max_profit: Lucro máximo possível
        - max_loss: Perda máxima possível
        - rr_ratio: Razão risco/recompensa
        - strategy_type: Tipo de estratégia (call_spread, straddle, etc)
        """
        self.last_opinion = self._evaluate(context)
        return self.last_opinion

    def _evaluate(self, context: dict) -> AgentOpinion:
        """Avalia estratégia."""
        max_profit = context.get("max_profit", 100)
        max_loss = context.get("max_loss", -50)
        rr_ratio = context.get("rr_ratio", 1.0)
        strategy_type = context.get("strategy_type", "call_spread")

        # Scoring: R/R e profit absoluto
        confidence = 0.5

        # R/R > 2:1 é bom
        if rr_ratio > 2.0:
            confidence += 0.2
        elif rr_ratio > 1.0:
            confidence += 0.1
        elif rr_ratio < 0.5:
            confidence -= 0.2

        # Profit absoluto importa
        if max_profit > abs(max_loss) * 2:
            confidence += 0.15
        elif max_profit < abs(max_loss):
            confidence -= 0.15

        # Spreads são mais seguros que naked
        if "spread" in strategy_type.lower():
            confidence += 0.1

        confidence = np.clip(confidence, 0.0, 1.0)
        decision = AgentDecision.AGREE if confidence > 0.5 else AgentDecision.DISAGREE

        return AgentOpinion(
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            reasoning=f"R/R={rr_ratio:.2f}, MaxProfit={max_profit:.2f}, Strategy={strategy_type}",
        )


class Executor(Agent):
    """Executor — validação final e gate de execução."""

    def __init__(self):
        super().__init__(AgentType.EXECUTOR)

    def analyze(self, context: dict) -> AgentOpinion:
        """Analisa contexto de execução.

        Context esperado:
        - agreement_count: Quantos agentes concordam
        - total_agents: Total de agentes
        - avg_confidence: Confiança média
        - liquidez: Liquidez do ativo
        """
        self.last_opinion = self._evaluate(context)
        return self.last_opinion

    def _evaluate(self, context: dict) -> AgentOpinion:
        """Avalia execução."""
        agreement_count = context.get("agreement_count", 0)
        total_agents = context.get("total_agents", 3)
        avg_confidence = context.get("avg_confidence", 0.5)
        liquidez = context.get("liquidez", 0.5)

        # Deve ter consenso mínimo 3/4
        consensus_pct = agreement_count / total_agents if total_agents > 0 else 0.0

        confidence = avg_confidence * liquidez  # Confidence ponderada por liquidez

        # Gate 1: Consenso mínimo de 75%
        if consensus_pct < 0.75:
            decision = AgentDecision.DISAGREE
            confidence = max(0.1, confidence - 0.3)
        # Gate 2: Confiança mínima 0.5
        elif confidence < 0.5:
            decision = AgentDecision.DISAGREE
        else:
            decision = AgentDecision.AGREE

        return AgentOpinion(
            agent_type=self.agent_type,
            decision=decision,
            confidence=confidence,
            reasoning=f"Consensus={consensus_pct*100:.0f}% ({agreement_count}/{total_agents}), AvgConf={avg_confidence:.2f}, Liq={liquidez:.2f}",
        )

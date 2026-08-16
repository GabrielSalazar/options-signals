"""Orchestrator para coordenação de múltiplos agentes.

Coordena opiniões de 4 agentes especializados e implementa lógica de consenso.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.agents.agents import (
    TechnicalAnalyst,
    RiskManager,
    StrategySelector,
    Executor
)
from backend.agents.base import AgentDecision, AgentOpinion


@dataclass
class OrchestrationResult:
    """Resultado da orquestração de agentes."""
    final_decision: AgentDecision  # Decisão final (go/no-go)
    consensus_pct: float  # Percentual de concordância
    avg_confidence: float  # Confiança média
    opinions: list[AgentOpinion]  # Opiniões individuais
    reasoning: str  # Explicação da decisão final


class AgentOrchestrator:
    """Coordena decisões de múltiplos agentes.

    Implementa lógica de consenso e fallback para análise determinística.
    """

    def __init__(self):
        """Inicializa orchestrator com 4 agentes."""
        self.technical_analyst = TechnicalAnalyst()
        self.risk_manager = RiskManager()
        self.strategy_selector = StrategySelector()
        self.executor = Executor()

        self.agents = [
            self.technical_analyst,
            self.risk_manager,
            self.strategy_selector,
        ]

    def orchestrate(self, context: dict) -> OrchestrationResult:
        """Coordena agentes para decisão consensual.

        Args:
            context: Dict com dados completos do cenário

        Returns:
            OrchestrationResult com decisão final
        """
        # Step 1: Coléta opiniões dos 3 agentes
        opinions = []
        for agent in self.agents:
            opinion = agent.analyze(context)
            opinions.append(opinion)

        # Step 2: Calcula métricas de consenso
        agreement_count = sum(
            1 for op in opinions if op.decision == AgentDecision.AGREE
        )
        avg_confidence = np.mean([op.confidence for op in opinions])

        # Step 3: Passa ao Executor (gate final)
        executor_context = {
            "agreement_count": agreement_count,
            "total_agents": len(self.agents),
            "avg_confidence": avg_confidence,
            "liquidez": context.get("liquidez", 0.7),
        }
        executor_opinion = self.executor.analyze(executor_context)
        opinions.append(executor_opinion)

        # Step 4: Decisão final
        consensus_pct = agreement_count / len(self.agents)
        final_decision = executor_opinion.decision  # Executor tem poder de veto

        # Reasoning
        reasoning = self._build_reasoning(opinions, consensus_pct, avg_confidence)

        return OrchestrationResult(
            final_decision=final_decision,
            consensus_pct=consensus_pct,
            avg_confidence=avg_confidence,
            opinions=opinions,
            reasoning=reasoning
        )

    def _build_reasoning(
        self,
        opinions: list[AgentOpinion],
        consensus_pct: float,
        avg_confidence: float
    ) -> str:
        """Constrói explicação legível da decisão."""
        agree_count = sum(1 for op in opinions if op.decision == AgentDecision.AGREE)
        total_count = len(opinions)

        parts = [
            f"Consenso: {agree_count}/{total_count} agentes concordam ({consensus_pct*100:.0f}%)",
            f"Confiança média: {avg_confidence:.2f}/1.0",
        ]

        # Detalhe por agente
        for op in opinions[:-1]:  # Exclude executor from breakdown
            parts.append(
                f"  • {op.agent_type.value}: {op.decision.value} ({op.confidence:.2f}) — {op.reasoning[:60]}"
            )

        # Decisão executor
        executor_op = opinions[-1]
        parts.append(f"  → {executor_op.agent_type.value}: {executor_op.decision.value} (gate final)")

        return "\n".join(parts)

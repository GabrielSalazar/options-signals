"""Abstract base classes for multiagent framework.

Define interface que todos os agentes devem implementar.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AgentType(Enum):
    """Tipos de agentes no sistema."""
    TECHNICAL_ANALYST = "technical_analyst"
    RISK_MANAGER = "risk_manager"
    STRATEGY_SELECTOR = "strategy_selector"
    EXECUTOR = "executor"


class AgentDecision(Enum):
    """Decisão de um agente."""
    AGREE = "agree"  # Sim, prosseguir
    DISAGREE = "disagree"  # Não, não prosseguir
    ABSTAIN = "abstain"  # Sem opinião formada


@dataclass
class AgentOpinion:
    """Opinião de um agente sobre um cenário."""
    agent_type: AgentType  # Tipo do agente
    decision: AgentDecision  # Decisão (agree/disagree/abstain)
    confidence: float  # Confiança (0.0-1.0)
    reasoning: str  # Explicação da decisão
    score: Optional[float] = None  # Score numérico se aplicável


class Agent(ABC):
    """Agente abstrato — define interface que todos os agentes implementam.

    Cada agente é especialista em um aspecto (análise técnica, risco, estratégia, execução).
    """

    def __init__(self, agent_type: AgentType):
        """Inicializa agente.

        Args:
            agent_type: Tipo de agente
        """
        self.agent_type = agent_type
        self.last_opinion: Optional[AgentOpinion] = None

    @abstractmethod
    def analyze(self, context: dict) -> AgentOpinion:
        """Analisa cenário e retorna opinião.

        Args:
            context: Dict com dados do cenário (preço, gregas, vol, etc)

        Returns:
            AgentOpinion com decisão e confiança
        """
        pass

    def get_last_opinion(self) -> Optional[AgentOpinion]:
        """Retorna última opinião do agente."""
        return self.last_opinion

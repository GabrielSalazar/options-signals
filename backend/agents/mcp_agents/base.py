"""Base classes para agentes do pipeline MCP."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class MCPAgent(ABC):
    """Base abstrata para agentes do pipeline MCP.

    Cada agente implementa um estágio do pipeline:
    1. Data Collector - coleta e normaliza dados
    2. Hypothesis Generator - gera combinações de parâmetros
    3. Backtest Engine - simula operações
    4. Metrics Analyzer - calcula KPIs
    5. Validator - valida contra thresholds
    6. Signal Generator - formata sinais
    7. Signal Registry - armazena e indexa
    """

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa entrada e retorna saída.

        Args:
            input_data: Dict com entrada (estrutura específica por agente)

        Returns:
            Dict com saída processada (estrutura específica por agente)
        """
        pass

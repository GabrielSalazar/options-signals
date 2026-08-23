"""Agentes MCP do pipeline de backtesting."""
from backend.agents.mcp_agents.base import MCPAgent
from backend.agents.mcp_agents.data_collector import DataCollectorAgent

__all__ = ["MCPAgent", "DataCollectorAgent"]

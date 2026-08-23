"""DTOs para pipeline MCP de agentes.

Define modelos de entrada/saída para agentes especializados em backtesting
e geração de sinais via pipeline multi-agente.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1: DATA COLLECTOR
# ─────────────────────────────────────────────────────────────────────────────

class DataCollectorInput(BaseModel):
    """Entrada para Agent 1: Data Collector.

    Especifica estratégia, ativo, período e indicadores a coletar.
    """
    strategy: str = Field(..., min_length=1, description="Nome da estratégia")
    asset: str = Field(..., min_length=4, max_length=10, description="Ticker B3")
    date_range: Dict[str, str] = Field(
        ...,
        description="Período: {start, end} em YYYY-MM-DD"
    )
    indicators: List[str] = Field(
        default=["rsi", "macd", "atr"],
        description="Indicadores a calcular: rsi, macd, atr, bb"
    )
    data_source: str = Field(
        default="yfinance",
        description="Fonte de dados: yfinance ou brapi"
    )

    @field_validator("asset", mode="before")
    @classmethod
    def clean_ticker(cls, v: str) -> str:
        """Normaliza ticker (maiúsculas, remove .SA)."""
        if isinstance(v, str):
            return v.upper().replace(".SA", "")
        return v


@dataclass
class OHLCPoint:
    """Um ponto OHLC no histórico."""
    date: str  # ISO 8601 (YYYY-MM-DD)
    o: float   # Open
    h: float   # High
    l: float   # Low
    c: float   # Close
    v: int     # Volume


@dataclass
class IndicatorsData:
    """Indicadores técnicos calculados."""
    rsi: Optional[List[float]] = None
    macd: Optional[Dict[str, List[float]]] = None  # {line, signal, histogram}
    atr: Optional[List[float]] = None
    bb: Optional[Dict[str, List[float]]] = None  # {upper, middle, lower}


class DataCollectorOutput(BaseModel):
    """Saída de Agent 1: Data Collector.

    Contém histórico OHLC normalizado, indicadores calculados, e metadata.
    """
    ohlc: List[Dict[str, Any]]  # List[OHLCPoint.__dict__]
    indicators: Dict[str, Any]
    meta: Dict[str, Any]

"""Signal model — Pydantic typed representation of trading signals."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalType(str, Enum):
    """Enum for signal types."""

    CALL_ALTA = "CALL_ALTA"
    CALL_REVERSAO = "CALL_REVERSAO"
    CALL_SIDEWAYS = "CALL_SIDEWAYS"
    PUT_ALTA = "PUT_ALTA"
    PUT_REVERSAO = "PUT_REVERSAO"
    PUT_SIDEWAYS = "PUT_SIDEWAYS"


class Signal(BaseModel):
    """
    Trading signal model.

    Represents a buy/sell signal with target prices, stop loss, and confidence metrics.

    Attributes:
        ticker: Stock ticker (e.g., 'PETR4')
        tipo_sinal: Signal type (CALL_ALTA, PUT_ALTA, etc.)
        alvo1: Primary target price
        alvo2: Secondary target price (optional)
        alvo3: Tertiary target price (optional)
        stop_loss: Stop loss price (must differ from alvo1)
        score_ponderado: Confidence score 0-100
        data_sinal: Signal generation timestamp
        confianca: Confidence coefficient 0.0-1.0 (optional)

    Example:
        ```python
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime.now(),
        )
        ```
    """

    ticker: str = Field(
        ..., min_length=4, max_length=10, description="Stock ticker (uppercase)"
    )
    tipo_sinal: SignalType = Field(..., description="Signal type enum")
    alvo1: float = Field(..., gt=0, description="Primary target price")
    alvo2: Optional[float] = Field(
        None, gt=0, description="Secondary target price (optional)"
    )
    alvo3: Optional[float] = Field(
        None, gt=0, description="Tertiary target price (optional)"
    )
    stop_loss: float = Field(..., gt=0, description="Stop loss price")
    score_ponderado: int = Field(
        ..., ge=0, le=100, description="Confidence score 0-100"
    )
    data_sinal: datetime = Field(..., description="Signal generation timestamp")
    confianca: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence coefficient 0.0-1.0"
    )

    model_config = {"use_enum_values": False}

    @field_validator("ticker", mode="before")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Ticker must be uppercase."""
        if isinstance(v, str):
            return v.upper().replace(".SA", "")
        return v

    @model_validator(mode="after")
    def validate_alvo_vs_stop(self) -> "Signal":
        """Alvo1 must differ from stop_loss."""
        if self.alvo1 == self.stop_loss:
            raise ValueError(
                "alvo1 (target price) cannot equal stop_loss — must differ"
            )
        return self

    @field_validator("alvo2", mode="after")
    @classmethod
    def validate_alvo2_order(cls, v: Optional[float], info) -> Optional[float]:
        """If alvo2 exists, ensure proper ordering."""
        if v is not None and "alvo1" in info.data:
            # For CALL signals: alvo1 > alvo2 > alvo3
            # For PUT signals: order is same
            if not (v < info.data["alvo1"]):
                raise ValueError(
                    "alvo2 must be less than alvo1 (targets should descend)"
                )
        return v

    @field_validator("alvo3", mode="after")
    @classmethod
    def validate_alvo3_order(cls, v: Optional[float], info) -> Optional[float]:
        """If alvo3 exists, ensure proper ordering."""
        if v is not None:
            if "alvo2" in info.data and info.data["alvo2"] is not None:
                if not (v < info.data["alvo2"]):
                    raise ValueError(
                        "alvo3 must be less than alvo2 (targets should descend)"
                    )
            elif "alvo1" in info.data:
                if not (v < info.data["alvo1"]):
                    raise ValueError(
                        "alvo3 must be less than alvo1 (targets should descend)"
                    )
        return v

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Signal(ticker={self.ticker}, tipo={self.tipo_sinal.value}, "
            f"alvo1={self.alvo1}, stop={self.stop_loss}, score={self.score_ponderado})"
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return self.model_dump()

    def to_json_str(self) -> str:
        """Convert to JSON string."""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def json_schema_str(cls) -> str:
        """Get JSON schema as string."""
        import json

        return json.dumps(cls.model_json_schema())

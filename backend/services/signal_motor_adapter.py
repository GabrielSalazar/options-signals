"""Adapter to convert motor output to typed Signal instances."""
import logging
from datetime import datetime
from typing import Optional

from backend.core.models.signal import Signal, SignalType

logger = logging.getLogger("signal_adapter")


class SignalMotorAdapter:
    """Converts raw motor output (dict) to typed Signal instances.

    Maps from legacy motor dict format to Pydantic Signal model with
    validation and graceful fallback for invalid signals.
    """

    # Mapping from motor tipo_sinal to Signal SignalType
    TIPO_MAPPING = {
        "CALL_ALTA": SignalType.CALL_ALTA,
        "CALL_REVERSAO": SignalType.CALL_REVERSAO,
        "CALL_SIDEWAYS": SignalType.CALL_SIDEWAYS,
        "PUT_ALTA": SignalType.PUT_ALTA,
        "PUT_REVERSAO": SignalType.PUT_REVERSAO,
        "PUT_SIDEWAYS": SignalType.PUT_SIDEWAYS,
    }

    @classmethod
    def adapt(cls, motor_output: dict, data_sinal: Optional[datetime] = None) -> Optional[Signal]:
        """Convert motor dict to Signal instance.

        Args:
            motor_output: Raw dict from motor (result of _montar_sinal)
            data_sinal: Signal timestamp (defaults to now)

        Returns:
            Signal instance if valid, None if validation fails gracefully.

        Example:
            ```python
            motor_dict = core_engine._montar_sinal(...)
            signal = SignalMotorAdapter.adapt(motor_dict)
            if signal:
                print(f"Valid signal: {signal}")
            ```
        """
        if not motor_output:
            return None

        try:
            # Extract required fields
            ticker = motor_output.get("ticker")
            tipo_sinal_str = motor_output.get("tipo_sinal")
            alvo1 = motor_output.get("alvo1")
            stop_loss = motor_output.get("stop")
            score_ponderado = motor_output.get("score_ponderado")

            # Validate required fields exist and have sensible values
            if not all([ticker, tipo_sinal_str, alvo1 is not None, stop_loss is not None]):
                logger.warning(
                    f"Motor output missing required fields: "
                    f"ticker={ticker}, tipo_sinal={tipo_sinal_str}, "
                    f"alvo1={alvo1}, stop={stop_loss}"
                )
                return None

            # Map tipo_sinal to enum
            if tipo_sinal_str not in cls.TIPO_MAPPING:
                logger.warning(f"Unknown tipo_sinal: {tipo_sinal_str}")
                return None

            # Extract optional fields
            alvo2 = motor_output.get("alvo2")
            alvo3 = motor_output.get("alvo_final")  # Use alvo_final as alvo3
            confianca = cls._extract_confidence(motor_output)

            # Use provided timestamp or current time
            if data_sinal is None:
                data_sinal = datetime.now()

            # Create Signal instance with validation
            signal = Signal(
                ticker=ticker,
                tipo_sinal=cls.TIPO_MAPPING[tipo_sinal_str],
                alvo1=float(alvo1),
                alvo2=float(alvo2) if alvo2 is not None else None,
                alvo3=float(alvo3) if alvo3 is not None else None,
                stop_loss=float(stop_loss),
                score_ponderado=int(score_ponderado) if score_ponderado is not None else 50,
                data_sinal=data_sinal,
                confianca=confianca,
            )
            return signal

        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Failed to adapt motor output to Signal: {e}")
            return None

    @classmethod
    def adapt_batch(
        cls, motor_outputs: list[dict], data_sinal: Optional[datetime] = None
    ) -> list[Signal]:
        """Convert multiple motor dicts to Signal instances.

        Args:
            motor_outputs: List of raw motor dicts
            data_sinal: Signal timestamp (applied to all)

        Returns:
            List of valid Signal instances (skips invalid ones with logging).
        """
        signals = []
        for output in motor_outputs:
            signal = cls.adapt(output, data_sinal)
            if signal:
                signals.append(signal)
        return signals

    @staticmethod
    def _extract_confidence(motor_output: dict) -> Optional[float]:
        """Extract confidence coefficient from motor output.

        Uses multiple heuristics to derive a 0.0-1.0 confidence value
        from available motor metrics.

        Priority:
        1. score_ponderado / 100 (if available and within bounds)
        2. IV rank normalized (if available)
        3. Consensus decision (if available)
        4. Default to None
        """
        # Strategy 1: Use score_ponderado as base (0-100 → 0.0-1.0)
        score = motor_output.get("score_ponderado")
        if score is not None:
            try:
                confidence = float(score) / 100.0
                if 0.0 <= confidence <= 1.0:
                    return confidence
            except (ValueError, TypeError):
                pass

        # Strategy 2: IV rank (0-100 → 0.0-1.0)
        iv_rank = motor_output.get("iv_rank")
        if iv_rank is not None:
            try:
                confidence = float(iv_rank) / 100.0
                if 0.0 <= confidence <= 1.0:
                    return confidence
            except (ValueError, TypeError):
                pass

        # Strategy 3: Consensus decision (if boolean or 0/1)
        consenso = motor_output.get("consenso_decisao")
        if consenso is not None:
            try:
                if isinstance(consenso, bool):
                    return 0.9 if consenso else 0.1
                elif consenso in (0, 1):
                    return 0.9 if consenso else 0.1
            except (ValueError, TypeError):
                pass

        # No confidence available
        return None

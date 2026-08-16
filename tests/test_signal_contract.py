import json
from datetime import datetime
import pytest
from backend.core.models.signal import Signal, SignalType
from backend.services.signal_motor_adapter import SignalMotorAdapter

class TestSignalContract:
    """Test Signal contract between backend and frontend."""

    def test_signal_enum_types(self):
        """All expected signal types exist."""
        expected_types = {
            "CALL_ALTA", "CALL_REVERSAO", "CALL_SIDEWAYS",
            "PUT_ALTA", "PUT_REVERSAO", "PUT_SIDEWAYS",
        }
        actual_types = {member.value for member in SignalType}
        assert actual_types == expected_types

    def test_signal_roundtrip_json(self):
        """Signal to JSON to Signal preserves data."""
        original = Signal(
            ticker="PETR4", tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50, stop_loss=26.00, score_ponderado=75,
            data_sinal=datetime(2026, 8, 15, 10, 30, 0),
        )
        json_str = original.model_dump_json()
        parsed_dict = json.loads(json_str)
        reconstructed = Signal(**parsed_dict)
        assert reconstructed.ticker == original.ticker

    def test_adapter_produces_valid_signals(self):
        """Adapter produces valid Signals."""
        motor_outputs = [
            {
                "ticker": "PETR4", "tipo_sinal": "CALL_ALTA",
                "alvo1": 27.00, "alvo2": 28.00, "alvo_final": 29.00,
                "stop": 26.00, "score_ponderado": 75,
            }
        ]
        signals = SignalMotorAdapter.adapt_batch(motor_outputs)
        assert len(signals) == 1
        assert signals[0].alvo1 < signals[0].alvo2 < signals[0].alvo3

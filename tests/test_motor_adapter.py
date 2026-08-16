"""Tests for signal motor adapter."""
from datetime import datetime

import pytest

from backend.core.models.signal import Signal, SignalType
from backend.services.signal_motor_adapter import SignalMotorAdapter


class TestSignalMotorAdapterValid:
    """Test successful adaptations from motor output to Signal."""

    def test_adapt_minimal_motor_output(self):
        """Adapt minimal valid motor output to Signal."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.ticker == "PETR4"
        assert signal.tipo_sinal == SignalType.CALL_ALTA
        assert signal.alvo1 == 27.50
        assert signal.stop_loss == 26.00
        assert signal.score_ponderado == 75

    def test_adapt_complete_motor_output(self):
        """Adapt complete motor output with all fields."""
        now = datetime.now()
        motor_output = {
            "ticker": "VALE3",
            "tipo_sinal": "PUT_ALTA",
            "alvo1": 19.50,
            "alvo2": 19.00,
            "alvo_final": 18.50,
            "stop": 20.00,
            "score_ponderado": 85,
            "iv_rank": 70,
            "consenso_decisao": True,
        }
        signal = SignalMotorAdapter.adapt(motor_output, data_sinal=now)
        assert signal is not None
        assert signal.alvo2 == 19.00
        assert signal.alvo3 == 18.50
        assert signal.confianca == 0.85  # score_ponderado / 100

    def test_adapt_all_signal_types(self):
        """Test adapter with all SignalType variants."""
        signal_types = [
            "CALL_ALTA",
            "CALL_REVERSAO",
            "CALL_SIDEWAYS",
            "PUT_ALTA",
            "PUT_REVERSAO",
            "PUT_SIDEWAYS",
        ]
        for tipo in signal_types:
            motor_output = {
                "ticker": "PETR4",
                "tipo_sinal": tipo,
                "alvo1": 27.50,
                "stop": 26.00,
                "score_ponderado": 75,
            }
            signal = SignalMotorAdapter.adapt(motor_output)
            assert signal is not None
            assert signal.tipo_sinal.value == tipo


class TestSignalMotorAdapterConfidence:
    """Test confidence extraction from various motor outputs."""

    def test_confidence_from_score_ponderado(self):
        """Extract confidence from score_ponderado (primary strategy)."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": 85,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.confianca == 0.85

    def test_confidence_from_iv_rank(self):
        """Extract confidence from IV rank when score_ponderado missing."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": None,
            "iv_rank": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.confianca == 0.75

    def test_confidence_from_consenso(self):
        """Extract confidence from consenso_decisao."""
        # Boolean True
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": None,
            "iv_rank": None,
            "consenso_decisao": True,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.confianca == 0.9

        # Boolean False
        motor_output["consenso_decisao"] = False
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.confianca == 0.1

    def test_confidence_default_none(self):
        """Default to None when no confidence source available."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": None,
            "iv_rank": None,
            "consenso_decisao": None,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.confianca is None


class TestSignalMotorAdapterInvalid:
    """Test graceful handling of invalid motor outputs."""

    def test_adapt_empty_dict(self):
        """Empty dict returns None."""
        signal = SignalMotorAdapter.adapt({})
        assert signal is None

    def test_adapt_none(self):
        """None input returns None."""
        signal = SignalMotorAdapter.adapt(None)
        assert signal is None

    def test_missing_required_field_ticker(self):
        """Missing ticker returns None."""
        motor_output = {
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None

    def test_missing_required_field_tipo_sinal(self):
        """Missing tipo_sinal returns None."""
        motor_output = {
            "ticker": "PETR4",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None

    def test_missing_required_field_alvo1(self):
        """Missing alvo1 returns None."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "stop": 26.00,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None

    def test_missing_required_field_stop(self):
        """Missing stop returns None."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.50,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None

    def test_invalid_tipo_sinal(self):
        """Invalid tipo_sinal returns None."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "INVALID_TYPE",
            "alvo1": 27.50,
            "stop": 26.00,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None

    def test_alvo1_equals_stop(self):
        """Signal validation catches alvo1 == stop (fails in Signal model)."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": 27.00,
            "stop": 27.00,  # Same value = invalid
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None

    def test_invalid_numeric_values(self):
        """Non-numeric target/stop values return None."""
        motor_output = {
            "ticker": "PETR4",
            "tipo_sinal": "CALL_ALTA",
            "alvo1": "not_a_number",
            "stop": 26.00,
            "score_ponderado": 75,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is None


class TestSignalMotorAdapterBatch:
    """Test batch adaptation."""

    def test_adapt_batch_mixed_valid_invalid(self):
        """Batch adapter skips invalid signals and returns only valid ones."""
        motor_outputs = [
            {
                "ticker": "PETR4",
                "tipo_sinal": "CALL_ALTA",
                "alvo1": 27.50,
                "stop": 26.00,
                "score_ponderado": 75,
            },
            {
                "ticker": "VALE3",
                # Missing tipo_sinal - invalid
                "alvo1": 19.50,
                "stop": 18.50,
                "score_ponderado": 80,
            },
            {
                "ticker": "BBAS3",
                "tipo_sinal": "PUT_ALTA",
                "alvo1": 8.50,
                "stop": 9.00,
                "score_ponderado": 70,
            },
        ]
        signals = SignalMotorAdapter.adapt_batch(motor_outputs)
        assert len(signals) == 2
        assert signals[0].ticker == "PETR4"
        assert signals[1].ticker == "BBAS3"

    def test_adapt_batch_empty_list(self):
        """Empty input list returns empty list."""
        signals = SignalMotorAdapter.adapt_batch([])
        assert signals == []

    def test_adapt_batch_all_invalid(self):
        """Batch with all invalid signals returns empty list."""
        motor_outputs = [
            {},  # Missing required fields
            {"ticker": "PETR4"},  # Missing fields
            None,  # None
        ]
        signals = SignalMotorAdapter.adapt_batch(motor_outputs)
        assert signals == []

    def test_adapt_batch_timestamp(self):
        """Batch applies same timestamp to all signals."""
        now = datetime(2026, 8, 15, 10, 30, 0)
        motor_outputs = [
            {
                "ticker": "PETR4",
                "tipo_sinal": "CALL_ALTA",
                "alvo1": 27.50,
                "stop": 26.00,
                "score_ponderado": 75,
            },
            {
                "ticker": "VALE3",
                "tipo_sinal": "PUT_ALTA",
                "alvo1": 19.50,
                "stop": 18.50,
                "score_ponderado": 80,
            },
        ]
        signals = SignalMotorAdapter.adapt_batch(motor_outputs, data_sinal=now)
        assert all(s.data_sinal == now for s in signals)


class TestSignalMotorAdapterIntegration:
    """Integration tests with realistic motor outputs."""

    def test_adapt_realistic_motor_output(self):
        """Test with realistic motor output structure."""
        motor_output = {
            "emoji": "📈",
            "ticker": "PETR4",
            "nome": "Petrobras",
            "tipo_sinal": "CALL_ALTA",
            "direcao": "ALTA",
            "preco_acao": 27.35,
            "ticker_opcao": "PETRK40",
            "strike_ref": 40.0,
            "dist_otm_pct": 45.5,
            "hv_20d": 0.25,
            "iv_mercado": 0.30,
            "iv_impl": 0.28,
            "iv_source": "B3",
            "iv_rank": 72,
            "dte": 21,
            "premio_est": 1.50,
            "preco_tela": 1.60,
            "entrada_min": 1.45,
            "entrada_max": 1.75,
            "alvo1": 27.50,
            "alvo2": 28.00,
            "alvo_final": 29.00,
            "stop": 26.50,
            "score": 85,
            "score_ponderado": 82,
            "score_tecnico": 85,
            "rsi": 65.5,
            "stoch_k": 78.0,
            "vol_ratio": 1.2,
            "consenso_decisao": True,
        }
        signal = SignalMotorAdapter.adapt(motor_output)
        assert signal is not None
        assert signal.ticker == "PETR4"
        assert signal.tipo_sinal == SignalType.CALL_ALTA
        assert signal.alvo1 == 27.50
        assert signal.alvo2 == 28.00
        assert signal.alvo3 == 29.00
        assert signal.stop_loss == 26.50
        assert signal.score_ponderado == 82
        # Confidence should use score_ponderado: 82/100 = 0.82
        assert signal.confianca == 0.82

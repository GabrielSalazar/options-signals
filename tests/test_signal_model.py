"""Testes para Signal model Pydantic."""
import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.core.models.signal import Signal, SignalType


class TestSignalModelValid:
    """Testes de validação do modelo Signal."""

    def test_create_signal_minimal(self):
        """Signal com campos mínimos obrigatórios."""
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime.now(),
        )
        assert signal.ticker == "PETR4"
        assert signal.tipo_sinal == SignalType.CALL_ALTA
        assert signal.alvo1 == 27.50
        assert signal.stop_loss == 26.00
        assert signal.score_ponderado == 75

    def test_create_signal_completo(self):
        """Signal com todos os campos."""
        now = datetime.now()
        signal = Signal(
            ticker="VALE3",
            tipo_sinal=SignalType.PUT_ALTA,
            alvo1=19.50,
            alvo2=19.00,
            alvo3=18.50,
            stop_loss=20.00,
            score_ponderado=85,
            data_sinal=now,
            confianca=0.92,
        )
        assert signal.alvo2 == 19.00
        assert signal.alvo3 == 18.50
        assert signal.confianca == 0.92

    def test_signal_to_dict(self):
        """Serializar Signal para dict."""
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime(2026, 8, 15, 10, 30, 0),
        )
        data = signal.model_dump()
        assert data["ticker"] == "PETR4"
        assert data["tipo_sinal"] == "CALL_ALTA"
        assert isinstance(data["data_sinal"], datetime)

    def test_signal_to_json(self):
        """Serializar Signal para JSON."""
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime(2026, 8, 15, 10, 30, 0),
        )
        json_str = signal.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["ticker"] == "PETR4"
        assert "data_sinal" in parsed

    def test_signal_from_dict(self):
        """Criar Signal a partir de dict."""
        data = {
            "ticker": "BBAS3",
            "tipo_sinal": "PUT_ALTA",
            "alvo1": 8.50,
            "stop_loss": 9.00,
            "score_ponderado": 70,
            "data_sinal": datetime.now(),
        }
        signal = Signal(**data)
        assert signal.ticker == "BBAS3"
        assert signal.tipo_sinal == SignalType.PUT_ALTA


class TestSignalValidators:
    """Testes para validators do Signal."""

    def test_score_ponderado_minimum(self):
        """Score não pode ser menor que 0."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                ticker="PETR4",
                tipo_sinal=SignalType.CALL_ALTA,
                alvo1=27.50,
                stop_loss=26.00,
                score_ponderado=-1,
                data_sinal=datetime.now(),
            )
        assert "score_ponderado" in str(exc_info.value)

    def test_score_ponderado_maximum(self):
        """Score não pode ser maior que 100."""
        with pytest.raises(ValidationError) as exc_info:
            Signal(
                ticker="PETR4",
                tipo_sinal=SignalType.CALL_ALTA,
                alvo1=27.50,
                stop_loss=26.00,
                score_ponderado=101,
                data_sinal=datetime.now(),
            )
        assert "score_ponderado" in str(exc_info.value)

    def test_confianca_range(self):
        """Confiança deve estar entre 0 e 1."""
        # Válido: 0.5
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime.now(),
            confianca=0.5,
        )
        assert signal.confianca == 0.5

        # Inválido: 1.5
        with pytest.raises(ValidationError):
            Signal(
                ticker="PETR4",
                tipo_sinal=SignalType.CALL_ALTA,
                alvo1=27.50,
                stop_loss=26.00,
                score_ponderado=75,
                data_sinal=datetime.now(),
                confianca=1.5,
            )

    def test_alvo_precisa_stop_loss(self):
        """Alvo não pode ser igual ao stop loss."""
        with pytest.raises(ValidationError):
            Signal(
                ticker="PETR4",
                tipo_sinal=SignalType.CALL_ALTA,
                alvo1=27.50,
                stop_loss=27.50,  # Mesmo valor = inválido
                score_ponderado=75,
                data_sinal=datetime.now(),
            )

    def test_alvo_ordem_crescente(self):
        """Alvos devem estar em ordem (alvo1 > alvo2 > alvo3)."""
        # Válido: ordem decrescente para venda
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.PUT_ALTA,
            alvo1=28.00,
            alvo2=27.00,
            alvo3=26.00,
            stop_loss=29.00,
            score_ponderado=75,
            data_sinal=datetime.now(),
        )
        assert signal.alvo1 > signal.alvo2 > signal.alvo3

    def test_ticker_uppercase(self):
        """Ticker sempre em uppercase."""
        signal = Signal(
            ticker="petr4",  # lowercase
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime.now(),
        )
        assert signal.ticker == "PETR4"

    def test_tipo_sinal_enum(self):
        """Tipo de sinal deve ser um SignalType válido."""
        # Válido
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime.now(),
        )
        assert isinstance(signal.tipo_sinal, SignalType)

        # Inválido
        with pytest.raises(ValidationError):
            Signal(
                ticker="PETR4",
                tipo_sinal="INVALID_TYPE",  # type: ignore
                alvo1=27.50,
                stop_loss=26.00,
                score_ponderado=75,
                data_sinal=datetime.now(),
            )


class TestSignalMethods:
    """Testes para métodos do Signal."""

    def test_json_schema(self):
        """JSON Schema deve conter todos os campos."""
        schema = Signal.model_json_schema()
        assert "properties" in schema
        assert "ticker" in schema["properties"]
        assert "tipo_sinal" in schema["properties"]
        assert "alvo1" in schema["properties"]
        assert "score_ponderado" in schema["properties"]

    def test_repr(self):
        """String representation do Signal."""
        signal = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=datetime(2026, 8, 15, 10, 30, 0),
        )
        repr_str = repr(signal)
        assert "PETR4" in repr_str
        assert "CALL_ALTA" in repr_str


class TestSignalEquality:
    """Testes para comparação de Signals."""

    def test_signal_equality(self):
        """Dois signals com mesmos dados são iguais."""
        now = datetime(2026, 8, 15, 10, 30, 0)
        signal1 = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=now,
        )
        signal2 = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=now,
        )
        assert signal1 == signal2

    def test_signal_inequality(self):
        """Signals com dados diferentes não são iguais."""
        now = datetime.now()
        signal1 = Signal(
            ticker="PETR4",
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=now,
        )
        signal2 = Signal(
            ticker="VALE3",  # ticker diferente
            tipo_sinal=SignalType.CALL_ALTA,
            alvo1=27.50,
            stop_loss=26.00,
            score_ponderado=75,
            data_sinal=now,
        )
        assert signal1 != signal2

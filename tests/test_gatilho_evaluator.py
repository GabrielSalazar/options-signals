"""Tests for GatilhoEvaluator service."""
import pandas as pd
import pytest

from backend.services.gatilho_evaluator import GatilhoEvaluator


class TestGatilhoEvaluator:
    """Test trigger evaluation."""

    def test_rsi_oversold_alta(self):
        """Detect ALTA trigger on RSI oversold."""
        evaluator = GatilhoEvaluator()
        df = pd.DataFrame()
        ultimo = {"rsi": 25, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "atr": 2, "suporte_20": 98, "resistencia_20": 102, "adx": 0}
        penult = {"rsi": 30, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "suporte_20": 98, "resistencia_20": 102}

        result = evaluator.evaluate(df, ultimo, penult, 100.0, 1000, 1000)

        assert "G1" in result["ids_alta"]
        assert result["score_alta"] >= 15
        assert result["rsi"] == 25

    def test_rsi_overbought_baixa(self):
        """Detect BAIXA trigger on RSI overbought."""
        evaluator = GatilhoEvaluator()
        df = pd.DataFrame()
        ultimo = {"rsi": 75, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "atr": 2, "suporte_20": 98, "resistencia_20": 102, "adx": 0}
        penult = {"rsi": 70, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "suporte_20": 98, "resistencia_20": 102}

        result = evaluator.evaluate(df, ultimo, penult, 100.0, 1000, 1000)

        assert "B1" in result["ids_baixa"]
        assert result["score_baixa"] >= 15

    def test_volume_spike(self):
        """Detect volume spike trigger."""
        evaluator = GatilhoEvaluator()
        df = pd.DataFrame()
        ultimo = {"rsi": 50, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "atr": 2, "suporte_20": 98, "resistencia_20": 102, "adx": 0}
        penult = {"rsi": 50, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "suporte_20": 98, "resistencia_20": 102}

        result = evaluator.evaluate(df, ultimo, penult, 100.0, 1000, 2000)  # vol_med=1000, volume=2000

        # Should detect volume spike (G6, B6)
        assert "G6" in result["ids_alta"] or "B6" in result["ids_baixa"]
        assert result["vol_ratio"] == 2.0

    def test_no_triggers(self):
        """Return empty triggers when conditions not met."""
        evaluator = GatilhoEvaluator()
        df = pd.DataFrame()
        ultimo = {"rsi": 50, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "atr": 2, "suporte_20": 98, "resistencia_20": 102, "adx": 0}
        penult = {"rsi": 50, "stoch_k": 50, "ema9": 100, "ema21": 100, "macd_diff": 0, "suporte_20": 98, "resistencia_20": 102}

        result = evaluator.evaluate(df, ultimo, penult, 100.0, 1000, 1000)

        # Neutral conditions = no strong triggers
        assert result["score_alta"] <= 30 or result["score_baixa"] <= 30

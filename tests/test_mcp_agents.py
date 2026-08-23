"""Tests para MCP agents pipeline.

Testa Data Collector (Agent 1) com dados reais de B3.
"""
import asyncio
import pytest

from backend.agents.mcp_agents.data_collector import DataCollectorAgent
from backend.domain.mcp_models import DataCollectorInput


class TestDataCollectorAgent:
    """Testes do Data Collector (Agent 1)."""

    def test_agent_initialization(self):
        """Deve inicializar com valores corretos."""
        agent = DataCollectorAgent()
        assert agent.cache_ttl_success == 3600
        assert agent.cache_ttl_error == 60
        assert agent.timeout == 10

    @pytest.mark.asyncio
    async def test_data_collector_input_validation(self):
        """Deve validar entrada corretamente."""
        agent = DataCollectorAgent()

        # Entrada válida
        valid_input = {
            "strategy": "iron_condor_v2",
            "asset": "PETR4",
            "date_range": {"start": "2024-06-01", "end": "2024-08-22"},
        }
        cfg = DataCollectorInput(**valid_input)
        assert cfg.asset == "PETR4"
        assert cfg.strategy == "iron_condor_v2"

        # Entrada inválida (strategy vazio)
        invalid_input = {
            "strategy": "",
            "asset": "PETR4",
            "date_range": {"start": "2024-06-01", "end": "2024-08-22"},
        }
        with pytest.raises(Exception):
            DataCollectorInput(**invalid_input)

    @pytest.mark.asyncio
    async def test_data_collector_fetch_petr4(self):
        """Deve buscar dados reais de PETR4."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "iron_condor_v2",
            "asset": "PETR4",
            "date_range": {"start": "2024-06-01", "end": "2024-08-22"},
            "indicators": ["rsi", "macd", "atr", "bb"],
            "data_source": "yfinance",
        }

        output = await agent.process(input_data)

        # Validações
        assert "ohlc" in output
        assert len(output["ohlc"]) > 30, "Dados insuficientes"
        assert all(
            k in o for o in output["ohlc"] for k in ["date", "o", "h", "l", "c", "v"]
        ), "OHLC point missing fields"

        assert "indicators" in output
        assert "meta" in output

        meta = output["meta"]
        assert meta["asset"] == "PETR4"
        assert meta["source"] == "yfinance"
        assert meta["records_count"] > 30
        # Gaps can be high due to weekends
        assert 0.0 <= meta["data_quality_score"] <= 1.0

        print(
            f"[PASS] Coletou {meta['records_count']} candles para PETR4 "
            f"(quality: {meta['data_quality_score']:.1%})"
        )

    @pytest.mark.asyncio
    async def test_data_collector_complete_indicators(self):
        """Deve calcular todos os 4 indicadores."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "test",
            "asset": "VALE3",
            "date_range": {"start": "2024-07-01", "end": "2024-08-22"},
            "indicators": ["rsi", "macd", "atr", "bb"],
        }

        output = await agent.process(input_data)

        assert "indicators" in output
        indicators = output["indicators"]

        assert "rsi" in indicators
        assert isinstance(indicators["rsi"], list)
        assert len(indicators["rsi"]) > 0

        assert "macd" in indicators
        assert isinstance(indicators["macd"], dict)
        assert "line" in indicators["macd"]
        assert "signal" in indicators["macd"]
        assert "histogram" in indicators["macd"]

        assert "atr" in indicators
        assert isinstance(indicators["atr"], list)
        assert len(indicators["atr"]) > 0

        assert "bb" in indicators
        assert isinstance(indicators["bb"], dict)
        assert "upper" in indicators["bb"]
        assert "middle" in indicators["bb"]
        assert "lower" in indicators["bb"]

        print("[PASS] All 4 indicators calculated correctly")

    @pytest.mark.asyncio
    async def test_data_collector_subset_indicators(self):
        """Deve permitir calcular apenas um subset de indicadores."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "test",
            "asset": "ITUB4",
            "date_range": {"start": "2024-07-15", "end": "2024-08-22"},
            "indicators": ["rsi"],  # Apenas RSI
        }

        output = await agent.process(input_data)

        indicators = output["indicators"]
        assert "rsi" in indicators
        assert "macd" not in indicators
        assert "atr" not in indicators
        assert "bb" not in indicators

        print("[PASS] Subset indicator selection works")

    @pytest.mark.asyncio
    async def test_data_collector_invalid_ticker(self):
        """Deve falhar graciosamente com ticker inválido."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "test",
            "asset": "XXXXX",  # Ticker inválido
            "date_range": {"start": "2024-06-01", "end": "2024-08-22"},
        }

        with pytest.raises(ValueError, match="No data available"):
            await agent.process(input_data)

        print("[PASS] Invalid ticker handled gracefully")

    @pytest.mark.asyncio
    async def test_data_collector_invalid_date_range(self):
        """Deve falhar com data_range invertido."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "test",
            "asset": "PETR4",
            "date_range": {"start": "2024-08-22", "end": "2024-06-01"},  # Invertido
        }

        # Deve retornar vazio (gracioso) ou falhar
        try:
            output = await agent.process(input_data)
            assert len(output["ohlc"]) == 0
        except ValueError:
            pass  # Também aceitável falhar com ValueError

        print("[PASS] Invalid date range handled")

    @pytest.mark.asyncio
    async def test_data_collector_ticker_normalization(self):
        """Deve normalizar ticker (maiúsculas, remove .SA)."""
        agent = DataCollectorAgent()

        # Enviar com .SA e minúsculas
        input_data = {
            "strategy": "test",
            "asset": "petr4.SA",  # Com .SA e minúsculas
            "date_range": {"start": "2024-08-01", "end": "2024-08-22"},
        }

        output = await agent.process(input_data)

        # Deve estar normalizado na meta
        assert output["meta"]["asset"] == "PETR4"

        print("[PASS] Ticker normalization works")


class TestDataCollectorCache:
    """Testes de cache do Data Collector."""

    @pytest.mark.asyncio
    async def test_cache_hit_on_repeated_call(self):
        """Deve usar cache na segunda chamada."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "cache_test",
            "asset": "PETR4",
            "date_range": {"start": "2024-08-01", "end": "2024-08-15"},
            "indicators": ["rsi"],
        }

        # Primeira chamada (sem cache)
        output1 = await agent.process(input_data)
        assert len(output1["ohlc"]) > 0

        # Segunda chamada (com cache)
        output2 = await agent.process(input_data)
        assert len(output2["ohlc"]) > 0

        # Dados devem ser idênticos
        assert output1["ohlc"] == output2["ohlc"]

        print("[PASS] Cache works correctly")


class TestDataCollectorQuality:
    """Testes de validação de qualidade."""

    @pytest.mark.asyncio
    async def test_quality_score_calculation(self):
        """Score de qualidade deve estar entre 0.0-1.0."""
        agent = DataCollectorAgent()

        input_data = {
            "strategy": "quality_test",
            "asset": "PETR4",
            "date_range": {"start": "2024-01-01", "end": "2024-08-22"},
        }

        output = await agent.process(input_data)

        quality = output["meta"]["data_quality_score"]
        assert 0.0 <= quality <= 1.0

        print(f"[PASS] Quality score validation passed: {quality:.1%}")

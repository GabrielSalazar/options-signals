"""Integration tests for OptionBuilder with OptionPricer.

Testes validam que OptionBuilder integra corretamente precificação genérica.
Todos os testes usam strikes/ativos arbitrários (não específicos de ticker).
"""
import pytest

# Importa builder de estruturas de opções integrado com Black-Scholes
from backend.services.option_builder import OptionBuilder


class TestOptionBuilderIntegration:
    """Test OptionBuilder with Black-Scholes pricing."""

    def test_builder_creates_with_default_rate(self):
        """Builder should initialize with default risk-free rate."""
        builder = OptionBuilder()
        assert builder.risk_free_rate == 0.10

    def test_builder_accepts_custom_rate(self):
        """Builder should accept custom risk-free rate."""
        builder = OptionBuilder(risk_free_rate=0.05)
        assert builder.risk_free_rate == 0.05

    def test_build_call_option(self):
        """Build should create valid CALL option structure."""
        builder = OptionBuilder(risk_free_rate=0.10)

        result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=9,
            strike_ref=105.0,
            dist_otm=5.0,
            iv_impl=0.25,
            hv_20d=0.20,
            dividend_yield=0.0,
        )

        # Validate structure has required fields
        assert "premium" in result
        assert "delta" in result
        assert "gamma" in result
        assert "vega" in result
        assert "theta" in result
        assert "rho" in result
        assert result["strike_ref"] == 105.0
        assert result["dte"] == 9

    def test_build_put_option(self):
        """Build should create valid PUT option structure."""
        builder = OptionBuilder()

        result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="PUT_BAIXA",
            direcao_label="BAIXA",
            dte=30,  # Longer DTE for more time value
            strike_ref=95.0,
            dist_otm=5.0,
            iv_impl=0.25,
            hv_20d=0.20,
        )

        # Verify structure has all Greeks (premium may be low for OTM)
        assert "premium" in result
        assert result["delta"] < 0  # PUT delta is negative
        assert "gamma" in result
        assert result["theta"] < 0  # Time decay hurts long put

    def test_greek_values_reasonable(self):
        """Greeks should be within reasonable bounds."""
        builder = OptionBuilder()

        result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=100.0,
            dist_otm=0.0,  # ATM
            iv_impl=0.20,
            hv_20d=0.20,
        )

        # Delta should be ~0.5 for ATM call
        assert 0.40 < result["delta"] < 0.65
        # Gamma should be positive
        assert result["gamma"] > 0
        # Vega should be positive
        assert result["vega"] > 0
        # Premium should be positive
        assert result["premium"] > 0

    def test_iv_fallback_to_hv(self):
        """Should use HV when IV is zero or missing."""
        builder = OptionBuilder()

        result_with_iv = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=105.0,
            dist_otm=5.0,
            iv_impl=0.30,  # High IV
            hv_20d=0.10,   # Low HV
        )

        result_without_iv = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=105.0,
            dist_otm=5.0,
            iv_impl=0.0,   # No IV
            hv_20d=0.10,   # Use this
        )

        # Higher IV should give higher premium
        assert result_with_iv["premium"] > result_without_iv["premium"]

    def test_dividend_yield_affects_delta(self):
        """Dividend yield should decrease CALL delta."""
        builder = OptionBuilder()

        result_no_div = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=100.0,
            dist_otm=0.0,
            iv_impl=0.20,
            hv_20d=0.20,
            dividend_yield=0.0,
        )

        result_with_div = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=100.0,
            dist_otm=0.0,
            iv_impl=0.20,
            hv_20d=0.20,
            dividend_yield=0.05,  # 5% dividend
        )

        # Dividend reduces CALL delta (cost of carry)
        assert result_with_div["delta"] < result_no_div["delta"]

    def test_moneyness_calculated(self):
        """Moneyness should be spot/strike."""
        builder = OptionBuilder()

        result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=110.0,
            dist_otm=10.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        expected_moneyness = 100.0 / 110.0
        assert abs(result["moneyness"] - expected_moneyness) < 0.0001

    def test_targets_calculated_correctly(self):
        """Targets should be above entry for CALL, below for PUT."""
        builder = OptionBuilder()

        call_result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=105.0,
            dist_otm=5.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        # Targets should progress: preco < alvo1 < alvo2 < alvo_final
        assert call_result["alvo1"] > 100.0
        assert call_result["alvo2"] > call_result["alvo1"]
        assert call_result["alvo_final"] > call_result["alvo2"]
        # Stop should be below entry
        assert call_result["stop"] < 100.0

    def test_put_targets_inverted(self):
        """PUT targets should be below entry."""
        builder = OptionBuilder()

        put_result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="PUT_BAIXA",
            direcao_label="BAIXA",
            dte=30,
            strike_ref=95.0,
            dist_otm=5.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        # Targets should progress downward
        assert put_result["alvo1"] < 100.0
        assert put_result["alvo2"] < put_result["alvo1"]
        assert put_result["alvo_final"] < put_result["alvo2"]
        # Stop should be above entry
        assert put_result["stop"] > 100.0

    def test_rr_ratios_calculated(self):
        """R/R ratios should be positive (reward/risk)."""
        builder = OptionBuilder()

        result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=105.0,
            dist_otm=5.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        # R/R should increase with target level
        assert result["rr_alvo1"] > 0
        assert result["rr_alvo2"] > result["rr_alvo1"]
        assert result["rr_final"] > result["rr_alvo2"]

    def test_intrinsic_and_time_value(self):
        """Intrinsic + time = premium."""
        builder = OptionBuilder()

        result = builder.build(
            ticker_base="TEST",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=95.0,  # ITM call
            dist_otm=-5.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        intrinsic_plus_time = result["intrinsic_value"] + result["time_value"]
        assert abs(intrinsic_plus_time - result["premium"]) < 0.01

    def test_generic_across_different_underlyings(self):
        """Builder should work identically for different underlyings."""
        builder = OptionBuilder()

        # Price same option on different tickers/prices
        result_100 = builder.build(
            ticker_base="TICKER1",
            preco=100.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=105.0,
            dist_otm=5.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        result_50 = builder.build(
            ticker_base="TICKER2",
            preco=50.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=30,
            strike_ref=52.5,  # Same 5% OTM
            dist_otm=5.0,
            iv_impl=0.20,
            hv_20d=0.20,
        )

        # Options have similar structure (same OTM%, same IV, same DTE)
        # So moneyness and relative Greeks should be similar
        assert abs(result_100["moneyness"] - result_50["moneyness"]) < 0.01
        # Delta and gamma percentages should be similar
        assert abs(result_100["delta"] - result_50["delta"]) < 0.1


class TestOptionBuilderBackwardCompatibility:
    """Test that integration doesn't break existing API."""

    def test_build_returns_expected_fields(self):
        """Build should return dict with all expected fields."""
        builder = OptionBuilder()

        result = builder.build(
            ticker_base="PETR4",
            preco=25.0,
            tipo_sinal="CALL_ALTA",
            direcao_label="ALTA",
            dte=9,
            strike_ref=26.0,
            dist_otm=4.0,
            iv_impl=0.30,
            hv_20d=0.25,
        )

        expected_fields = [
            "ticker_opcao",
            "strike_ref",
            "dist_otm",
            "dte",
            "premium",
            "delta",
            "gamma",
            "vega",
            "theta",
            "rho",
            "entrada_min",
            "entrada_max",
            "alvo1",
            "alvo2",
            "alvo_final",
            "stop",
            "book_until",
            "rr_alvo1",
            "rr_alvo2",
            "rr_final",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

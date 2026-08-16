"""Tests for generic option pricing engine.

Tests validate pricing for ANY underlying asset, not specific stocks.
All tests use standard Black-Scholes assumptions.
"""
import pytest
from datetime import datetime, timedelta

from backend.domain.option_pricing import (
    OptionPricer,
    OptionInput,
    OptionType,
)


class TestOptionPricerBasic:
    """Test generic Black-Scholes pricing."""

    def test_atm_call_has_50pct_delta(self):
        """At-the-money call should have ~0.5 delta (adjusted for rates)."""
        pricer = OptionPricer()
        result = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=0.25,  # 3 months
                volatility=0.20,
                risk_free_rate=0.05,
            )
        )
        # With positive rates, ATM delta is slightly > 0.5
        assert 0.50 < result.delta < 0.60, f"ATM call delta should be ~0.55, got {result.delta}"

    def test_itm_call_has_high_delta(self):
        """In-the-money call (spot > strike) should have high delta."""
        pricer = OptionPricer()
        result = pricer.price(
            OptionInput(
                spot_price=110.0,
                strike_price=100.0,
                time_to_expiry=0.25,
                volatility=0.20,
                risk_free_rate=0.05,
            )
        )
        assert result.delta > 0.75, f"ITM call delta should be > 0.75, got {result.delta}"

    def test_otm_call_has_low_delta(self):
        """Out-of-the-money call (spot < strike) should have low delta."""
        pricer = OptionPricer()
        result = pricer.price(
            OptionInput(
                spot_price=90.0,
                strike_price=100.0,
                time_to_expiry=0.25,
                volatility=0.20,
                risk_free_rate=0.05,
            )
        )
        assert result.delta < 0.25, f"OTM call delta should be < 0.25, got {result.delta}"

    def test_call_and_put_both_have_positive_value(self):
        """Both calls and puts should have positive premium."""
        pricer = OptionPricer()

        S, K, T, sigma, r = 100.0, 100.0, 0.25, 0.20, 0.05

        call = pricer.price(
            OptionInput(
                spot_price=S,
                strike_price=K,
                time_to_expiry=T,
                volatility=sigma,
                risk_free_rate=r,
                dividend_yield=0.0,
                option_type=OptionType.CALL,
            )
        )

        put = pricer.price(
            OptionInput(
                spot_price=S,
                strike_price=K,
                time_to_expiry=T,
                volatility=sigma,
                risk_free_rate=r,
                dividend_yield=0.0,
                option_type=OptionType.PUT,
            )
        )

        # Both should have positive value
        assert call.premium > 0, f"Call premium should be positive, got {call.premium}"
        assert put.premium > 0, f"Put premium should be positive, got {put.premium}"


class TestOptionPricerGreeks:
    """Test Greek calculations."""

    def test_gamma_always_positive(self):
        """Gamma should always be positive (for both calls and puts)."""
        pricer = OptionPricer()

        for strike in [90, 100, 110]:
            call = pricer.price(
                OptionInput(
                    spot_price=100.0,
                    strike_price=float(strike),
                    time_to_expiry=0.25,
                    volatility=0.20,
                    risk_free_rate=0.05,
                )
            )
            assert call.gamma > 0, f"Gamma should be positive, got {call.gamma}"

    def test_gamma_peaks_atm(self):
        """Gamma peaks at-the-money (ATM)."""
        pricer = OptionPricer()

        gammas = {}
        for strike in [95, 100, 105]:
            result = pricer.price(
                OptionInput(
                    spot_price=100.0,
                    strike_price=float(strike),
                    time_to_expiry=0.25,
                    volatility=0.20,
                    risk_free_rate=0.05,
                )
            )
            gammas[strike] = result.gamma

        # ATM gamma should be highest
        assert gammas[100] > gammas[95], f"ATM gamma {gammas[100]} should > OTM {gammas[95]}"
        assert gammas[100] > gammas[105], f"ATM gamma {gammas[100]} should > OTM {gammas[105]}"

    def test_vega_positive_for_options(self):
        """Vega should be positive (price increases with volatility)."""
        pricer = OptionPricer()

        for strike in [90, 100, 110]:
            result = pricer.price(
                OptionInput(
                    spot_price=100.0,
                    strike_price=float(strike),
                    time_to_expiry=0.25,
                    volatility=0.20,
                    risk_free_rate=0.05,
                )
            )
            assert result.vega > 0, f"Vega should be positive, got {result.vega}"

    def test_theta_exists_for_options(self):
        """Theta should be negative for long calls (time decay)."""
        pricer = OptionPricer()

        result = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=105.0,  # OTM call
                time_to_expiry=30 / 365.0,
                volatility=0.20,
                risk_free_rate=0.05,
            )
        )
        # Long call theta is negative (time decay hurts the position)
        assert result.theta < 0, f"Long call theta should be negative, got {result.theta}"


class TestImpliedVolatility:
    """Test IV calculation by inverting Black-Scholes."""

    def test_iv_recovery(self):
        """IV calculated from price should recover original volatility."""
        pricer = OptionPricer()

        original_iv = 0.25
        option_input = OptionInput(
            spot_price=100.0,
            strike_price=105.0,
            time_to_expiry=0.25,
            volatility=original_iv,
            risk_free_rate=0.05,
        )

        # Price with known IV
        result = pricer.price(option_input)
        market_price = result.premium

        # Recover IV from price
        input_for_iv = OptionInput(
            spot_price=100.0,
            strike_price=105.0,
            time_to_expiry=0.25,
            volatility=0.0,  # Irrelevant, will be calculated
            risk_free_rate=0.05,
        )
        recovered_iv = pricer.implied_volatility(market_price, input_for_iv)

        assert recovered_iv is not None
        assert abs(recovered_iv - original_iv) < 0.001, \
            f"IV recovery failed: {recovered_iv:.4f} != {original_iv:.4f}"

    def test_iv_increases_with_price(self):
        """Higher market price → higher implied volatility."""
        pricer = OptionPricer()

        option_input_low_vol = OptionInput(
            spot_price=100.0,
            strike_price=105.0,
            time_to_expiry=0.25,
            volatility=0.15,
            risk_free_rate=0.05,
        )
        price_low_vol = pricer.price(option_input_low_vol).premium

        option_input_high_vol = OptionInput(
            spot_price=100.0,
            strike_price=105.0,
            time_to_expiry=0.25,
            volatility=0.35,
            risk_free_rate=0.05,
        )
        price_high_vol = pricer.price(option_input_high_vol).premium

        # Higher vol → higher price
        assert price_high_vol > price_low_vol

        # Recover IV from both prices
        input_for_iv = OptionInput(
            spot_price=100.0,
            strike_price=105.0,
            time_to_expiry=0.25,
            volatility=0.0,
            risk_free_rate=0.05,
        )

        iv_low = pricer.implied_volatility(price_low_vol, input_for_iv)
        iv_high = pricer.implied_volatility(price_high_vol, input_for_iv)

        assert iv_high > iv_low, f"Higher price should have higher IV: {iv_high} > {iv_low}"


class TestMoneyness:
    """Test moneyness and OTM percentage calculations."""

    def test_pct_otm_call(self):
        """Test OTM% calculation for calls."""
        pricer = OptionPricer()

        option = OptionInput(
            spot_price=100.0,
            strike_price=110.0,  # 10% OTM
            time_to_expiry=0.25,
            volatility=0.20,
            risk_free_rate=0.05,
            option_type=OptionType.CALL,
        )

        otm_pct = pricer.calculate_pct_otm(option)
        assert abs(otm_pct - 10.0) < 0.01, f"Should be 10% OTM, got {otm_pct}%"

    def test_pct_otm_put(self):
        """Test OTM% calculation for puts."""
        pricer = OptionPricer()

        option = OptionInput(
            spot_price=100.0,
            strike_price=90.0,  # 10% OTM (for put, lower strike is OTM)
            time_to_expiry=0.25,
            volatility=0.20,
            risk_free_rate=0.05,
            option_type=OptionType.PUT,
        )

        otm_pct = pricer.calculate_pct_otm(option)
        assert abs(otm_pct - 10.0) < 0.01, f"Should be 10% OTM, got {otm_pct}%"

    def test_moneyness(self):
        """Test moneyness ratio (S/K)."""
        pricer = OptionPricer()

        option = OptionInput(
            spot_price=100.0,
            strike_price=110.0,
            time_to_expiry=0.25,
            volatility=0.20,
            risk_free_rate=0.05,
        )

        result = pricer.price(option)
        expected_moneyness = 100.0 / 110.0
        assert abs(result.moneyness - expected_moneyness) < 0.0001, \
            f"Moneyness should be {expected_moneyness}, got {result.moneyness}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_time_to_expiry_call(self):
        """Call at expiry should equal intrinsic value."""
        pricer = OptionPricer()

        result = pricer.price(
            OptionInput(
                spot_price=110.0,
                strike_price=100.0,
                time_to_expiry=0.0,
                volatility=0.20,
                risk_free_rate=0.05,
            )
        )

        intrinsic = max(110.0 - 100.0, 0)
        assert abs(result.premium - intrinsic) < 0.01, \
            f"At expiry, premium should equal intrinsic: {result.premium} == {intrinsic}"

    def test_zero_time_to_expiry_put(self):
        """Put at expiry should equal intrinsic value."""
        pricer = OptionPricer()

        result = pricer.price(
            OptionInput(
                spot_price=90.0,
                strike_price=100.0,
                time_to_expiry=0.0,
                volatility=0.20,
                risk_free_rate=0.05,
                option_type=OptionType.PUT,
            )
        )

        intrinsic = max(100.0 - 90.0, 0)
        assert abs(result.premium - intrinsic) < 0.01

    def test_very_low_volatility(self):
        """Pricing should handle very low volatility gracefully."""
        pricer = OptionPricer()

        result = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=105.0,
                time_to_expiry=0.25,
                volatility=0.001,  # Very low
                risk_free_rate=0.05,
            )
        )

        # Should still produce reasonable output
        assert result.premium >= 0
        assert 0 <= result.delta <= 1

    def test_high_volatility(self):
        """Pricing should handle high volatility gracefully."""
        pricer = OptionPricer()

        result = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=105.0,
                time_to_expiry=0.25,
                volatility=2.0,  # 200% volatility
                risk_free_rate=0.05,
            )
        )

        # Should still produce reasonable output
        assert result.premium >= 0
        assert 0 <= result.delta <= 1

    def test_dividend_yield_effect_on_call_delta(self):
        """Higher dividend yield should decrease call delta (cost of carry)."""
        pricer = OptionPricer()

        call_no_div = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=0.25,
                volatility=0.20,
                risk_free_rate=0.05,
                dividend_yield=0.0,
            )
        )

        call_with_div = pricer.price(
            OptionInput(
                spot_price=100.0,
                strike_price=100.0,
                time_to_expiry=0.25,
                volatility=0.20,
                risk_free_rate=0.05,
                dividend_yield=0.05,
            )
        )

        assert call_with_div.delta < call_no_div.delta, \
            "Dividend yield should reduce call delta"


class TestTimeConversion:
    """Test time-to-expiry conversions."""

    def test_time_to_expiry_calculation(self):
        """Test conversion of datetime to years."""
        pricer = OptionPricer()

        now = datetime(2026, 8, 16)
        expiry = datetime(2026, 8, 25)  # 9 days

        years = pricer.time_to_expiry_years(expiry, now)
        expected_years = 9 / 365.25

        assert abs(years - expected_years) < 0.0001, \
            f"9 days should be {expected_years:.6f} years, got {years:.6f}"

    def test_negative_time_handled(self):
        """Negative time (past expiry) should be clamped to 0."""
        pricer = OptionPricer()

        now = datetime(2026, 8, 25)
        expiry = datetime(2026, 8, 16)  # Past expiry

        years = pricer.time_to_expiry_years(expiry, now)

        assert years == 0, f"Past expiry should give 0 years, got {years}"

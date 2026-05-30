"""
Testes unitários para o módulo greeks.py — Black-Scholes e gregas.

Cobre:
  - bs_call_price / bs_put_price com valores conhecidos
  - Put-Call Parity
  - calculate_greeks (Delta, Gamma, Theta, Vega, Rho, POP)
  - implied_volatility convergência
  - Edge cases (T=0, sigma=0, etc.)
"""
import pytest
import math
from backend.domain.greeks import (
    bs_call_price, bs_put_price,
    calculate_greeks, implied_volatility,
    _d1_d2, RISK_FREE_RATE_DEFAULT,
)


# ── Constantes de teste ──────────────────────────────────────────────────────

S = 100.0    # Preço do ativo subjacente
K = 100.0    # Strike ATM
T = 30 / 365 # 30 dias em anos
R = 0.135    # Selic ~13.5%
SIGMA = 0.30 # Vol de 30%


class TestBlackScholesPrice:
    """Testes de precificação Call/Put."""

    def test_call_price_positive(self):
        price = bs_call_price(S, K, T, R, SIGMA)
        assert price > 0, "Preço da CALL ATM deve ser positivo"

    def test_put_price_positive(self):
        price = bs_put_price(S, K, T, R, SIGMA)
        assert price > 0, "Preço da PUT ATM deve ser positivo"

    def test_call_higher_than_intrinsic_itm(self):
        """CALL ITM: preço BS >= valor intrínseco."""
        s_itm, k_itm = 110, 100
        price = bs_call_price(s_itm, k_itm, T, R, SIGMA)
        intrinsic = s_itm - k_itm
        assert price >= intrinsic, f"Call ITM price {price} < intrinsic {intrinsic}"

    def test_put_higher_than_intrinsic_itm(self):
        """PUT ITM: preço BS >= valor intrínseco descontado."""
        s_itm, k_itm = 90, 100
        price = bs_put_price(s_itm, k_itm, T, R, SIGMA)
        # Com juros altos, o valor presente do strike é menor
        intrinsic_pv = k_itm * math.exp(-R * T) - s_itm
        assert price >= intrinsic_pv, f"Put ITM price {price} < PV intrinsic {intrinsic_pv}"

    def test_call_at_expiry_itm(self):
        """No vencimento, CALL ITM = S - K."""
        assert bs_call_price(110, 100, 0, R, SIGMA) == pytest.approx(10.0)

    def test_call_at_expiry_otm(self):
        """No vencimento, CALL OTM = 0."""
        assert bs_call_price(90, 100, 0, R, SIGMA) == pytest.approx(0.0)

    def test_put_at_expiry_itm(self):
        """No vencimento, PUT ITM = K - S."""
        assert bs_put_price(90, 100, 0, R, SIGMA) == pytest.approx(10.0)

    def test_put_at_expiry_otm(self):
        """No vencimento, PUT OTM = 0."""
        assert bs_put_price(110, 100, 0, R, SIGMA) == pytest.approx(0.0)

    def test_put_call_parity(self):
        """Paridade Put-Call: C - P = S - K * exp(-rT)."""
        call = bs_call_price(S, K, T, R, SIGMA)
        put = bs_put_price(S, K, T, R, SIGMA)
        parity = S - K * math.exp(-R * T)
        assert call - put == pytest.approx(parity, abs=0.01), \
            f"Put-Call Parity falhou: C-P={call - put:.4f}, S-Ke^-rT={parity:.4f}"

    def test_higher_vol_higher_price(self):
        """Maior vol → maior preço (tanto CALL quanto PUT)."""
        c_lo = bs_call_price(S, K, T, R, 0.20)
        c_hi = bs_call_price(S, K, T, R, 0.50)
        assert c_hi > c_lo, "Preço da CALL deve subir com maior vol"

        p_lo = bs_put_price(S, K, T, R, 0.20)
        p_hi = bs_put_price(S, K, T, R, 0.50)
        assert p_hi > p_lo, "Preço da PUT deve subir com maior vol"

    def test_longer_time_higher_price(self):
        """Mais tempo → maior preço de opção."""
        c_short = bs_call_price(S, K, 10 / 365, R, SIGMA)
        c_long = bs_call_price(S, K, 90 / 365, R, SIGMA)
        assert c_long > c_short


class TestD1D2:
    """Testes para a função auxiliar _d1_d2."""

    def test_atm_d1_positive(self):
        """Para ATM com r > 0, d1 deve ser positivo."""
        d1, d2 = _d1_d2(S, K, T, R, SIGMA)
        assert d1 > 0

    def test_d2_less_than_d1(self):
        """d2 = d1 - sigma * sqrt(T), então d2 < d1."""
        d1, d2 = _d1_d2(S, K, T, R, SIGMA)
        assert d2 < d1

    def test_edge_sigma_zero(self):
        """sigma=0 → retorna (0,0)."""
        d1, d2 = _d1_d2(S, K, T, R, 0)
        assert d1 == 0.0 and d2 == 0.0

    def test_edge_t_zero(self):
        """T=0 → retorna (0,0)."""
        d1, d2 = _d1_d2(S, K, 0, R, SIGMA)
        assert d1 == 0.0 and d2 == 0.0


class TestCalculateGreeks:
    """Testes para calculate_greeks (Delta, Gamma, Theta, Vega, Rho, POP)."""

    def test_call_delta_between_0_and_1(self):
        g = calculate_greeks(S, K, T, SIGMA, "CALL")
        assert 0.0 <= g["delta"] <= 1.0

    def test_put_delta_between_neg1_and_0(self):
        g = calculate_greeks(S, K, T, SIGMA, "PUT")
        assert -1.0 <= g["delta"] <= 0.0

    def test_call_put_delta_relation(self):
        """Delta_call - Delta_put ≈ 1."""
        gc = calculate_greeks(S, K, T, SIGMA, "CALL")
        gp = calculate_greeks(S, K, T, SIGMA, "PUT")
        assert gc["delta"] - gp["delta"] == pytest.approx(1.0, abs=0.01)

    def test_gamma_positive(self):
        """Gamma é sempre positivo para comprador."""
        g = calculate_greeks(S, K, T, SIGMA, "CALL")
        assert g["gamma"] > 0

    def test_gamma_same_for_call_and_put(self):
        """Gamma de CALL e PUT com mesmos parâmetros são iguais."""
        gc = calculate_greeks(S, K, T, SIGMA, "CALL")
        gp = calculate_greeks(S, K, T, SIGMA, "PUT")
        assert gc["gamma"] == pytest.approx(gp["gamma"], abs=1e-6)

    def test_theta_negative_for_buyer(self):
        """Theta é tipicamente negativo para CALL longa."""
        g = calculate_greeks(S, K, T, SIGMA, "CALL")
        assert g["theta"] < 0

    def test_vega_positive(self):
        g = calculate_greeks(S, K, T, SIGMA, "CALL")
        assert g["vega"] > 0

    def test_vega_same_for_call_and_put(self):
        gc = calculate_greeks(S, K, T, SIGMA, "CALL")
        gp = calculate_greeks(S, K, T, SIGMA, "PUT")
        assert gc["vega"] == pytest.approx(gp["vega"], abs=1e-6)

    def test_prob_profit_between_0_and_1(self):
        g = calculate_greeks(S, K, T, SIGMA, "CALL")
        assert 0.0 <= g["prob_profit"] <= 1.0

    def test_edge_expired(self):
        """T=0 → todas as gregas devem ser zero."""
        g = calculate_greeks(S, K, 0, SIGMA, "CALL")
        assert g["delta"] == 0.0
        assert g["gamma"] == 0.0
        assert g["vega"] == 0.0


class TestImpliedVolatility:
    """Testes para a função de IV via Newton-Raphson."""

    def test_iv_converges_to_known_vol(self):
        """Se geramos preço com sigma=0.30, IV deve convergir de volta para ~0.30."""
        price = bs_call_price(S, K, T, R, SIGMA)
        iv = implied_volatility(S, K, T, price, "CALL", R, sigma_init=0.5)
        assert iv == pytest.approx(SIGMA, abs=0.01), \
            f"IV={iv:.4f} deveria convergir para {SIGMA}"

    def test_iv_put(self):
        """IV para PUT também deve convergir."""
        price = bs_put_price(S, K, T, R, SIGMA)
        iv = implied_volatility(S, K, T, price, "PUT", R, sigma_init=0.5)
        assert iv == pytest.approx(SIGMA, abs=0.01)

    def test_iv_edge_zero_price(self):
        """Preço zero → retorna sigma_init."""
        iv = implied_volatility(S, K, T, 0.0, "CALL", R, sigma_init=0.5)
        assert iv == 0.5

    def test_iv_edge_expired(self):
        """T=0 → retorna sigma_init."""
        iv = implied_volatility(S, K, 0, 5.0, "CALL", R, sigma_init=0.5)
        assert iv == 0.5

    def test_iv_higher_price_higher_vol(self):
        """Preço mais alto → IV mais alta."""
        p_lo = bs_call_price(S, K, T, R, 0.20)
        p_hi = bs_call_price(S, K, T, R, 0.60)
        iv_lo = implied_volatility(S, K, T, p_lo, "CALL", R)
        iv_hi = implied_volatility(S, K, T, p_hi, "CALL", R)
        assert iv_hi > iv_lo

"""Testes para resolver_iv — fallback chain de IV implícita (Camada 1.1)."""
import pytest
from backend.domain.options_math import resolver_iv
from backend.domain.greeks import bs_call_price

S, K, T, R, SIGMA = 100.0, 105.0, 30 / 365, 0.135, 0.30


def test_resolver_iv_usa_tela_quando_premio_real_e_valido():
    preco_tela = bs_call_price(S, K, T, R, SIGMA)
    iv, fonte = resolver_iv(preco_tela, S, K, T, "CALL", hv_20d=0.25)
    assert fonte == "tela"
    assert iv == pytest.approx(SIGMA, abs=0.01)


def test_resolver_iv_rejeita_premio_abaixo_do_intrinsico():
    """Prêmio < valor intrínseco é violação de no-arbitrage — cai pro próximo nível."""
    preco_abaixo_intrinsico = 0.01  # CALL ITM (S>K) com prêmio absurdamente baixo
    iv, fonte = resolver_iv(preco_abaixo_intrinsico, S=110, K=100, T=T, tipo="CALL", hv_20d=0.25)
    assert fonte != "tela"


def test_resolver_iv_usa_mediana_dos_vizinhos_sem_preco_de_tela():
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.25,
                            ivs_strikes_vizinhos=[0.28, 0.32, 0.30])
    assert fonte == "strikes_vizinhos"
    assert iv == pytest.approx(0.30)


def test_resolver_iv_ignora_vizinhos_fora_da_faixa_valida():
    """IVs fora de [0.05, 3.0] (erro de cálculo) são descartadas da mediana."""
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.25,
                            ivs_strikes_vizinhos=[0.28, 10.0, 0.32])
    assert fonte == "strikes_vizinhos"
    assert iv == pytest.approx(0.30)  # mediana de [0.28, 0.32], 10.0 descartado


def test_resolver_iv_cai_para_hv_proxy_sem_tela_nem_vizinhos():
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.25)
    assert fonte == "hv_proxy"
    assert iv == pytest.approx(0.25 * 1.1)


def test_resolver_iv_usa_default_sem_nenhum_dado():
    iv, fonte = resolver_iv(None, S, K, T, "CALL", hv_20d=0.0)
    assert fonte == "default"
    assert iv == pytest.approx(0.40)

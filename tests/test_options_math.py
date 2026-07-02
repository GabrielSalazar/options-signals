"""Testes para resolver_iv — fallback chain de IV implícita (Camada 1.1)."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from backend.domain.greeks import bs_call_price, bs_put_price
from backend.domain.options_math import (
    decodificar_opcao_b3,
    estimar_iv_historica,
    estimar_premio_otm,
    mes_vencimento_ideal,
    resolver_iv,
)

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


def test_resolver_iv_put_usa_tela_quando_premio_valido():
    """Branch PUT do cálculo de intrínseco (linha 147)."""
    from backend.domain.greeks import bs_put_price
    preco_tela = bs_put_price(S, K, T, R, SIGMA)
    iv, fonte = resolver_iv(preco_tela, S, K, T, "PUT", hv_20d=0.25)
    assert fonte == "tela"
    assert iv == pytest.approx(SIGMA, abs=0.01)


def test_resolver_iv_sem_preco_tela_t_zero_cai_para_proximo_nivel():
    """T<=0 com preco_tela setado não deve tentar 'tela' (guarda `and T > 0`)."""
    iv, fonte = resolver_iv(5.0, S, K, T=0.0, tipo="CALL", hv_20d=0.25,
                            ivs_strikes_vizinhos=[0.30])
    assert fonte == "strikes_vizinhos"


# ---------------------------------------------------------------------------
# decodificar_opcao_b3
# ---------------------------------------------------------------------------

def test_decodificar_opcao_b3_codigo_curto_retorna_vazio():
    assert decodificar_opcao_b3("PETR") == {}


def test_decodificar_opcao_b3_letra_invalida_retorna_vazio():
    """Letra que não está em MESES_CALL nem MESES_PUT (ex.: 'Z')."""
    assert decodificar_opcao_b3("PETRZ405") == {}


def test_decodificar_opcao_b3_strike_nao_numerico_retorna_vazio():
    assert decodificar_opcao_b3("PETRC40X") == {}


def test_decodificar_opcao_b3_call_strike_grande_acima_10000():
    """strike_raw >= 10000 → strike_raw / 100."""
    decoded = decodificar_opcao_b3("PETRC12345")
    assert decoded["tipo"] == "CALL"
    assert decoded["mes_venc"] == 3
    assert decoded["strike"] == pytest.approx(123.45)


def test_decodificar_opcao_b3_strike_faixa_1000_usa_candidato_quando_maior_igual_2():
    """strike_raw in [1000, 10000), candidato (strike_raw/100) >= 2.0 → usa candidato direto."""
    decoded = decodificar_opcao_b3("PETRC1050")  # 1050/100=10.5 (>=2.0) -> candidato usado
    assert decoded["strike"] == pytest.approx(10.50)
    decoded2 = decodificar_opcao_b3("PETRC1500")  # 1500/100=15.0
    assert decoded2["strike"] == pytest.approx(15.0)


def test_decodificar_opcao_b3_strike_faixa_100_candidato_menor_que_1_divide_mil():
    """strike_raw in [100, 1000), candidato (strike_raw/100) < 1.0 → strike_raw/1000."""
    decoded = decodificar_opcao_b3("PETRC150")  # 150/100=1.5 (>=1.0) -> usa candidato
    assert decoded["strike"] == pytest.approx(1.5)
    decoded2 = decodificar_opcao_b3("PETRC099")  # strike_raw=99 -> cai no else (< 100)
    assert decoded2["strike"] == pytest.approx(9.9)


def test_decodificar_opcao_b3_strike_pequeno_divide_dez():
    """strike_raw < 100 → strike_raw / 10."""
    decoded = decodificar_opcao_b3("PETRC050")
    assert decoded["strike"] == pytest.approx(5.0)


def test_decodificar_opcao_b3_etf_strike_pequeno_divide_dez():
    decoded = decodificar_opcao_b3("BOVAC050")
    assert decoded["acao_base"] == "BOVA"
    assert decoded["strike"] == pytest.approx(5.0)


def test_decodificar_opcao_b3_etf_strike_grande_sem_divisao():
    """ETF com strike_raw >= 100 → usado direto, sem divisão."""
    decoded = decodificar_opcao_b3("BOVAC120")
    assert decoded["strike"] == pytest.approx(120.0)


def test_decodificar_opcao_b3_put_mes_decodificado_corretamente():
    decoded = decodificar_opcao_b3("PETRN405")  # N -> mes 2 (PUT)
    assert decoded["tipo"] == "PUT"
    assert decoded["mes_venc"] == 2


def test_decodificar_opcao_b3_ano_vencimento_proximo_ano_quando_mes_passado():
    """Quando o mês decodificado já passou no ano atual, assume próximo ano."""
    from backend.domain.options_math import MESES_CALL
    hoje = datetime.now(timezone.utc)
    mes_passado = hoje.month - 1 if hoje.month > 1 else 12
    letra = next(l for l, m in MESES_CALL.items() if m == mes_passado)
    decoded = decodificar_opcao_b3(f"PETR{letra}405")
    if mes_passado < hoje.month:
        assert decoded["ano_venc"] == hoje.year + 1
    else:
        assert decoded["ano_venc"] == hoje.year


# ---------------------------------------------------------------------------
# mes_vencimento_ideal / _proximo_vencimento_b3
# ---------------------------------------------------------------------------

def test_mes_vencimento_ideal_retorna_tupla_mes_ano_dte():
    mes, ano, dte = mes_vencimento_ideal()
    assert 1 <= mes <= 12
    assert ano >= datetime.now(timezone.utc).year
    assert dte >= 0


def test_proximo_vencimento_b3_fallback_quando_range_impossivel(monkeypatch):
    """dte_max < dte_min -> nenhuma sexta cabe no range -> fallback 'nenhum' (linha 94)."""
    from backend.domain import options_math as om
    monkeypatch.setitem(om.CONFIG, "dte_minimo", 9999)
    monkeypatch.setitem(om.CONFIG, "dte_maximo", 1)
    mes, ano, dte, tipo = om._proximo_vencimento_b3()
    hoje = datetime.now(timezone.utc).date()
    assert (mes, ano, dte, tipo) == (hoje.month, hoje.year, 0, "nenhum")


# ---------------------------------------------------------------------------
# estimar_iv_historica
# ---------------------------------------------------------------------------

def test_estimar_iv_historica_poucos_dados_retorna_default():
    """len(retornos) < janela → 0.40 (linha 104)."""
    df = pd.DataFrame({"Close": [10.0, 10.1, 10.2]})  # só 2 retornos, janela padrão 20
    assert estimar_iv_historica(df) == 0.40


def test_estimar_iv_historica_calcula_com_dados_suficientes():
    np.random.seed(42)
    precos = 100 * np.exp(np.cumsum(np.random.normal(0, 0.01, 40)))
    df = pd.DataFrame({"Close": precos})
    iv = estimar_iv_historica(df, janela=20)
    assert iv > 0


def test_estimar_iv_historica_intervalo_1h_usa_fator_diferente():
    np.random.seed(7)
    precos = 100 * np.exp(np.cumsum(np.random.normal(0, 0.01, 40)))
    df = pd.DataFrame({"Close": precos})
    iv_1h = estimar_iv_historica(df, janela=20, interval="1h")
    iv_1d = estimar_iv_historica(df, janela=20, interval="1d")
    # fator_anualizacao maior para "1h" (sqrt(252*7) > sqrt(252)) -> iv_1h > iv_1d
    assert iv_1h > iv_1d


# ---------------------------------------------------------------------------
# estimar_premio_otm
# ---------------------------------------------------------------------------

def test_estimar_premio_otm_dte_zero_retorna_fallback_percentual():
    premio = estimar_premio_otm(preco=100.0, strike=110.0, dte_du=0, iv=0.3, tipo="PUT")
    assert premio == max(0.10, round(100.0 * 0.015, 2))


def test_estimar_premio_otm_iv_zero_retorna_fallback_percentual():
    premio = estimar_premio_otm(preco=100.0, strike=110.0, dte_du=10, iv=0.0, tipo="CALL")
    assert premio == max(0.10, round(100.0 * 0.015, 2))


def test_estimar_premio_otm_put_normal():
    premio = estimar_premio_otm(preco=100.0, strike=95.0, dte_du=20, iv=0.3, tipo="PUT")
    assert premio >= 0.10


def test_estimar_premio_otm_call_normal():
    premio = estimar_premio_otm(preco=100.0, strike=105.0, dte_du=20, iv=0.3, tipo="CALL")
    assert premio >= 0.10


def test_estimar_premio_otm_excecao_cai_para_fator_otm(monkeypatch):
    """Força exceção no bloco try (math.log com preco<=0) para exercitar o except (linha 130-132)."""
    premio = estimar_premio_otm(preco=-10.0, strike=95.0, dte_du=20, iv=0.3, tipo="PUT")
    assert premio >= 0.01


# ---------------------------------------------------------------------------
# estimar_premio_otm deve usar a mesma precificação BS (com taxa livre de
# risco/desconto) usada pelos greeks — não uma fórmula sem juros à parte.
# ---------------------------------------------------------------------------

def test_estimar_premio_otm_call_bate_com_bs_call_price_com_selic():
    preco, strike, dte_du, iv = 100.0, 105.0, 20, 0.30
    premio = estimar_premio_otm(preco, strike, dte_du, iv, tipo="CALL")
    esperado = bs_call_price(preco, strike, dte_du / 252, r=0.135, sigma=iv)
    assert premio == pytest.approx(round(esperado, 2), abs=0.01)


def test_estimar_premio_otm_put_bate_com_bs_put_price_com_selic():
    preco, strike, dte_du, iv = 100.0, 95.0, 20, 0.30
    premio = estimar_premio_otm(preco, strike, dte_du, iv, tipo="PUT")
    esperado = bs_put_price(preco, strike, dte_du / 252, r=0.135, sigma=iv)
    assert premio == pytest.approx(round(esperado, 2), abs=0.01)

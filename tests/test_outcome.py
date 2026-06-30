"""Testes do rastreamento de desfecho (abordagem A: reprecificação BS).

avaliar_desfecho recebe o sinal + a série de preços da AÇÃO a partir do dia do
sinal e, reprecificando a opção via Black-Scholes a cada dia, decide se o sinal
bateu alvo (ganho), bateu stop (perda), expirou ou ainda está aberto.
"""
from backend.domain.outcome import (
    avaliar_desfecho,
    comparar_por_desfecho,
    eh_ganho,
    retorno_pct_do_desfecho,
)


def _sinal(**over):
    s = {
        "tipo_sinal": "CALL", "strike_ref": 110.0,
        "premio_est": 1.0, "preco_tela": None,
        "alvo1": 1.25, "alvo2": 3.50, "alvo_final": 8.0, "stop": 0.57,
        "hv_20d": 40.0, "iv_mercado": None, "dte": 20, "preco_acao": 100.0,
    }
    s.update(over)
    return s


# ── avaliar_desfecho ──────────────────────────────────────────────────────────

def test_call_em_alta_ganha():
    # ação sobe forte → prêmio da CALL multiplica → bate alvo
    precos = [100, 104, 108, 113, 118, 122]
    r = avaliar_desfecho(_sinal(), precos)
    assert r["desfecho"] in ("alvo1", "alvo2", "alvo_final")
    assert r["ganhou"] is True


def test_call_em_queda_bate_stop():
    precos = [100, 98, 96, 93, 90, 88]
    r = avaliar_desfecho(_sinal(), precos)
    assert r["desfecho"] == "stop"
    assert r["ganhou"] is False


def test_put_em_queda_ganha():
    # PUT: ação cai → prêmio da PUT sobe → ganho
    precos = [100, 96, 92, 88, 84, 80]
    r = avaliar_desfecho(_sinal(tipo_sinal="PUT", strike_ref=90.0), precos)
    assert r["ganhou"] is True


def test_dados_insuficientes_fica_aberto():
    # janela curta e quase flat: prêmio não cruza stop nem alvo → aberto
    precos = [100, 100, 101]
    r = avaliar_desfecho(_sinal(), precos)
    assert r["desfecho"] == "aberto"
    assert r["ganhou"] is False


def test_desfecho_reporta_dias_ate():
    precos = [100, 102, 106, 112, 120]
    r = avaliar_desfecho(_sinal(), precos)
    assert isinstance(r["dias_ate"], int) and r["dias_ate"] >= 1


# ── comparar_por_desfecho ─────────────────────────────────────────────────────

def test_eh_ganho_helper():
    assert eh_ganho("alvo1") and eh_ganho("alvo_final")
    assert not eh_ganho("stop") and not eh_ganho("aberto") and not eh_ganho("expirou")


def test_comparar_calcula_winrate_e_efeito_do_ponderado():
    # 4 sinais resolvidos: 2 ganhos (ponderado aprovou 1), 2 perdas (ponderado aprovou 0)
    avaliados = [
        {"desfecho": "alvo2", "ponderado_passou": True},
        {"desfecho": "alvo1", "ponderado_passou": False},
        {"desfecho": "stop",  "ponderado_passou": False},
        {"desfecho": "stop",  "ponderado_passou": True},
    ]
    rep = comparar_por_desfecho(avaliados)
    assert rep["resolvidos"] == 4
    assert rep["ganhos"] == 2 and rep["perdas"] == 2
    assert rep["win_rate_classico"] == 50.0
    # entre os aprovados pelo ponderado (1 ganho alvo2 + 1 perda stop) → 50%
    assert rep["win_rate_ponderado"] == 50.0


def test_comparar_ignora_abertos_e_expirados():
    avaliados = [
        {"desfecho": "alvo1", "ponderado_passou": True},
        {"desfecho": "aberto", "ponderado_passou": True},
        {"desfecho": "expirou", "ponderado_passou": False},
    ]
    rep = comparar_por_desfecho(avaliados)
    assert rep["resolvidos"] == 1  # só o alvo1 conta
    assert rep["win_rate_classico"] == 100.0


# ── retorno_pct_do_desfecho ────────────────────────────────────────────────

def test_retorno_pct_do_desfecho_alvo1():
    assert retorno_pct_do_desfecho("alvo1") == 25.0


def test_retorno_pct_do_desfecho_alvo2():
    assert retorno_pct_do_desfecho("alvo2") == 250.0


def test_retorno_pct_do_desfecho_alvo_final():
    assert retorno_pct_do_desfecho("alvo_final") == 700.0


def test_retorno_pct_do_desfecho_stop():
    assert retorno_pct_do_desfecho("stop") == -43.0


def test_retorno_pct_do_desfecho_expirou_retorna_none():
    assert retorno_pct_do_desfecho("expirou") is None


def test_retorno_pct_do_desfecho_aberto_retorna_none():
    assert retorno_pct_do_desfecho("aberto") is None

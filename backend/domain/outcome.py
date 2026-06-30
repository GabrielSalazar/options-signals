"""Rastreamento de desfecho de sinais (abordagem A: reprecificação Black-Scholes).

Não há histórico confiável de preço por opção da B3. Em vez disso, acompanhamos o
preço da AÇÃO (que temos) e reprecificamos a opção via BS a cada dia, escalando o
caminho para começar exatamente no prêmio de entrada do sinal. Comparando o prêmio
reprecificado contra alvos/stop, classificamos o sinal como ganho/perda/aberto.

Isso permite comparar, de forma justa, o score clássico vs. o ponderado (shadow):
dos sinais que deram certo/errado, quantos o ponderado teria aprovado.
"""
from backend.core.config import CONFIG
from backend.domain.greeks import bs_call_price, bs_put_price

_GANHOS = ("alvo1", "alvo2", "alvo_final")


def eh_ganho(desfecho: str) -> bool:
    return desfecho in _GANHOS


def avaliar_desfecho(sinal: dict, precos_acao: list) -> dict:
    """Avalia o desfecho de um sinal dado o caminho de preços da ação.

    `precos_acao`: closes diários começando no dia do sinal (índice 0 = entrada),
    em ordem cronológica. Retorna {desfecho, ganhou, dias_ate} onde desfecho ∈
    {alvo1, alvo2, alvo_final, stop, expirou, aberto, indeterminado}.
    """
    if not precos_acao or len(precos_acao) < 2:
        return {"desfecho": "aberto", "ganhou": False, "dias_ate": 0}

    tipo = (sinal.get("tipo_sinal") or "CALL").upper()
    K = float(sinal["strike_ref"])
    base = float(sinal.get("preco_tela") or sinal["premio_est"])  # prêmio de entrada
    iv_pct = sinal.get("iv_mercado") or sinal.get("hv_20d") or 40.0
    sigma = float(iv_pct) / 100.0
    dte0 = int(sinal["dte"])
    alvo1, alvo2 = float(sinal["alvo1"]), float(sinal["alvo2"])
    alvo_final, stop = float(sinal["alvo_final"]), float(sinal["stop"])

    pricer = bs_call_price if tipo == "CALL" else bs_put_price
    S0 = float(precos_acao[0])
    p0_bs = pricer(S0, K, max(dte0, 1) / 252, sigma=sigma)
    if p0_bs <= 0:
        return {"desfecho": "indeterminado", "ganhou": False, "dias_ate": 0}

    hit_alvo1 = False
    melhor = None
    for i in range(1, len(precos_acao)):
        remaining = dte0 - i
        if remaining <= 0:  # chegou ao vencimento
            return {"desfecho": melhor or "expirou", "ganhou": eh_ganho(melhor or ""), "dias_ate": i}

        premio = base * pricer(float(precos_acao[i]), K, remaining / 252, sigma=sigma) / p0_bs

        if not hit_alvo1:
            if premio <= stop:
                return {"desfecho": "stop", "ganhou": False, "dias_ate": i}
            if premio >= alvo1:
                hit_alvo1 = True
                melhor = "alvo1"
        if hit_alvo1:
            if premio >= alvo_final:
                melhor = "alvo_final"
            elif premio >= alvo2 and melhor != "alvo_final":
                melhor = "alvo2"

    # acabaram os dados antes do vencimento
    if melhor:
        return {"desfecho": melhor, "ganhou": True, "dias_ate": len(precos_acao) - 1}
    return {"desfecho": "aberto", "ganhou": False, "dias_ate": len(precos_acao) - 1}


def comparar_por_desfecho(avaliados: list) -> dict:
    """Compara clássico vs. ponderado sobre sinais já avaliados.

    `avaliados`: lista de dicts com pelo menos {desfecho, ponderado_passou}.
    Considera apenas sinais RESOLVIDOS (ganho ou stop); ignora aberto/expirou.
    Retorna win-rates e o efeito de filtrar pelo ponderado.
    """
    resolvidos = [a for a in avaliados if a["desfecho"] in _GANHOS or a["desfecho"] == "stop"]
    ganhos = [a for a in resolvidos if a["desfecho"] in _GANHOS]
    perdas = [a for a in resolvidos if a["desfecho"] == "stop"]
    n = len(resolvidos)

    aprovados = [a for a in resolvidos if a.get("ponderado_passou")]
    aprov_ganhos = [a for a in aprovados if a["desfecho"] in _GANHOS]

    def pct(num, den):
        return round(num / den * 100, 1) if den else 0.0

    return {
        "resolvidos": n,
        "ganhos": len(ganhos),
        "perdas": len(perdas),
        "win_rate_classico": pct(len(ganhos), n),
        "aprovados_ponderado": len(aprovados),
        "win_rate_ponderado": pct(len(aprov_ganhos), len(aprovados)),
        # perdedores que o ponderado teria barrado (acerto do ponderado)
        "perdas_barradas_ponderado": len([a for a in perdas if not a.get("ponderado_passou")]),
        # vencedores que o ponderado teria barrado (custo do ponderado)
        "ganhos_barrados_ponderado": len([a for a in ganhos if not a.get("ponderado_passou")]),
    }


_RETORNO_PCT_POR_DESFECHO = {
    "alvo1": "alvo1_pct", "alvo2": "alvo2_pct",
    "alvo_final": "alvo_final_pct", "stop": "stop_pct",
}


def retorno_pct_do_desfecho(desfecho: str) -> float | None:
    """Retorno percentual nominal associado ao desfecho (Camada 2.4 —
    telemetria por gatilho). Usa os percentuais de CONFIG que definem
    alvos/stop (mesma fonte que gera os valores absolutos do sinal), não o
    caminho de preço real — é uma categorização, não uma medição exata do
    retorno realizado. `expirou`/`aberto`/`indeterminado` não têm percentual
    associado de forma confiável -> None."""
    campo = _RETORNO_PCT_POR_DESFECHO.get(desfecho)
    if campo is None:
        return None
    return round(CONFIG[campo] * 100, 1)

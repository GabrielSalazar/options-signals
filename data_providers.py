import requests
import logging
from typing import Dict, List, Optional
from cache import cache_get, cache_set

logger = logging.getLogger("b3_scanner")

_OPCOES_NET_BASE = "https://opcoes.net.br/listaopcoes/completa"


def _fetch_chain(ticker: str) -> List[list]:
    """
    Busca a chain bruta de opções para um ticker. Cache de 3 min.
    Retorna lista vazia se a API falhar — chamadores devem tratar.
    """
    cache_key = f"opcoes_chain:{ticker}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    try:
        url = f"{_OPCOES_NET_BASE}?idAcao={ticker}&listarVencimentos=true&cotacoes=true"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("success") != "data":
            cache_set(cache_key, [], ttl=180)
            return []
        chain = data.get("data", {}).get("cotacoesOpcoes", []) or []
        cache_set(cache_key, chain, ttl=180)
        return chain
    except Exception as e:
        logger.warning(f"Erro ao buscar chain de {ticker}: {e}")
        cache_set(cache_key, [], ttl=60)  # cache curto em caso de erro
        return []

def get_real_options_from_opcoes_net(ticker: str, tipo_alvo: str, strike_alvo: float) -> Optional[Dict]:
    """
    Busca a opção real mais próxima de strike_alvo do tipo CALL ou PUT.
    Usado pelo core_engine para validar o strike teórico contra a grade da B3.
    """
    cache_key = f"opcao_strike:{ticker}:{tipo_alvo}:{strike_alvo:.2f}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached if cached else None

    chain = _fetch_chain(ticker)
    result = None
    menor_distancia = float("inf")

    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]

        if op_tipo != tipo_alvo:
            continue
        if op_negocios is None or op_preco is None or op_preco <= 0.01:
            continue

        distancia = abs(op_strike - strike_alvo)
        if distancia < menor_distancia:
            menor_distancia = distancia
            result = {
                "ticker_opcao": op_ticker,
                "strike_real":  op_strike,
                "preco_tela":   op_preco,
                "num_negocios": op_negocios,
            }

    cache_set(cache_key, result if result else {}, ttl=180)
    return result


def get_liquid_options_for_ticker(ticker: str, limit: int = 2) -> List[Dict]:
    """
    Retorna até `limit` opções mais líquidas (por número de negócios) para um ticker.
    Mistura CALLs e PUTs. Usado pelo endpoint /market/opcoes.
    """
    chain = _fetch_chain(ticker)
    candidatos: List[Dict] = []

    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]

        if op_tipo not in ("CALL", "PUT"):
            continue
        if op_negocios is None or op_negocios <= 0:
            continue
        if op_preco is None or op_preco <= 0.01:
            continue

        candidatos.append({
            "ticker_opcao":      op_ticker,
            "ticker_subjacente": ticker,
            "tipo":              op_tipo,
            "strike":            float(op_strike),
            "preco":             float(op_preco),
            "negocios":          int(op_negocios),
        })

    candidatos.sort(key=lambda x: x["negocios"], reverse=True)
    return candidatos[:limit]

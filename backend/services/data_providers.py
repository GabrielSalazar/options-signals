import base64
import json
import logging
import os
import time
from typing import Dict, List, Optional

import yfinance as yf

from backend.core.cache import cache_get, cache_set
from backend.domain.options_math import decodificar_opcao_b3
from backend.services.http_client import get_with_retry

logger = logging.getLogger("b3_scanner")

_OPCOES_NET_BASE = "https://opcoes.net.br/listaopcoes/completa"
_BRAPI_BASE = "https://brapi.dev/api"


def fetch_brapi_historical(ticker: str, range_: str = "6mo", interval: str = "1d"):
    """
    Fallback de histórico OHLCV via brapi quando yfinance falha.
    Retorna pandas.DataFrame ou DataFrame vazio.
    """
    import pandas as pd
    ticker_clean = ticker.replace(".SA", "")
    cache_key = f"brapi_hist:{ticker_clean}:{range_}:{interval}"
    cached = cache_get(cache_key)
    if cached is not None:
        try:
            return pd.DataFrame(cached) if cached else pd.DataFrame()
        except Exception:
            pass

    token = os.getenv("BRAPI_TOKEN", "")
    params = {"range": range_, "interval": interval, "fundamental": "false"}
    if token:
        params["token"] = token
    try:
        r = get_with_retry(f"{_BRAPI_BASE}/quote/{ticker_clean}", params=params, timeout=15)
        results = r.json().get("results", [])
        if not results or "historicalDataPrice" not in results[0]:
            return pd.DataFrame()
        df = pd.DataFrame(results[0]["historicalDataPrice"])
        df["date"] = pd.to_datetime(df["date"], unit="s")
        df = (df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                 "close": "Close", "volume": "Volume"})
                .set_index("date").sort_index()
                [["Open", "High", "Low", "Close", "Volume"]].dropna())
        cache_set(cache_key, df.reset_index().to_dict(orient="records"), ttl=300)
        return df
    except Exception as e:
        logger.debug(f"brapi histórico falhou para {ticker}: {e}")
        return pd.DataFrame()


def fetch_all_b3_tickers() -> List[str]:
    """
    Retorna todos os tickers de ações/ETFs disponíveis na B3 via brapi /available.
    Filtra apenas papéis "normais" (4-6 chars terminando em dígito) para reduzir ruído.
    Cache de 24h (lista muda raramente).
    """
    cached = cache_get("b3_all_tickers")
    if cached:
        return cached
    token = os.getenv("BRAPI_TOKEN", "")
    params = {"token": token} if token else {}
    try:
        r = get_with_retry(f"{_BRAPI_BASE}/available", params=params, timeout=15)
        stocks = r.json().get("stocks", [])
        tickers = [s for s in stocks if 5 <= len(s) <= 6 and s[-1].isdigit()]
        cache_set("b3_all_tickers", tickers, ttl=86400)
        logger.info(f"brapi /available: {len(tickers)} tickers da B3 carregados")
        return tickers
    except Exception as e:
        logger.warning(f"Erro ao buscar /available da brapi: {e}")
        return []


_B3_LISTED_BASE = ("https://sistemaswebb3-listados.b3.com.br/listedCompaniesProxy"
                   "/CompanyCall/GetInitialCompanies")
_B3_SUFIXOS = ("3", "4", "11")
_B3_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
}


def _b3_page_url(page_number: int, page_size: int = 120) -> str:
    payload = {"language": "pt-br", "pageNumber": page_number, "pageSize": page_size}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return f"{_B3_LISTED_BASE}/{encoded}"


def fetch_b3_official_tickers() -> Dict[str, str]:
    """
    Colhe raízes de empresas + nomes via API oficial da B3 e expande cada raiz
    de 4 letras nos sufixos negociáveis (3, 4, 11). Retorna {ticker_base: nome}.
    Cache 24h. Qualquer falha → {} (degradação graciosa). O ruído (tickers que
    não negociam) é removido depois pelo filtro de volume.
    """
    cached = cache_get("b3_official_tickers")
    if cached is not None:
        return cached

    resultado: Dict[str, str] = {}
    try:
        page, total_pages = 1, 1
        while page <= total_pages:
            r = get_with_retry(_b3_page_url(page), headers=_B3_HEADERS, timeout=15)
            data = r.json()
            total_pages = data.get("page", {}).get("totalPages", 1) or 1
            for emp in data.get("results", []):
                raiz = (emp.get("issuingCompany") or "").strip().upper()
                nome = (emp.get("tradingName") or emp.get("companyName") or raiz).strip()
                if len(raiz) == 4 and raiz.isalpha():
                    for suf in _B3_SUFIXOS:
                        resultado.setdefault(f"{raiz}{suf}", nome)
            page += 1
            if page <= total_pages:
                time.sleep(0.3)
        cache_set("b3_official_tickers", resultado, ttl=86400)
        logger.info(f"B3 oficial: {len(resultado)} candidatos em {total_pages} página(s)")
        return resultado
    except Exception as e:
        logger.warning(f"Erro ao buscar API oficial da B3: {e}")
        return {}


def _volume_financeiro(data, ticker: str, single: bool) -> Optional[float]:
    """Volume financeiro médio diário (Close*Volume) de um ticker no df do yfinance.
    Lida com df single-index (1 ticker) e MultiIndex (vários)."""
    try:
        if single:
            sub = data
        else:
            if ticker not in data.columns.get_level_values(0):
                return None
            sub = data[ticker]
        close = sub["Close"].dropna()
        volume = sub["Volume"].dropna()
        if close.empty or volume.empty:
            return None
        fin = (close * volume).dropna()
        if fin.empty:
            return None
        return float(fin.mean())
    except Exception:
        return None


def filtrar_por_volume(
    tickers: List[str],
    min_volume_rs: float,
    batch_size: int = 20,
    delay_s: float = 1.0,
    period: str = "10d",
) -> Dict[str, float]:
    """
    Baixa OHLCV de `period` via yfinance em lotes e retorna
    {ticker: volume_financeiro_medio_rs} apenas para os que atingem min_volume_rs.
    Tickers sem dados são ignorados; erro num lote → loga e pula. Delay entre lotes.
    """
    aprovados: Dict[str, float] = {}
    if not tickers:
        return aprovados

    for i in range(0, len(tickers), batch_size):
        lote = tickers[i:i + batch_size]
        try:
            data = yf.download(
                lote, period=period, interval="1d", auto_adjust=True,
                progress=False, group_by="ticker", threads=True,
            )
        except Exception as e:
            logger.warning(f"filtrar_por_volume: lote {i // batch_size} falhou: {e}")
            continue

        single = len(lote) == 1
        for t in lote:
            vol_rs = _volume_financeiro(data, t, single)
            if vol_rs is not None and vol_rs >= min_volume_rs:
                aprovados[t] = vol_rs

        if i + batch_size < len(tickers):
            time.sleep(delay_s)

    logger.info(f"filtro de volume: {len(aprovados)}/{len(tickers)} ≥ R${min_volume_rs:,.0f}")
    return aprovados


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
        response = get_with_retry(url, timeout=10)
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

    from backend.core.config import CONFIG
    min_neg = CONFIG.get("min_negocios_opcao", 0)

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
        if op_negocios < min_neg:
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


def obter_opcoes_vizinhas(ticker: str, tipo_alvo: str, strike_alvo: float,
                           mes_v: int, ano_v: int, excluir_strike: float,
                           n: int = 4) -> List[Dict]:
    """
    Busca até `n` opções líquidas do mesmo tipo e vencimento, mais próximas de
    strike_alvo (excluindo o próprio strike). Usado no fallback chain de IV
    (Camada 1.1) quando não há prêmio de tela para o strike de referência.
    """
    from backend.core.config import CONFIG
    min_neg = CONFIG.get("min_negocios_opcao", 0)

    chain = _fetch_chain(ticker)
    candidatos = []

    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]

        if op_tipo != tipo_alvo:
            continue
        if op_negocios is None or op_preco is None or op_preco <= 0.01:
            continue
        if op_negocios < min_neg:
            continue
        if abs(op_strike - excluir_strike) < 0.001:
            continue

        decoded = decodificar_opcao_b3(op_ticker)
        if not decoded or decoded.get("mes_venc") != mes_v or decoded.get("ano_venc") != ano_v:
            continue

        candidatos.append({
            "ticker_opcao": op_ticker,
            "strike_real":  op_strike,
            "preco_tela":   op_preco,
        })

    candidatos.sort(key=lambda c: abs(c["strike_real"] - strike_alvo))
    return candidatos[:n]


def obter_opcao_atm(ticker: str, preco_spot: float, mes_v: int, ano_v: int,
                     tipo_alvo: str = "CALL") -> Optional[Dict]:
    """
    Busca a opção líquida mais próxima do spot (ATM) do tipo/vencimento dados.
    Usado pelo job diário de histórico de IV (Camada 1.2).
    """
    from backend.core.config import CONFIG
    min_neg = CONFIG.get("min_negocios_opcao", 0)

    chain = _fetch_chain(ticker)
    melhor = None
    menor_distancia = float("inf")

    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]

        if op_tipo != tipo_alvo:
            continue
        if op_negocios is None or op_preco is None or op_preco <= 0.01:
            continue
        if op_negocios < min_neg:
            continue

        decoded = decodificar_opcao_b3(op_ticker)
        if not decoded or decoded.get("mes_venc") != mes_v or decoded.get("ano_venc") != ano_v:
            continue

        distancia = abs(op_strike - preco_spot)
        if distancia < menor_distancia:
            menor_distancia = distancia
            melhor = {"ticker_opcao": op_ticker, "strike_real": op_strike, "preco_tela": op_preco}

    return melhor


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

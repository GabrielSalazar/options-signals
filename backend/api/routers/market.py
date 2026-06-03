"""Endpoints de dados de mercado: cotações de índices/ações e opções líquidas."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("b3_api")
router = APIRouter(prefix="/market", tags=["Market"])


@router.get("")
def get_market():
    import yfinance as yf

    INDICES = [("IBOV", "^BVSP")]
    ACOES = [
        ("PETR4", "PETR4.SA"), ("VALE3", "VALE3.SA"), ("ITUB4", "ITUB4.SA"),
        ("WEGE3", "WEGE3.SA"), ("ABEV3", "ABEV3.SA"), ("BBAS3", "BBAS3.SA"),
        ("MGLU3", "MGLU3.SA"), ("RENT3", "RENT3.SA"),
    ]

    all_yf = [yf_t for _, yf_t in INDICES + ACOES]

    try:
        df = yf.download(all_yf, period="5d", interval="1d", progress=False,
                         auto_adjust=True, group_by="ticker", timeout=20)

        def get_quote(yf_ticker: str):
            try:
                if len(all_yf) == 1:
                    close = df["Close"].dropna()
                else:
                    close = df[yf_ticker]["Close"].dropna()
                if len(close) < 2:
                    return None
                price = float(close.iloc[-1])
                prev = float(close.iloc[-2])
                chg_pct = (price - prev) / prev * 100
                return {"price": round(price, 2), "chg_pct": round(chg_pct, 2)}
            except Exception:
                return None

        result: dict = {"indices": [], "acoes": []}
        for label, yf_t in INDICES:
            q = get_quote(yf_t)
            if q:
                result["indices"].append({"ticker": label, **q})
        for label, yf_t in ACOES:
            q = get_quote(yf_t)
            if q:
                result["acoes"].append({"ticker": label, **q})

        return result
    except Exception as e:
        logger.error(f"Erro ao buscar market data: {e}")
        raise HTTPException(status_code=503, detail="Dados de mercado indisponíveis")


@router.get("/opcoes")
def get_market_options():
    """
    Retorna lista de opções reais mais líquidas dos principais tickers da B3,
    consumida pela tab Opções do MarketWidget no frontend.

    Dados vêm de opcoes.net.br com cache de 3 min por ticker.
    Todos os tickers são consultados em paralelo (ThreadPoolExecutor).
    Em caso de erro total, retorna lista vazia (frontend usa fallback).
    """
    from backend.services.data_providers import get_liquid_options_for_ticker

    TICKERS_HOT = ["PETR4", "VALE3", "ITUB4", "MGLU3", "WEGE3", "BBAS3"]

    todas: list[dict] = []

    def fetch_opts(ticker: str) -> list[dict]:
        try:
            return get_liquid_options_for_ticker(ticker, limit=2)
        except Exception as e:
            logger.warning(f"Erro ao buscar opções de {ticker}: {e}")
            return []

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_opts, t): t for t in TICKERS_HOT}
        for future in as_completed(futures):
            todas.extend(future.result())

    # Ordenar globalmente por liquidez, top 6
    todas.sort(key=lambda x: x["negocios"], reverse=True)
    return {"opcoes": todas[:6]}


@router.get("/opcoes/chain/{ticker}")
def get_options_chain(ticker: str):
    """Retorna a cadeia completa de opções em tempo real para o ticker."""
    from backend.services.data_providers import _fetch_chain
    chain = _fetch_chain(ticker)
    opcoes = []
    for op in chain:
        if len(op) < 10:
            continue
        op_ticker, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]
        opcoes.append({
            "ticker": op_ticker,
            "tipo": op_tipo,
            "strike": float(op_strike) if op_strike else 0.0,
            "preco": float(op_preco) if op_preco else 0.0,
            "negocios": int(op_negocios) if op_negocios else 0
        })
    return {"chain": opcoes}

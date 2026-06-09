"""Endpoints de dados de mercado: cotações de índices/ações e opções líquidas."""
import logging
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, HTTPException

from backend.services.data_providers import fetch_brapi_historical, _fetch_chain
from backend.domain.options_math import estimar_iv_historica
from backend.domain.indicators import _rsi_manual, _stoch_manual, _adx_manual

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


def _fetch_historical_with_fallback(ticker: str) -> "pd.DataFrame":
    """Tenta brapi → yfinance → Yahoo Finance HTTP direto."""
    import time
    import yfinance as yf
    import backend.services.data_providers as dp

    df = dp.fetch_brapi_historical(ticker, "6mo")
    if df is not None and not df.empty:
        return df

    yf_ticker = ticker if ticker.endswith(".SA") else f"{ticker}.SA"

    # Fallback 1: yfinance
    try:
        df_yf = yf.download(yf_ticker, period="6mo", interval="1d",
                            progress=False, auto_adjust=True)
        if df_yf is not None and not df_yf.empty:
            df_yf.index.name = "date"
            if isinstance(df_yf.columns, pd.MultiIndex):
                df_yf.columns = df_yf.columns.get_level_values(0)
            return df_yf[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception as e:
        logger.warning(f"yfinance fallback falhou para {ticker}: {e}")

    # Fallback 2: Yahoo Finance Chart API via HTTP direto
    try:
        import requests as _req
        now = int(time.time())
        period1 = now - 180 * 86400
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}"
        r = _req.get(url, params={"period1": period1, "period2": now, "interval": "1d"},
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        result = r.json().get("chart", {}).get("result", [])
        if result:
            ts = result[0]["timestamp"]
            q = result[0]["indicators"]["quote"][0]
            adj = result[0]["indicators"].get("adjclose", [{}])[0].get("adjclose", q["close"])
            df_http = pd.DataFrame({
                "Open": q["open"], "High": q["high"], "Low": q["low"],
                "Close": adj, "Volume": q["volume"],
            }, index=pd.to_datetime(ts, unit="s"))
            df_http.index.name = "date"
            return df_http.dropna()
    except Exception as e:
        logger.warning(f"Yahoo Finance HTTP fallback falhou para {ticker}: {e}")

    return pd.DataFrame()


@router.get("/analysis/{ticker}")
def get_market_analysis(ticker: str):
    """
    Retorna análise completa do ativo: indicadores técnicos calculados sobre
    histórico de 6 meses + chain de opções.
    Contrato de resposta: AssetAnalysisPayload (ver docs/superpowers/specs).
    """
    import backend.api.routers.market as _self

    # --- Dados históricos (brapi com fallback yfinance) ---
    df = _fetch_historical_with_fallback(ticker)

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' não encontrado ou sem dados históricos.")

    if len(df) < 60:
        raise HTTPException(
            status_code=422,
            detail=f"Dados insuficientes para '{ticker}': {len(df)} pregões disponíveis, mínimo 60."
        )

    close = df["Close"]

    # --- Preço atual ---
    preco_atual = float(close.iloc[-1])

    # --- Volatilidade histórica ---
    hv_20 = _self.estimar_iv_historica(df, janela=20)
    hv_60 = _self.estimar_iv_historica(df, janela=60)

    # --- Médias móveis simples ---
    def _sma(series: pd.Series, window: int) -> float:
        if len(series) >= window:
            return float(series.rolling(window).mean().iloc[-1])
        return float(series.mean())

    ma20 = _sma(close, 20)
    ma50 = _sma(close, 50)
    ma200 = _sma(close, 200) if len(close) >= 200 else _sma(close, len(close))

    # --- σ₂₀: desvio padrão dos log-retornos × √252 (janela 20 dias) ---
    log_returns = np.log(close / close.shift(1)).dropna()
    sigma_20 = float(log_returns.tail(20).std() * np.sqrt(252)) if len(log_returns) >= 20 else hv_20

    # --- RSI₁₄ ---
    rsi14 = float(_self._rsi_manual(close, period=14).iloc[-1])
    if np.isnan(rsi14):
        rsi14 = 50.0

    # --- Bollinger %B (20 períodos, 2σ) ---
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std
    bb_range = (bb_upper - bb_lower).iloc[-1]
    if bb_range and not np.isnan(bb_range) and bb_range > 0:
        bollinger_pct_b = float((preco_atual - float(bb_lower.iloc[-1])) / bb_range)
    else:
        bollinger_pct_b = 0.5

    # --- Z-Score vs MA20 ---
    z_score_20 = float((preco_atual - ma20) / (sigma_20 + 1e-9)) if sigma_20 > 0 else 0.0

    # --- Faixa 52 semanas (252 pregões) ---
    ultimos_252 = close.tail(252)
    faixa_52s_min = float(ultimos_252.min())
    faixa_52s_max = float(ultimos_252.max())

    # --- MACD (12/26/9) ---
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_diff_val = float((macd_line - macd_signal_line).iloc[-1])
    if np.isnan(macd_diff_val):
        macd_diff_val = 0.0

    # --- Stochastic K/D (14/3) ---
    stoch_k_series = _stoch_manual(df["High"], df["Low"], close, k=14)
    stoch_d_series = stoch_k_series.rolling(3).mean()
    stoch_k_val = float(stoch_k_series.iloc[-1])
    stoch_d_val = float(stoch_d_series.iloc[-1])
    if np.isnan(stoch_k_val): stoch_k_val = 50.0
    if np.isnan(stoch_d_val): stoch_d_val = 50.0

    # --- ADX (14) ---
    adx_val = float(_adx_manual(df["High"], df["Low"], close, period=14).iloc[-1])
    if np.isnan(adx_val): adx_val = 0.0

    # --- Fundamentalistas: Graham e DCF ---
    preco_graham: float | None = None
    preco_dcf: float | None = None
    try:
        import math
        import yfinance as yf
        yf_ticker_str = ticker if ticker.upper().endswith(".SA") else f"{ticker.upper()}.SA"
        info = yf.Ticker(yf_ticker_str).info
        lpa = info.get("trailingEps") or info.get("forwardEps")
        vpa = info.get("bookValue")
        fcl_total = info.get("freeCashflow")
        shares = info.get("sharesOutstanding")
        if lpa and lpa > 0 and vpa and vpa > 0:
            preco_graham = round(math.sqrt(22.5 * lpa * vpa), 2)
        if fcl_total and fcl_total > 0 and shares and shares > 0:
            fcl_por_acao = fcl_total / shares
            preco_dcf = round(fcl_por_acao / (0.15 - 0.04), 2)
    except Exception as e:
        logger.warning(f"Fundamentalistas de {ticker} falharam: {e}")

    # --- Chain de opções (falha silenciosa) ---
    chain_items = []
    try:
        raw_chain = _self._fetch_chain(ticker)
        for op in raw_chain:
            if len(op) < 10:
                continue
            _, _, op_tipo, _, _, op_strike, _, _, op_preco, op_negocios = op[:10]
            if op_tipo not in ("CALL", "PUT"):
                continue
            chain_items.append({
                "strike": float(op_strike) if op_strike else 0.0,
                "preco": float(op_preco) if op_preco else 0.0,
                "tipo": op_tipo.lower(),
                "negocios": int(op_negocios) if op_negocios else 0,
            })
    except Exception as e:
        logger.warning(f"Chain de {ticker} falhou silenciosamente: {e}")
        chain_items = []

    return {
        "ticker": ticker.upper(),
        "preco_atual": round(preco_atual, 4),
        "hv_20": round(hv_20, 6),
        "hv_60": round(hv_60, 6),
        "ma20": round(ma20, 4),
        "ma50": round(ma50, 4),
        "ma200": round(ma200, 4),
        "sigma_20": round(sigma_20, 6),
        "rsi14": round(rsi14, 2),
        "bollinger_pct_b": round(bollinger_pct_b, 6),
        "z_score_20": round(z_score_20, 6),
        "faixa_52s_min": round(faixa_52s_min, 4),
        "faixa_52s_max": round(faixa_52s_max, 4),
        "macd_diff": round(macd_diff_val, 4),
        "stoch_k": round(stoch_k_val, 2),
        "stoch_d": round(stoch_d_val, 2),
        "adx": round(adx_val, 2),
        "preco_graham": preco_graham,
        "preco_dcf": preco_dcf,
        "chain": chain_items,
    }

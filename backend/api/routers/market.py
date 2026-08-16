"""Endpoints de dados de mercado: cotações de índices/ações e opções líquidas."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.core.constants import RSI_NEUTRAL_DEFAULT, STOCH_NEUTRAL_DEFAULT, EMA_SLOW_PERIOD
from backend.domain.analytics import compute_statistical_indicators
from backend.domain.greeks import implied_volatility
from backend.domain.indicators import (  # noqa: F401
    _adx_manual,
    _rsi_manual,  # usado via _self._rsi_manual em tests/test_market_analysis.py
    _stoch_manual,
    calcular_indicadores,
)
from backend.domain.options_math import (  # noqa: F401
    estimar_iv_historica,  # usado via _self.estimar_iv_historica / monkeypatch em tests/test_market_analysis.py
    mes_vencimento_ideal,
)
from backend.domain.setups import detectar_setups
from backend.services.data_providers import (  # noqa: F401
    _fetch_chain,
    fetch_brapi_historical,  # usado via mock.patch em tests/test_market_analysis.py
)

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
    # Reimport local (não redundante): permite que
    # mock.patch("backend.services.data_providers._fetch_chain", ...) nos
    # testes substitua a referência usada aqui em tempo de chamada.
    from backend.services.data_providers import _fetch_chain  # noqa: F811

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

    df = fetch_brapi_historical(ticker, "6mo")
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

    # --- Médias móveis, volatilidade e Bollinger via helper ---
    stats = compute_statistical_indicators(df)
    ma20 = stats["ma20"]
    ma50 = stats["ma50"]
    ma200 = stats["ma200"]
    sigma_20 = stats["sigma_20"]
    bollinger_pct_b = stats["bb_pct_b"]
    z_score_20 = stats["z_score_20"]

    # --- RSI₁₄ ---
    rsi14 = float(_self._rsi_manual(close, period=14).iloc[-1])
    if np.isnan(rsi14):
        rsi14 = RSI_NEUTRAL_DEFAULT

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
    if np.isnan(stoch_k_val): stoch_k_val = STOCH_NEUTRAL_DEFAULT
    if np.isnan(stoch_d_val): stoch_d_val = STOCH_NEUTRAL_DEFAULT

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
        t = yf.Ticker(yf_ticker_str)
        info = t.info or {}

        # LPA: tenta info primeiro, depois calcula via DRE
        lpa: float | None = info.get("trailingEps") or info.get("forwardEps")
        if not lpa:
            try:
                inc = t.income_stmt
                if inc is not None and not inc.empty:
                    lucro_col = next((c for c in inc.index if "Net Income" in str(c)), None)
                    lucro = float(inc.loc[lucro_col].iloc[0]) if lucro_col else None
                    shares_info = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                    if lucro and shares_info:
                        lpa = lucro / shares_info
            except Exception:
                pass

        # VPA: tenta info primeiro, depois calcula via balanço
        vpa: float | None = info.get("bookValue")
        if not vpa:
            try:
                bal = t.balance_sheet
                if bal is not None and not bal.empty:
                    equity_col = next((c for c in bal.index if "Stockholders" in str(c) or "Equity" in str(c)), None)
                    equity = float(bal.loc[equity_col].iloc[0]) if equity_col else None
                    shares_info = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                    if equity and shares_info:
                        vpa = equity / shares_info
            except Exception:
                pass

        # FCL: tenta info primeiro, depois calcula via fluxo de caixa
        fcl_total: float | None = info.get("freeCashflow")
        shares_out: float | None = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
        if not fcl_total:
            try:
                cf = t.cash_flow
                if cf is not None and not cf.empty:
                    op_col = next((c for c in cf.index if "Operating" in str(c) and "Cash" in str(c)), None)
                    cap_col = next((c for c in cf.index if "Capital" in str(c) and "Expenditure" in str(c)), None)
                    if op_col and cap_col:
                        fcl_total = float(cf.loc[op_col].iloc[0]) + float(cf.loc[cap_col].iloc[0])
                    elif op_col:
                        fcl_total = float(cf.loc[op_col].iloc[0])
            except Exception:
                pass

        if lpa and lpa > 0 and vpa and vpa > 0:
            preco_graham = round(math.sqrt(22.5 * lpa * vpa), 2)
        if fcl_total and fcl_total > 0 and shares_out and shares_out > 0:
            fcl_por_acao = fcl_total / shares_out
            preco_dcf = round(fcl_por_acao / (0.15 - 0.04), 2)
        logger.info(f"Fundamentalistas {ticker}: LPA={lpa}, VPA={vpa}, FCL={fcl_total}, shares={shares_out} → Graham={preco_graham}, DCF={preco_dcf}")
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


@router.get("/indicators/{ticker}")
def get_market_indicators(ticker: str):
    """Indicadores técnicos + setups de price action + leitura de vol para a
    sub-página 'Indicadores e Setup'. Contrato: IndicatorsPayload (ver spec)."""
    import math

    import backend.api.routers.market as _self

    df = _self._fetch_historical_with_fallback(ticker)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' não encontrado.")
    if len(df) < 60:
        raise HTTPException(status_code=422, detail=f"Dados insuficientes para '{ticker}'.")

    ind = calcular_indicadores(df)
    close = ind["Close"]
    preco_atual = float(close.iloc[-1])

    def _last(col: str, default: float = 0.0) -> float:
        if col in ind.columns:
            v = float(ind[col].iloc[-1])
            return v if not math.isnan(v) else default
        return default

    # --- Médias móveis, volatilidade e Bollinger via helper ---
    stats = compute_statistical_indicators(df)
    ma20 = stats["ma20"]
    ma50 = stats["ma50"]
    ma200 = stats["ma200"]
    sigma_20 = stats["sigma_20"]
    bollinger_pct_b = stats["bb_pct_b"]
    z_score_20 = stats["z_score_20"]

    hv_20 = _self.estimar_iv_historica(df, janela=20)
    hv_60 = _self.estimar_iv_historica(df, janela=60)

    # VWAP: track availability separately
    vwap = _last("vwap")  # Returns 0.0 (default) if 'vwap' not in columns
    vwap_available = "vwap" in ind.columns and not math.isnan(float(ind["vwap"].iloc[-1]))
    if not vwap_available:
        vwap = preco_atual  # Fallback for display purposes
    vwap_dist_pct = (preco_atual - vwap) / vwap * 100 if vwap else 0.0

    ult252 = close.tail(252)
    faixa_min, faixa_max = float(ult252.min()), float(ult252.max())

    # --- Expected move (base HV) e DTE do próximo vencimento ---
    try:
        _, _, dte = mes_vencimento_ideal()  # dte em dias úteis
        if not dte or dte <= 0:
            dte = EMA_SLOW_PERIOD  # Fallback: ~1 mês de dias úteis
    except Exception:
        dte = EMA_SLOW_PERIOD  # Fallback: ~1 mês de dias úteis
    em = preco_atual * sigma_20 * math.sqrt(max(dte, 1) / 252)
    faixa_1sigma = [round(preco_atual - em, 2), round(preco_atual + em, 2)]

    # --- IV ATM via chain (degrada para null) ---
    iv_atm = None
    iv_hv_ratio = None
    vol_read = "indisponivel"
    try:
        chain = _self._fetch_chain(ticker)
        atm = _atm_iv_from_chain(chain, preco_atual, dte)
        if atm is not None:
            iv_atm = round(atm, 4)
            iv_hv_ratio = round(iv_atm / hv_20, 2) if hv_20 > 0 else None
    except Exception:
        iv_atm = None
    if iv_atm is not None and hv_20 > 0:
        ratio = iv_atm / hv_20
        vol_read = "premio_gordo" if ratio > 1.2 else "premio_barato" if ratio < 0.9 else "neutro"

    setups = [
        {"nome": s.nome, "status": s.status, "vies": s.vies, "descricao": s.descricao}
        for s in detectar_setups(ind)
    ]

    return {
        "ticker": ticker.upper(),
        "preco_atual": round(preco_atual, 2),
        "hora": pd.Timestamp.now(tz="America/Sao_Paulo").strftime("%H:%M"),
        "rsi14": _last("rsi", 50.0) if "rsi" in ind.columns else round(_self._rsi_manual(close, 14).iloc[-1], 2),
        "stoch_k": _last("stoch_k", 50.0),
        "stoch_d": _last("stoch_d", 50.0),
        "vol_ratio": round(_last("vol_ratio", 1.0), 2),
        "ma20": round(ma20, 2), "ma50": round(ma50, 2), "ma200": round(ma200, 2),
        "adx": round(_last("adx", 0.0), 2),
        "macd_diff": round(_last("macd_diff", 0.0), 4),
        "bollinger_pct_b": round(bollinger_pct_b, 4),
        "z_score_20": round(z_score_20, 4),
        "atr14": round(_last("atr", 0.0), 4),
        "vwap": round(vwap, 2),
        "vwap_dist_pct": round(vwap_dist_pct, 2),
        "vwap_available": vwap_available,
        "hv_20": round(hv_20, 4), "hv_60": round(hv_60, 4),
        "sigma_20": round(sigma_20, 4),
        "expected_move": round(em, 2),
        "expected_move_pct": round(em / preco_atual * 100, 2),
        "faixa_1sigma": faixa_1sigma,
        "dte_proximo_venc": dte,
        "iv_atm": iv_atm,
        "iv_hv_ratio": iv_hv_ratio,
        "vol_read": vol_read,
        "faixa_52s_min": round(faixa_min, 2),
        "faixa_52s_max": round(faixa_max, 2),
        "setups": setups,
    }


def _atm_iv_from_chain(chain: list, spot: float, dte: int):
    """IV ATM a partir da chain bruta da opcoes.net. Retorna None se não der.

    Estrutura por linha (op[:10]): ticker, _, tipo, _, _, strike, _, _, preco, negocios.

    LIMITATION: A data de vencimento NÃO está nesse slice — sem ela, usamos dte (estimado
    em dias úteis) e o strike mais próximo do spot. Se a chain misturar vários vencimentos,
    o strike escolhido pode pertencer a outro vencimento que não o dte usado na inversão
    de IV → IV pode estar desviada.

    MITIGATION: Se IV cair fora de 0.01–4.99 (guardrail), retorna None e a leitura de vol
    degrada para "indisponivel" (HV-only). Isso previne propagação de IVs ruins.
    """
    if not chain:
        return None
    melhores = []
    for op in chain:
        if len(op) < 10:
            continue
        _, _, tipo, _, _, strike, _, _, preco, neg = op[:10]
        try:
            strike = float(strike); preco = float(preco)
        except (TypeError, ValueError):
            continue
        if tipo not in ("CALL", "PUT") or preco <= 0.01:
            continue
        melhores.append((abs(strike - spot), tipo, strike, preco))
    if not melhores:
        return None
    melhores.sort(key=lambda x: x[0])
    # Find nearest strike to spot
    # NOTE: chain contains ALL expirations mixed; we have no maturity info for each strike.
    # If strike is from a different expiration than dte_proximo_venc, IV inversion will be off.
    # This is mitigated by IV range guard below: out-of-range IV returns None.
    _, tipo, strike, preco = melhores[0]
    try:
        T = max(dte, 1) / 252  # dte em dias úteis → anos
        iv = implied_volatility(spot, strike, T, preco, tipo.upper())
        # IV range guard (0.01–4.99): prevents unrealistic IVs from propagating
        # when strike is from a mismatched expiration (see LIMITATION above).
        # Returns None → vol_read degrades to "indisponivel".
        return float(iv) if iv and 0.01 < iv < 4.99 else None
    except Exception:
        return None

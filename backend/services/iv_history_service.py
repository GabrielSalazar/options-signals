"""Histórico diário de IV ATM e cálculo de IV Rank (Camada 1.2)."""
import logging
from datetime import datetime, timezone

from backend.domain.options_math import estimar_iv_historica, mes_vencimento_ideal, resolver_iv
from backend.services.data_providers import fetch_brapi_historical, obter_opcao_atm
from backend.services.supabase_client import get_supabase
from backend.services.ticker_loader import carregar_tickers_b3

logger = logging.getLogger("b3_api")


def _iv_atm_do_ticker(ticker_base: str, df) -> tuple:
    """Retorna (iv_atm | None, hv_20d, fonte) para um ticker."""
    hv_20d = estimar_iv_historica(df)
    preco = float(df["Close"].iloc[-1])
    mes_v, ano_v, dte = mes_vencimento_ideal()
    T = max(dte, 1) / 252

    opcao = obter_opcao_atm(ticker_base, preco, mes_v, ano_v, tipo_alvo="CALL")
    if not opcao:
        return None, hv_20d, "sem_dado"

    iv_atm, fonte = resolver_iv(opcao["preco_tela"], preco, opcao["strike_real"], T, "CALL", hv_20d)
    if fonte != "tela":
        return None, hv_20d, "sem_dado"
    return iv_atm, hv_20d, "tela"


def coletar_iv_diaria(tickers: dict | None = None) -> int:
    """
    Job diário (pós-fechamento): persiste iv_atm/hv_20d/iv_premium por ticker
    do universo líquido em `iv_history`. Falha de um ticker não derruba o job.
    Retorna o nº de tickers persistidos com sucesso.
    """
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — histórico de IV não coletado")
        return 0

    if tickers is None:
        tickers = carregar_tickers_b3()

    hoje = datetime.now(timezone.utc).date().isoformat()
    persistidos = 0
    for ticker, _nome in tickers.items():
        ticker_base = ticker.replace(".SA", "")
        try:
            df = fetch_brapi_historical(ticker, range_="3mo", interval="1d")
            if df is None or df.empty:
                continue
            iv_atm, hv_20d, fonte = _iv_atm_do_ticker(ticker_base, df)
            if iv_atm is None:
                continue
            iv_premium = (iv_atm / hv_20d) if hv_20d > 0 else None
            supabase.table("iv_history").upsert({
                "ticker": ticker_base,
                "data": hoje,
                "iv_atm": round(iv_atm, 4),
                "hv_20d": round(hv_20d, 4),
                "iv_premium": round(iv_premium, 4) if iv_premium else None,
                "fonte": fonte,
            }, on_conflict="ticker,data").execute()
            persistidos += 1
        except Exception as e:
            logger.warning(f"Erro ao coletar IV de {ticker_base}: {e}")

    logger.info(f"Histórico de IV coletado — {persistidos}/{len(tickers)} tickers")
    return persistidos


def iv_rank(ticker_base: str) -> dict:
    """Retorna {'iv_rank': float|None, 'iv_premium': float|None, 'confiavel': bool}.
    'confiavel' exige >=60 dias úteis de histórico; caso contrário usa o proxy iv_premium."""
    supabase = get_supabase()
    if not supabase:
        return {"iv_rank": None, "iv_premium": None, "confiavel": False}

    try:
        res = (supabase.table("iv_history")
               .select("iv_atm, iv_premium, data")
               .eq("ticker", ticker_base)
               .order("data", desc=True)
               .limit(252)
               .execute())
        rows = res.data or []
    except Exception as e:
        logger.warning(f"Erro ao consultar iv_history de {ticker_base}: {e}")
        return {"iv_rank": None, "iv_premium": None, "confiavel": False}

    if not rows:
        return {"iv_rank": None, "iv_premium": None, "confiavel": False}

    atual = rows[0]
    ivs = [r["iv_atm"] for r in rows if r.get("iv_atm") is not None]
    confiavel = len(ivs) >= 60

    if confiavel and atual.get("iv_atm") is not None:
        menor, maior = min(ivs), max(ivs)
        rank = ((atual["iv_atm"] - menor) / (maior - menor) * 100) if maior > menor else 50.0
        return {"iv_rank": round(rank, 1), "iv_premium": atual.get("iv_premium"), "confiavel": True}

    return {"iv_rank": None, "iv_premium": atual.get("iv_premium"), "confiavel": False}

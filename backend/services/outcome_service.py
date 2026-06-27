"""Rastreamento de desfecho dos sinais (abordagem A).

Lê os sinais persistidos no Supabase, busca o preço da ação desde a data de cada
sinal e reprecifica a opção via Black-Scholes para classificar ganho/perda/aberto
([backend/domain/outcome.py](outcome)). Agrega o resultado comparando o score
clássico (que decide hoje) com o ponderado (shadow), respondendo: dos sinais que
deram certo/errado, quantos o ponderado teria aprovado.
"""
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd

from backend.services.supabase_client import get_supabase
from backend.services.core_engine import _baixar_ohlcv
from backend.domain.outcome import avaliar_desfecho, comparar_por_desfecho

logger = logging.getLogger("b3_api")

_CAMPOS = ("ticker, tipo_sinal, strike_ref, premio_est, preco_tela, alvo1, alvo2, "
           "alvo_final, stop, hv_20d, iv_mercado, dte, preco_acao, score, "
           "score_ponderado, ponderado_passou, timestamp")


def _precos_desde(ticker_sa: str, desde: datetime) -> list:
    """Closes diários da ação a partir de `desde` (inclusive), via provider (cacheado)."""
    df = _baixar_ohlcv(ticker_sa, "6mo", "1d", verbose=False)
    if df is None or df.empty:
        return []
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    if "Close" not in df.columns:
        return []
    serie = df["Close"].dropna()
    serie = serie[serie.index >= pd.Timestamp(desde.date())]
    return [float(x) for x in serie.tolist()]


def avaliar_sinais(dias: int = 30) -> dict:
    """Avalia o desfecho dos sinais dos últimos `dias` e compara clássico vs ponderado."""
    supabase = get_supabase()
    if not supabase:
        return {"erro": "Supabase indisponível", "resolvidos": 0, "sinais_avaliados": 0}

    cutoff = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    try:
        res = (supabase.table("signals")
               .select(_CAMPOS)
               .gte("timestamp", cutoff)
               .order("timestamp")
               .limit(2000)
               .execute())
        rows = res.data or []
    except Exception as e:
        return {"erro": str(e), "resolvidos": 0, "sinais_avaliados": 0}

    avaliados = []
    for s in rows:
        ts = s.get("timestamp")
        if not ts or s.get("strike_ref") is None or s.get("dte") is None:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        ticker_sa = (s.get("ticker") or "").upper()
        if not ticker_sa:
            continue
        if not ticker_sa.endswith(".SA"):
            ticker_sa += ".SA"

        precos = _precos_desde(ticker_sa, dt)
        if len(precos) < 2:
            continue
        r = avaliar_desfecho(s, precos)
        avaliados.append({
            **r,
            "ticker": s.get("ticker"),
            "tipo_sinal": s.get("tipo_sinal"),
            "score": s.get("score"),
            "score_ponderado": s.get("score_ponderado"),
            "ponderado_passou": s.get("ponderado_passou"),
        })

    relatorio = comparar_por_desfecho(avaliados)
    relatorio["periodo_dias"] = dias
    relatorio["sinais_avaliados"] = len(avaliados)
    dist: dict = {}
    for a in avaliados:
        dist[a["desfecho"]] = dist.get(a["desfecho"], 0) + 1
    relatorio["distribuicao"] = dist
    return relatorio

"""Endpoints de consulta de sinais: listagem, histórico, watchlist, analytics
e performance agregada. (O scan em si fica em routers/scan.py.)"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from backend.core.config import ATIVOS_B3
from backend.services import signal_service, signals_repository
from backend.services.supabase_client import get_supabase
from backend.services.ticker_loader import get_all_b3_assets

logger = logging.getLogger("b3_api")
router = APIRouter(tags=["Signals"])


@router.get("/signals")
def get_signals(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    tipo: str = Query(default=None),
    min_score: int = Query(default=0),
):
    """Busca sinais do Supabase com filtros server-side. Fallback para memória."""
    supabase = get_supabase()
    if not supabase:
        sinais = signal_service.last_scan_signals()
        if tipo:
            sinais = [s for s in sinais if s.get("tipo_sinal") == tipo]
        if min_score > 0:
            sinais = [s for s in sinais if s.get("score", 0) >= min_score]
        return {"data": sinais[offset:offset + limit], "count": len(sinais), "source": "memory"}

    try:
        res = signals_repository.fetch_signals(supabase, limit, offset, tipo, min_score)
        return {"data": res.data, "count": res.count, "source": "supabase"}
    except Exception as e:
        logger.error(f"Erro ao buscar sinais: {e}")
        last = signal_service.last_scan_signals()
        return {"data": last[offset:offset + limit], "count": len(last), "source": "memory_fallback"}


@router.get("/signals/history")
def get_history(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    ticker: str = Query(default=None),
    tipo_sinal: str = Query(default=None),
):
    supabase = get_supabase()
    filtered = signal_service.last_scan_signals()
    if ticker:
        filtered = [s for s in filtered if s.get("ticker", "").upper() == ticker.upper()]
    if tipo_sinal:
        filtered = [s for s in filtered if s.get("tipo_sinal", "") == tipo_sinal.upper()]
    if not supabase:
        return {"data": filtered[offset:offset + limit], "source": "memory"}
    try:
        res = signals_repository.fetch_history(supabase, limit, offset, ticker, tipo_sinal)
        return {"data": res.data, "source": "supabase"}
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return {"data": filtered[offset:offset + limit], "source": "memory_fallback"}


@router.get("/signals/watchlist")
def get_watchlist(all_b3: bool = Query(default=False)):
    base = get_all_b3_assets() if all_b3 else ATIVOS_B3
    return {"watchlist": [t.replace(".SA", "") for t in base.keys()],
            "count": len(base),
            "universe": "all-b3" if all_b3 else "curated"}


@router.get("/signals/analytics/{ticker}")
def analytics(ticker: str):
    supabase = get_supabase()
    ticker_upper = ticker.upper().replace(".SA", "")
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase não configurado")
    try:
        res = signals_repository.fetch_analytics(supabase, ticker_upper)
        sinais = res.data
        calls = [s for s in sinais if s.get("tipo_sinal") == "CALL"]
        puts = [s for s in sinais if s.get("tipo_sinal") == "PUT"]
        return {
            "ticker": ticker_upper,
            "total": len(sinais),
            "calls": len(calls),
            "puts": len(puts),
            "avg_score": round(sum(s.get("score", 0) for s in sinais) / len(sinais), 2) if sinais else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/performance")
def signals_performance(days: int = Query(default=30, ge=1, le=365)):
    """
    Dashboard agregado: win-rate por ticker, hit-rate por alvo, ponderado vs clássico.
    Lê do Supabase os últimos `days` dias de sinais.
    """
    supabase = get_supabase()
    if not supabase:
        return {"error": "Supabase indisponível"}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        res = signals_repository.fetch_performance(supabase, cutoff)
        rows = res.data or []
    except Exception as e:
        return {"error": str(e)}

    total = len(rows)
    if not total:
        return {"period_days": days, "total_signals": 0, "by_ticker": [], "summary": {}}

    by_ticker: dict = {}
    for r in rows:
        tk = r.get("ticker", "—")
        by_ticker.setdefault(tk, {"count": 0, "call": 0, "put": 0,
                                  "score_sum": 0, "score_pond_sum": 0,
                                  "pond_passou": 0, "delta_sum": 0.0, "delta_n": 0})
        b = by_ticker[tk]
        b["count"] += 1
        b["call"] += 1 if r.get("tipo_sinal") == "CALL" else 0
        b["put"] += 1 if r.get("tipo_sinal") == "PUT" else 0
        b["score_sum"] += r.get("score") or 0
        if r.get("score_ponderado") is not None:
            b["score_pond_sum"] += r["score_ponderado"]
        if r.get("ponderado_passou"):
            b["pond_passou"] += 1
        g = r.get("greeks") or {}
        if isinstance(g, dict) and g.get("delta") is not None:
            b["delta_sum"] += abs(g["delta"])
            b["delta_n"] += 1

    by_ticker_list = []
    for tk, b in by_ticker.items():
        by_ticker_list.append({
            "ticker": tk,
            "count": b["count"],
            "call": b["call"],
            "put": b["put"],
            "avg_score": round(b["score_sum"] / b["count"], 2) if b["count"] else 0,
            "avg_score_ponderado": round(b["score_pond_sum"] / b["count"], 1) if b["count"] else 0,
            "ponderado_concordancia_pct": round(b["pond_passou"] / b["count"] * 100, 1) if b["count"] else 0,
            "avg_abs_delta": round(b["delta_sum"] / b["delta_n"], 3) if b["delta_n"] else None,
        })
    by_ticker_list.sort(key=lambda x: x["count"], reverse=True)

    total_pond_passou = sum(1 for r in rows if r.get("ponderado_passou"))
    return {
        "period_days": days,
        "total_signals": total,
        "calls": sum(1 for r in rows if r.get("tipo_sinal") == "CALL"),
        "puts": sum(1 for r in rows if r.get("tipo_sinal") == "PUT"),
        "ponderado_concordancia_pct": round(total_pond_passou / total * 100, 1),
        "avg_score_classico": round(sum(r.get("score") or 0 for r in rows) / total, 2),
        "avg_score_ponderado": round(
            sum(r["score_ponderado"] for r in rows if r.get("score_ponderado") is not None)
            / max(1, sum(1 for r in rows if r.get("score_ponderado") is not None)), 1
        ),
        "by_ticker": by_ticker_list,
    }


@router.get("/signals/outcomes")
def signals_outcomes(days: int = Query(default=30, ge=1, le=365)):
    """Rastreamento de desfecho (abordagem A): reprecifica cada sinal via
    Black-Scholes sobre o preço da ação e compara o win-rate do clássico vs.
    o efeito de filtrar pelo score ponderado (shadow). Base para decidir o
    scoring (clássico × ponderado)."""
    from backend.services.outcome_service import avaliar_sinais
    return avaliar_sinais(dias=days)


@router.get("/signals/strategies")
def get_strategies():
    return {"strategies": ["CALL OTM", "PUT OTM", "CALL ATM", "PUT ATM"]}

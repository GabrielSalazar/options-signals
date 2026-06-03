"""Geração, persistência e estado em memória dos sinais.

Concentra todo o fluxo de produção de sinais: análise (single, batch, scan
agendado), persistência no Supabase, limpeza, fila de alertas em tempo real e
o último resultado de scan mantido em memória (fallback quando o Supabase está
indisponível).

Dependências em sentido único: ``routers → services → domain/core``.
"""
import asyncio
import logging
import threading
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.core.config import ATIVOS_B3, CONFIG, get_all_b3_assets
from backend.services.core_engine import analisar_ativo
from backend.services.supabase_client import get_supabase
from backend.services.telegram_service import enviar_telegram

logger = logging.getLogger("b3_api")

# ── Estado em memória ───────────────────────────────────────────────────────────
_last_scan_sinais: list[dict] = []
_last_scan_ts: str | None = None
_scan_lock = threading.Lock()
_alert_queues: list[asyncio.Queue] = []


def last_scan_signals() -> list[dict]:
    return _last_scan_sinais


def last_scan_ts() -> str | None:
    return _last_scan_ts


def update_last_scan(sinais: list[dict]):
    """Atualiza o último resultado de scan de forma thread-safe."""
    global _last_scan_sinais, _last_scan_ts
    with _scan_lock:
        _last_scan_sinais = sinais
        _last_scan_ts = datetime.now(timezone.utc).isoformat()


# ── Fila de alertas (SSE proativo) ──────────────────────────────────────────────
def register_alert_queue() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _alert_queues.append(q)
    return q


def unregister_alert_queue(q: asyncio.Queue):
    if q in _alert_queues:
        _alert_queues.remove(q)


async def broadcast_alert(sinal: dict):
    for q in _alert_queues:
        await q.put(sinal)


def _maybe_broadcast(sinal: dict):
    """Agenda o broadcast do sinal se houver event loop rodando (rotas async)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_alert(sinal))
    except RuntimeError:
        pass


# ── Persistência ────────────────────────────────────────────────────────────────
def persist_signals(sinais: list[dict]):
    """Upsert de sinais no Supabase — persiste todos os campos do SignalCard."""
    if not sinais:
        return
    supabase = get_supabase()
    if not supabase:
        logger.warning("Supabase indisponível — sinais não persistidos")
        return

    rows = []
    for s in sinais:
        rows.append({
            "ticker":        s["ticker"],
            "nome":          s.get("nome", ""),
            "tipo_sinal":    s["tipo_sinal"],
            "direcao":       s.get("direcao", ""),
            "score":         s["score"],
            "preco_acao":    s.get("preco_acao"),
            "ticker_opcao":  s.get("ticker_opcao", "N/A"),
            "strike_ref":    s.get("strike_ref"),
            "dist_otm_pct":  s.get("dist_otm_pct"),
            "iv_hist":       s.get("iv_hist"),
            "dte":           s.get("dte"),
            "mes_venc":      s.get("mes_venc"),
            "ano_venc":      s.get("ano_venc"),
            "premio_est":    s.get("premio_est"),
            "preco_tela":    s.get("preco_tela"),
            "entrada_min":   s.get("entrada_min"),
            "entrada_max":   s.get("entrada_max"),
            "alvo1":         s.get("alvo1"),
            "alvo2":         s.get("alvo2"),
            "alvo_final":    s.get("alvo_final"),
            "stop":          s.get("stop"),
            "rr_alvo1":      s.get("rr_alvo1"),
            "rr_alvo2":      s.get("rr_alvo2"),
            "rr_final":      s.get("rr_final"),
            "stoch_k":       s.get("stoch_k"),
            "rsi":           s.get("rsi"),
            "vol_ratio":     s.get("vol_ratio"),
            "gatilhos":      s.get("gatilhos", []),
            "book_until":    s.get("book_until"),
            "greeks":        s.get("greeks"),
            "score_ponderado": s.get("score_ponderado"),
            "ponderado_passou": s.get("ponderado_passou"),
            "iv_mercado":    s.get("iv_mercado"),
            "timestamp":     datetime.now(timezone.utc).isoformat(),
        })

    try:
        supabase.table("signals").insert(rows).execute()
        logger.info(f"{len(rows)} sinal(is) persistido(s) no Supabase")
    except Exception as e:
        logger.error(f"Erro ao persistir sinais: {e}")


def cleanup_old_signals(days: int = 30):
    """Remove sinais com mais de `days` dias para evitar crescimento ilimitado."""
    supabase = get_supabase()
    if not supabase:
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        supabase.table("signals").delete().lt("timestamp", cutoff).execute()
        logger.info(f"Cleanup: sinais anteriores a {cutoff} removidos")
    except Exception as e:
        logger.error(f"Erro no cleanup: {e}")


def rebuild_historico_sinais():
    """B2-fix: reconstrói _historico_sinais a partir do Supabase para evitar
    bypass da regra de reentrada após restart do processo."""
    from backend.core.config import _historico_sinais
    supabase = get_supabase()
    if not supabase:
        return
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=CONFIG.get("reentrada_min_dias", 3) + 1)).isoformat()
        res = (supabase.table("signals")
               .select("ticker, timestamp")
               .gte("timestamp", cutoff)
               .order("timestamp")
               .execute())
        for row in res.data:
            ticker = row.get("ticker", "")
            ts_str = row.get("timestamp", "")
            if not ticker or not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                _historico_sinais.setdefault(ticker, []).append(ts)
            except Exception:
                pass
        logger.info(f"historico_sinais reconstituído: {len(_historico_sinais)} tickers com sinal recente")
    except Exception as e:
        logger.warning(f"Erro ao reconstituir historico_sinais: {e}")


# ── Análise / scans ───────────────────────────────────────────────────────────
def _normalize_ticker(ticker: str) -> str:
    t = ticker.upper()
    return t if t.endswith(".SA") else t + ".SA"


def analyse_ticker(ticker: str, nome: str, verbose: bool = False) -> dict | None:
    """Analisa um único ativo — thread-safe (engana exceções por ativo)."""
    try:
        return analisar_ativo(ticker, nome, verbose=verbose)
    except Exception as e:
        logger.warning(f"Erro ao analisar {ticker}: {e}")
        return None


def scan_single(ticker: str) -> dict | None:
    """Scan de um ticker: analisa, persiste, notifica e faz broadcast."""
    ticker_sa = _normalize_ticker(ticker)
    nome = ATIVOS_B3.get(ticker_sa, ticker.upper())
    sinal = analisar_ativo(ticker_sa, nome, verbose=True)
    if not sinal:
        return None
    persist_signals([sinal])
    enviar_telegram(sinal)
    _maybe_broadcast(sinal)
    return sinal


def scan_batch(tickers: list[str]) -> list[dict]:
    """Scan em batch: paraleliza com 10 workers."""
    sinais: list[dict] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        def do_scan(t: str):
            t_sa = _normalize_ticker(t)
            nome = ATIVOS_B3.get(t_sa, t.upper())
            return analyse_ticker(t_sa, nome)

        futures = {pool.submit(do_scan, t): t for t in tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)

    if sinais:
        persist_signals(sinais)
        for s in sinais:
            enviar_telegram(s)
        update_last_scan(sinais)

    return sinais


def run_scan(verbose: bool = False, all_b3: bool = False):
    """Scan agendado: 10 workers em paralelo. all_b3=True varre todo o universo da B3."""
    logger.info("Iniciando scan agendado..." + (" (UNIVERSO COMPLETO B3)" if all_b3 else ""))
    ativos = list((get_all_b3_assets() if all_b3 else ATIVOS_B3).items())
    sinais: list[dict] = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(analyse_ticker, ticker, nome, verbose): ticker
                   for ticker, nome in ativos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)
                enviar_telegram(result)
                _maybe_broadcast(result)

    update_last_scan(sinais)
    persist_signals(sinais)
    logger.info(f"Scan concluído — {len(sinais)} sinal(is) encontrado(s)")

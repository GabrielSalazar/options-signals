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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from backend.core.config import ATIVOS_B3, CONFIG
from backend.services.core_engine import analisar_ativo
from backend.services.supabase_client import get_supabase
from backend.services.telegram_service import enviar_telegram, notificar_lote
from backend.services.ticker_loader import carregar_tickers_b3, nome_ativo

logger = logging.getLogger("b3_api")

# ── Estado em memória ───────────────────────────────────────────────────────────
_last_scan_sinais: list[dict] = []
_last_scan_ts: str | None = None
_scan_lock = threading.Lock()
_alert_queues: list[asyncio.Queue] = []
_alert_queues_lock = threading.Lock()

_main_loop: asyncio.AbstractEventLoop | None = None
_main_loop_lock = threading.Lock()

def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    with _main_loop_lock:
        _main_loop = loop


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
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    with _alert_queues_lock:
        _alert_queues.append(q)
    return q


def unregister_alert_queue(q: asyncio.Queue):
    with _alert_queues_lock:
        if q in _alert_queues:
            _alert_queues.remove(q)


async def broadcast_alert(sinal: dict):
    with _alert_queues_lock:
        queues_copy = list(_alert_queues)
    for q in queues_copy:
        try:
            q.put_nowait(sinal)
        except asyncio.QueueFull:
            try:
                q.get_nowait()  # descarta o mais antigo
                q.put_nowait(sinal)
            except Exception:
                pass


def _maybe_broadcast(sinal: dict):
    """Agenda o broadcast do sinal se houver event loop rodando."""
    global _main_loop
    with _main_loop_lock:
        loop = _main_loop
    if loop is not None:
        try:
            asyncio.run_coroutine_threadsafe(broadcast_alert(sinal), loop)
        except Exception as e:
            logger.error(f"Erro ao agendar broadcast SSE: {e}")
    else:
        try:
            running_loop = asyncio.get_running_loop()
            running_loop.create_task(broadcast_alert(sinal))
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
            "score_tecnico": s.get("score_tecnico", s.get("score")),
            "bonus_sessao":  s.get("bonus_sessao", 0),
            "preco_acao":    s.get("preco_acao"),
            "ticker_opcao":  s.get("ticker_opcao", "N/A"),
            "strike_ref":    s.get("strike_ref"),
            "dist_otm_pct":  s.get("dist_otm_pct"),
            "hv_20d":        s.get("hv_20d"),
            "iv_impl":       s.get("iv_impl"),
            "iv_source":     s.get("iv_source"),
            "iv_rank":       s.get("iv_rank"),
            "iv_premium":    s.get("iv_premium"),
            "iv_filter_decisao": s.get("iv_filter_decisao"),
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
            "gatilhos_ids":  s.get("gatilhos_ids", []),
            "familias_ativas": s.get("familias_ativas"),
            "score_familias_capped": s.get("score_familias_capped"),
            "consenso_decisao": s.get("consenso_decisao"),
            "setup":         s.get("setup"),
            "setup_params_shadow": s.get("setup_params_shadow"),
            "book_until":    s.get("book_until"),
            "greeks":        s.get("greeks"),
            "score_ponderado": s.get("score_ponderado"),
            "ponderado_passou": s.get("ponderado_passou"),
            "iv_mercado":    s.get("iv_mercado"),
            "oi":            s.get("oi"),
            "bid":           s.get("bid"),
            "ask":           s.get("ask"),
            "spread_pct":    s.get("spread_pct"),
            "vxbr":          s.get("vxbr"),
            "evento_label":  s.get("evento_label"),
            "filtro_liquidez_decisao": s.get("filtro_liquidez_decisao"),
            "filtro_liquidez_motivo":  s.get("filtro_liquidez_motivo"),
            "ativo_entrada": s.get("ativo_entrada"),
            "ativo_stop":    s.get("ativo_stop"),
            "ativo_tp1":     s.get("ativo_tp1"),
            "ativo_tp2":     s.get("ativo_tp2"),
            "absorcao":      s.get("absorcao"),
            "fluxo_persistencia_dias": s.get("fluxo_persistencia_dias"),
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
    from backend.core.config import _historico_sinais, _historico_sinais_lock
    supabase = get_supabase()
    if not supabase:
        return
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=CONFIG.get("reentrada_min_dias", 3) + 1)).isoformat()
        res = (supabase.table("signals")
               .select("ticker, timestamp, tipo_sinal, score_tecnico, score")
               .gte("timestamp", cutoff)
               .order("timestamp")
               .execute())
        with _historico_sinais_lock:
            _historico_sinais.clear()
            for row in res.data:
                ticker = row.get("ticker", "")
                ts_str = row.get("timestamp", "")
                if not ticker or not ts_str:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
                    score = row.get("score_tecnico")
                    if score is None:
                        score = row.get("score", 0)
                    _historico_sinais.setdefault(ticker, []).append(
                        {"ts": ts, "tipo": row.get("tipo_sinal"), "score": int(score or 0)}
                    )
                except Exception:
                    pass
        logger.info(f"historico_sinais reconstituído: {len(_historico_sinais)} tickers com sinal recente")
    except Exception as e:
        logger.warning(f"Erro ao reconstituir historico_sinais: {e}")


# ── Análise / scans ───────────────────────────────────────────────────────────
def _normalize_ticker(ticker: str) -> str:
    t = ticker.upper()
    return t if t.endswith(".SA") else t + ".SA"


def analyse_ticker(ticker: str, nome: str, verbose: bool = False,
                   incluir_em_cooldown: bool = False) -> dict | None:
    """Analisa um único ativo — thread-safe (engana exceções por ativo)."""
    try:
        return analisar_ativo(ticker, nome, verbose=verbose,
                              incluir_em_cooldown=incluir_em_cooldown)
    except Exception as e:
        logger.warning(f"Erro ao analisar {ticker}: {e}")
        return None


def sinais_novos(sinais: list[dict]) -> list[dict]:
    """Filtra sinais em cooldown de reentrada: só os novos podem ser
    persistidos/notificados (o cooldown continua deduplicando esses caminhos;
    a exibição no scan manual mostra todos)."""
    return [s for s in sinais if not s.get("em_cooldown")]


def scan_single(ticker: str) -> dict | None:
    """Scan de um ticker: analisa, persiste, notifica e faz broadcast.

    Sinal em cooldown de reentrada é retornado (exibição), mas não é
    persistido nem notificado de novo."""
    ticker_sa = _normalize_ticker(ticker)
    nome = nome_ativo(ticker_sa)
    sinal = analisar_ativo(ticker_sa, nome, verbose=True, incluir_em_cooldown=True)
    if not sinal:
        return None
    if not sinal.get("em_cooldown"):
        persist_signals([sinal])
        enviar_telegram(sinal)
        _maybe_broadcast(sinal)
    return sinal


def scan_batch(tickers: list[str]) -> list[dict]:
    """Scan em batch: paraleliza com 10 workers. Retorna todos os sinais
    (inclusive em cooldown); persiste/notifica só os novos."""
    sinais: list[dict] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        def do_scan(t: str):
            t_sa = _normalize_ticker(t)
            nome = nome_ativo(t_sa)
            return analyse_ticker(t_sa, nome, incluir_em_cooldown=True)

        futures = {pool.submit(do_scan, t): t for t in tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)

    novos = sinais_novos(sinais)
    if novos:
        persist_signals(novos)
        notificar_lote(novos)
        update_last_scan(novos)

    return sinais


def run_scan(verbose: bool = False, universe: str = "liquido"):
    """Scan agendado. universe: 'liquido' (padrão, universo filtrado) | 'curado'.

    A2: workers via CONFIG['scan_max_workers']. A3: Telegram em lote ao final
    (fora do hot-loop). A4: loga a duração do scan.
    """
    inicio = datetime.now(timezone.utc)
    if universe == "curado":
        ativos = list(ATIVOS_B3.items())
    else:
        ativos = list(carregar_tickers_b3().items())
    logger.info(f"Iniciando scan ({universe}) — {len(ativos)} ativos...")
    sinais: list[dict] = []

    max_workers = CONFIG.get("scan_max_workers", 8)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(analyse_ticker, ticker, nome, verbose): ticker
                   for ticker, nome in ativos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)
                _maybe_broadcast(result)

    update_last_scan(sinais)
    persist_signals(sinais)
    notificar_lote(sinais)
    dur = (datetime.now(timezone.utc) - inicio).total_seconds()
    logger.info(f"Scan ({universe}) concluído — {len(sinais)} sinal(is) em {dur:.0f}s")

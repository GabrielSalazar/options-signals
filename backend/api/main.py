import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import threading
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from backend.core.config import ATIVOS_B3, CONFIG, get_all_b3_assets
from backend.services.core_engine import analisar_ativo
from backend.core.cache import redis_status

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("b3_api")

_TELEGRAM_CONFIG_FILE = "telegram_config.json"


def _load_telegram_config():
    """Carrega config do Telegram de arquivo JSON (persiste entre soft-restarts)."""
    # Prioriza variáveis de ambiente (.env ou secrets do provedor de cloud)
    env_token = os.getenv("TELEGRAM_BOT_TOKEN")
    env_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if env_token:
        CONFIG["telegram_token"] = env_token
    if env_chat_id:
        CONFIG["telegram_chat_id"] = env_chat_id

    try:
        with open(_TELEGRAM_CONFIG_FILE) as f:
            data = json.load(f)
        if data.get("token") and not env_token:
            CONFIG["telegram_token"] = data["token"]
        if data.get("chat_id") and not env_chat_id:
            CONFIG["telegram_chat_id"] = data["chat_id"]
        logger.info("Config Telegram carregada de telegram_config.json")
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning(f"Erro ao carregar telegram_config.json: {e}")


def _save_telegram_config(token: str, chat_id: str):
    """Persiste config do Telegram em arquivo JSON."""
    try:
        with open(_TELEGRAM_CONFIG_FILE, "w") as f:
            json.dump({"token": token, "chat_id": chat_id}, f)
    except Exception as e:
        logger.warning(f"Erro ao salvar telegram_config.json: {e}")

NOMES_MESES = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
               7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

def enviar_telegram(sinal: dict):
    import requests
    token   = CONFIG.get("telegram_token", "")
    chat_id = CONFIG.get("telegram_chat_id", "")
    if not token or not chat_id:
        return
        
    mes_str = NOMES_MESES.get(sinal.get("mes_venc"), "")
    msg = (
        f"🎯 *SINAL B3 — {sinal.get('ticker')}* ({sinal.get('nome')})\\n"
        f"*Tipo:* {sinal.get('tipo_sinal')} | *Venc:* {mes_str}/{sinal.get('ano_venc')}\\n"
        f"*Strike ref:* R$ {sinal.get('strike_ref', 0):.2f} ({sinal.get('dist_otm_pct', 0):.0f}% OTM)\\n"
        f"*IV Hist:* {sinal.get('iv_hist')}% | *DTE:* {sinal.get('dte')} du\\n\\n"
        f"*Entrada:* R$ {sinal.get('entrada_min', 0):.2f} – {sinal.get('entrada_max', 0):.2f}\\n"
        f"*Alvo 1:* R$ {sinal.get('alvo1', 0):.2f} (+{CONFIG.get('alvo1_pct', 0.25)*100:.0f}%) | R/R: {sinal.get('rr_alvo1', 0):.1f}×\\n"
        f"*Alvo 2:* R$ {sinal.get('alvo2', 0):.2f} (+{CONFIG.get('alvo2_pct', 0.5)*100:.0f}%) | R/R: {sinal.get('rr_alvo2', 0):.1f}×\\n"
        f"*Stop:* R$ {sinal.get('stop', 0):.2f} ({CONFIG.get('stop_pct', 0.5)*100:.0f}%)\\n\\n"
        f"*Score:* {sinal.get('score')}/10\\n"
        f"*Gatilhos:*\\n• " + "\\n• ".join(sinal.get("gatilhos", []))
    )
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={'chat_id': chat_id, 'text': msg, 'parse_mode': 'Markdown'}, timeout=10)
        logger.info(f"Sinal {sinal.get('ticker')} enviado ao Telegram.")
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram para {sinal.get('ticker')}: {e}")

# ── Supabase ──────────────────────────────────────────────────────────────────

def get_supabase():
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if url and key:
            return create_client(url, key)
    except Exception as e:
        logger.warning(f"Supabase não configurado: {e}")
    return None


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


# ── Scanner job ───────────────────────────────────────────────────────────────

_last_scan_sinais: list[dict] = []
_last_scan_ts: str | None = None
_scan_lock = threading.Lock()
_alert_queues: list[asyncio.Queue] = []

async def broadcast_alert(sinal: dict):
    for q in _alert_queues:
        await q.put(sinal)


class BacktestParams(BaseModel):
    ticker: str
    start_date: str = "2024-01-01"
    end_date: str = ""

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        import re
        v = v.upper().replace(".SA", "")
        if not re.match(r"^[A-Z]{4,5}[0-9]{1,2}$", v):
            raise ValueError("Ticker inválido — use formato B3 (ex: PETR4, VALE3)")
        return v


def _scan_one(ticker: str, nome: str, verbose: bool = False) -> dict | None:
    """Analisa um único ativo — thread-safe."""
    try:
        return analisar_ativo(ticker, nome, verbose=verbose)
    except Exception as e:
        logger.warning(f"Erro ao analisar {ticker}: {e}")
        return None


def run_scan(verbose: bool = False, all_b3: bool = False):
    """Scan agendado: 10 workers em paralelo. all_b3=True varre todo o universo da B3."""
    global _last_scan_sinais, _last_scan_ts
    logger.info("Iniciando scan agendado..." + (" (UNIVERSO COMPLETO B3)" if all_b3 else ""))
    ativos = list((get_all_b3_assets() if all_b3 else ATIVOS_B3).items())
    sinais = []

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_scan_one, ticker, nome, verbose): ticker
                   for ticker, nome in ativos}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)
                enviar_telegram(result)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(broadcast_alert(result))
                except RuntimeError:
                    pass

    with _scan_lock:
        _last_scan_sinais = sinais
        _last_scan_ts = datetime.now(timezone.utc).isoformat()
    persist_signals(sinais)
    logger.info(f"Scan concluído — {len(sinais)} sinal(is) encontrado(s)")


# ── Lifecycle ─────────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def _rebuild_historico_sinais():
    """B2-fix: reconstrói _historico_sinais a partir do Supabase para evitar
    bypass da regra de reentrada após restart do processo."""
    from backend.core.config import _historico_sinais, registrar_sinal
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_telegram_config()
    _rebuild_historico_sinais()

    # Valida e loga estado do Redis logo no boot para facilitar diagnóstico
    rs = redis_status()
    if rs["status"] == "disabled":
        logger.warning(
            "REDIS_URL não configurada — cache desabilitado. "
            "Adicione REDIS_URL no Render para ativar cache distribuído."
        )
    elif rs["status"] == "connected":
        logger.info("Redis conectado e operacional.")
    else:
        logger.warning(f"Redis configurado mas indisponível (status={rs['status']}).")

    scheduler.add_job(
        run_scan,
        trigger=CronTrigger(day_of_week="mon-fri", hour="10-16", minute="0,30", timezone="America/Sao_Paulo"),
        id="scan_job",
        name="Scan Options every 30m during market hours",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        cleanup_old_signals,
        trigger=CronTrigger(hour=2, minute=0, timezone="America/Sao_Paulo"),
        id="cleanup_job",
        name="Cleanup old signals",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler iniciado")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="B3 Options Signals API", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    rs = redis_status()
    sched_running = scheduler.running if scheduler else False
    jobs = []
    if sched_running:
        jobs = [
            {"id": j.id, "next_run": str(j.next_run_time)}
            for j in scheduler.get_jobs()
        ]
    return {
        "status": "healthy",
        "data_source": "real",
        "last_scan": _last_scan_ts,
        "components": {
            "api": "ok",
            "market_data": "ok",
            "redis": rs["status"],
            "scheduler": "running" if sched_running else "stopped",
        },
        "redis": rs,
        "scheduler_jobs": jobs,
    }


@app.get("/signals")
def get_signals(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    tipo: str = Query(default=None),
    min_score: int = Query(default=0),
):
    """Busca sinais do Supabase com filtros server-side. Fallback para memória."""
    supabase = get_supabase()
    if not supabase:
        sinais = _last_scan_sinais
        if tipo:
            sinais = [s for s in sinais if s.get("tipo_sinal") == tipo]
        if min_score > 0:
            sinais = [s for s in sinais if s.get("score", 0) >= min_score]
        return {"data": sinais[offset:offset + limit], "count": len(sinais), "source": "memory"}

    try:
        query = (supabase.table("signals")
                 .select("*", count="exact")
                 .order("timestamp", desc=True))
        if tipo:
            query = query.eq("tipo_sinal", tipo)
        if min_score > 0:
            query = query.gte("score", min_score)
        res = query.range(offset, offset + limit - 1).execute()
        return {"data": res.data, "count": res.count, "source": "supabase"}
    except Exception as e:
        logger.error(f"Erro ao buscar sinais: {e}")
        return {"data": _last_scan_sinais[offset:offset + limit], "count": len(_last_scan_sinais), "source": "memory_fallback"}


@app.post("/signals/scan/{ticker}")
def scan_ticker(ticker: str = Path(pattern=r"^[A-Za-z0-9]{4,8}$")):
    ticker_sa = ticker.upper()
    if not ticker_sa.endswith(".SA"):
        ticker_sa += ".SA"
    nome = ATIVOS_B3.get(ticker_sa, ticker.upper())
    sinal = analisar_ativo(ticker_sa, nome, verbose=True)
    if not sinal:
        return {"sinal": None, "message": "Nenhum sinal detectado"}
    persist_signals([sinal])
    enviar_telegram(sinal)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_alert(sinal))
    except RuntimeError:
        pass
    return {"sinal": sinal}


@app.get("/signals/scan/{ticker}")
def scan_ticker_get(ticker: str = Path(pattern=r"^[A-Za-z0-9]{4,8}$")):
    return scan_ticker(ticker)


@app.post("/signals/scan")
def scan_batch(tickers: list[str]):
    """Scan em batch: aceita lista de tickers, paraleliza com 10 workers."""
    sinais = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        def do_scan(t: str):
            t_sa = t.upper() if t.upper().endswith(".SA") else t.upper() + ".SA"
            nome = ATIVOS_B3.get(t_sa, t.upper())
            return _scan_one(t_sa, nome)

        futures = {pool.submit(do_scan, t): t for t in tickers}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sinais.append(result)

    if sinais:
        persist_signals(sinais)
        for s in sinais:
            enviar_telegram(s)

    global _last_scan_sinais, _last_scan_ts
    if sinais:
        _last_scan_sinais = sinais
        _last_scan_ts = datetime.now(timezone.utc).isoformat()

    return {"data": sinais, "count": len(sinais), "message": f"{len(sinais)} sinal(is) encontrado(s)"}


@app.get("/signals/scan/stream")
async def scan_stream(tickers: str = Query(default="")):
    """SSE: envia eventos de progresso conforme cada ticker é analisado."""
    ticker_list = (
        [t.strip() for t in tickers.split(",") if t.strip()]
        if tickers else list(ATIVOS_B3.keys())
    )

    async def event_generator():
        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()
        total = len(ticker_list)
        sem = asyncio.Semaphore(10)

        async def scan_one_async(ticker: str):
            async with sem:
                t_sa = ticker.upper() if ticker.upper().endswith(".SA") else ticker.upper() + ".SA"
                nome = ATIVOS_B3.get(t_sa, ticker.upper())
                result = await loop.run_in_executor(None, _scan_one, t_sa, nome)
                await q.put((ticker, result))

        tasks = [asyncio.create_task(scan_one_async(t)) for t in ticker_list]
        sinais = []

        for _ in range(total):
            ticker, result = await q.get()
            completed = total - sum(1 for t in tasks if not t.done()) + 1
            event: dict = {
                "type": "progress",
                "ticker": ticker.replace(".SA", ""),
                "completed": completed,
                "total": total,
                "has_signal": result is not None,
            }
            if result:
                sinais.append(result)
                event["signal"] = result

            yield f"data: {json.dumps(event, default=str)}\n\n"

        await asyncio.gather(*tasks, return_exceptions=True)

        if sinais:
            persist_signals(sinais)
            for s in sinais:
                enviar_telegram(s)
            global _last_scan_sinais, _last_scan_ts
            _last_scan_sinais = sinais
            _last_scan_ts = datetime.now(timezone.utc).isoformat()

        yield f"data: {json.dumps({'type': 'done', 'count': len(sinais)}, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/signals/alerts/stream")
async def alerts_stream():
    """SSE: envia eventos proativos em tempo real (novos sinais de opções)."""
    q = asyncio.Queue()
    _alert_queues.append(q)

    async def event_generator():
        try:
            while True:
                sinal = await q.get()
                yield f"data: {json.dumps(sinal, default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if q in _alert_queues:
                _alert_queues.remove(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/signals/scan/all")
def scan_all():
    run_scan()
    return {"message": f"{len(_last_scan_sinais)} sinal(is) encontrado(s)", "data": _last_scan_sinais}


@app.post("/signals/scan/all-b3")
def scan_all_b3():
    """Varre TODO o universo B3 (centenas de tickers via brapi /available).
    Mais lento que /scan/all — use com moderação."""
    run_scan(all_b3=True)
    return {"message": f"{len(_last_scan_sinais)} sinal(is) encontrado(s)",
            "universe": "all-b3", "data": _last_scan_sinais}


@app.get("/signals/history")
def get_history(
    limit: int = Query(default=50, le=200),
    ticker: str = Query(default=None),
    tipo_sinal: str = Query(default=None),
):
    supabase = get_supabase()
    filtered = _last_scan_sinais
    if ticker:
        filtered = [s for s in filtered if s.get("ticker", "").upper() == ticker.upper()]
    if tipo_sinal:
        filtered = [s for s in filtered if s.get("tipo_sinal", "") == tipo_sinal.upper()]
    if not supabase:
        return {"data": filtered[:limit], "source": "memory"}
    try:
        query = supabase.table("signals").select("*").order("timestamp", desc=True)
        if ticker:
            query = query.eq("ticker", ticker.upper())
        if tipo_sinal:
            query = query.eq("tipo_sinal", tipo_sinal.upper())
        res = query.limit(limit).execute()
        return {"data": res.data, "source": "supabase"}
    except Exception as e:
        logger.error(f"Erro ao buscar histórico: {e}")
        return {"data": filtered[:limit], "source": "memory_fallback"}


@app.get("/signals/watchlist")
def get_watchlist(all_b3: bool = Query(default=False)):
    base = get_all_b3_assets() if all_b3 else ATIVOS_B3
    return {"watchlist": [t.replace(".SA", "") for t in base.keys()],
            "count": len(base),
            "universe": "all-b3" if all_b3 else "curated"}


@app.get("/signals/analytics/{ticker}")
def analytics(ticker: str):
    supabase = get_supabase()
    ticker_upper = ticker.upper().replace(".SA", "")
    if not supabase:
        raise HTTPException(status_code=503, detail="Supabase não configurado")
    try:
        res = (supabase.table("signals")
               .select("*")
               .eq("ticker", ticker_upper)
               .order("timestamp", desc=True)
               .limit(100)
               .execute())
        sinais = res.data
        calls = [s for s in sinais if s.get("tipo_sinal") == "CALL"]
        puts  = [s for s in sinais if s.get("tipo_sinal") == "PUT"]
        return {
            "ticker": ticker_upper,
            "total": len(sinais),
            "calls": len(calls),
            "puts": len(puts),
            "avg_score": round(sum(s.get("score", 0) for s in sinais) / len(sinais), 2) if sinais else 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/signals/performance")
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
        res = (supabase.table("signals")
               .select("ticker, tipo_sinal, score, score_ponderado, ponderado_passou, entrada_max, alvo1, alvo2, alvo_final, stop, timestamp, greeks")
               .gte("timestamp", cutoff)
               .order("timestamp", desc=True)
               .limit(2000)
               .execute())
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
        b["put"]  += 1 if r.get("tipo_sinal") == "PUT"  else 0
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
        "puts":  sum(1 for r in rows if r.get("tipo_sinal") == "PUT"),
        "ponderado_concordancia_pct": round(total_pond_passou / total * 100, 1),
        "avg_score_classico": round(sum(r.get("score") or 0 for r in rows) / total, 2),
        "avg_score_ponderado": round(
            sum(r["score_ponderado"] for r in rows if r.get("score_ponderado") is not None)
            / max(1, sum(1 for r in rows if r.get("score_ponderado") is not None)), 1
        ),
        "by_ticker": by_ticker_list,
    }


@app.get("/signals/strategies")
def get_strategies():
    return {"strategies": ["CALL OTM", "PUT OTM", "CALL ATM", "PUT ATM"]}


@app.get("/backtest/strategies")
def backtest_strategies():
    return {"strategies": ["momentum", "reversao", "breakout"]}


@app.post("/backtest/run")
def backtest_run(params: BacktestParams):
    from backend.services.backtest import rodar_backtest
    import numpy as np
    ticker_raw = params.ticker
    ticker = ticker_raw + ".SA"
    nome = ATIVOS_B3.get(ticker, ticker_raw)
    start = params.start_date
    end = params.end_date or datetime.now().strftime("%Y-%m-%d")

    sinais = rodar_backtest(ticker, nome, start, end)

    # Serialize pandas Timestamps
    for s in sinais:
        if "data_sinal" in s and hasattr(s["data_sinal"], "isoformat"):
            s["data_sinal"] = s["data_sinal"].isoformat()

    total = len(sinais)
    if total == 0:
        return {"sinais": 0, "metrics": None, "equity_curve": [], "data": []}

    wins = sum(1 for s in sinais if s.get("hit_alvo1"))
    win_rate = wins / total

    # Equity curve — 10% position sizing per trade
    equity = 10000.0
    equity_curve = [round(equity, 2)]
    trade_returns = []
    for s in sinais:
        if s.get("hit_alvo1"):
            r = s.get("max_return", 0) * 0.10
        elif s.get("hit_stop"):
            r = -0.03
        else:
            r = s.get("max_return", 0) * 0.05
        trade_returns.append(r)
        equity *= (1 + r)
        equity_curve.append(round(equity, 2))

    total_return_pct = (equity_curve[-1] / equity_curve[0] - 1) * 100

    peak = equity_curve[0]
    max_dd = 0.0
    for e in equity_curve:
        if e > peak:
            peak = e
        dd = (peak - e) / peak
        if dd > max_dd:
            max_dd = dd

    if len(trade_returns) > 1:
        mean_r = float(np.mean(trade_returns))
        std_r = float(np.std(trade_returns))
        sharpe = round(mean_r / std_r * (252 ** 0.5), 2) if std_r > 0 else 0.0
        
        # Sortino
        down_returns = [r for r in trade_returns if r < 0]
        std_down = float(np.std(down_returns)) if len(down_returns) > 1 else 0.0
        sortino = round(mean_r / std_down * (252 ** 0.5), 2) if std_down > 0 else 0.0
        
        # Calmar
        calmar = round(total_return_pct / 100 / max_dd, 2) if max_dd > 0 else 0.0
        
        # Expectancy ($) per trade based on 10k initial equity position sizing
        avg_win = float(np.mean([r for r in trade_returns if r > 0])) if any(r > 0 for r in trade_returns) else 0.0
        avg_loss = float(np.mean([r for r in trade_returns if r < 0])) if any(r < 0 for r in trade_returns) else 0.0
        expectancy_pct = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        expectancy_usd = round(expectancy_pct * 1000, 2) # Assume $1000 per trade average size
    else:
        sharpe = 0.0
        sortino = 0.0
        calmar = 0.0
        expectancy_usd = 0.0

    return {
        "sinais": total,
        "metrics": {
            "win_rate": round(win_rate * 100, 1),
            "total_return": round(total_return_pct, 1),
            "max_drawdown": round(max_dd * 100, 1),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar,
            "expectancy": expectancy_usd,
            "trades": total,
        },
        "equity_curve": equity_curve,
        "data": sinais,
    }


@app.get("/market")
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


@app.get("/market/opcoes")
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


@app.get("/market/opcoes/chain/{ticker}")
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


@app.get("/config/telegram")
def get_telegram():
    return {"token": bool(CONFIG.get("telegram_token")), "chat_id": bool(CONFIG.get("telegram_chat_id"))}


@app.post("/config/telegram")
def set_telegram(config: dict):
    token = config.get("token", "")
    chat_id = config.get("chat_id", "")
    CONFIG["telegram_token"] = token
    CONFIG["telegram_chat_id"] = chat_id
    _save_telegram_config(token, chat_id)
    return {"ok": True}

"""Endpoints de scan: batch, stream SSE, scan completo e ticker único.

Ordem das rotas importa: os caminhos literais (`/stream`, `/all`, `/all-b3`)
são declarados ANTES da rota paramétrica `/{ticker}`, senão esta última os
captura (o segmento de path casa com `{ticker}` antes da validação do padrão).
"""
import json
import asyncio
import logging

from fastapi import APIRouter, Query, Path
from fastapi.responses import StreamingResponse

from backend.core.config import ATIVOS_B3
from backend.services import signal_service
from backend.services.signal_service import analyse_ticker, persist_signals
from backend.services.telegram_service import notificar_lote

logger = logging.getLogger("b3_api")
router = APIRouter(tags=["Scan"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.post("/signals/scan")
def scan_batch(tickers: list[str]):
    """Scan em batch: aceita lista de tickers, paraleliza com 10 workers."""
    sinais = signal_service.scan_batch(tickers)
    return {"data": sinais, "count": len(sinais), "message": f"{len(sinais)} sinal(is) encontrado(s)"}


@router.get("/signals/scan/stream")
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
                result = await loop.run_in_executor(None, analyse_ticker, t_sa, nome)
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
            notificar_lote(sinais)
            signal_service.update_last_scan(sinais)

        yield f"data: {json.dumps({'type': 'done', 'count': len(sinais)}, default=str)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.get("/signals/alerts/stream")
async def alerts_stream():
    """SSE: envia eventos proativos em tempo real (novos sinais de opções)."""
    q = signal_service.register_alert_queue()

    async def event_generator():
        try:
            while True:
                sinal = await q.get()
                yield f"data: {json.dumps(sinal, default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            signal_service.unregister_alert_queue(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/signals/scan/all")
def scan_all():
    signal_service.run_scan(universe="curado")
    sinais = signal_service.last_scan_signals()
    return {"message": f"{len(sinais)} sinal(is) encontrado(s)", "data": sinais}


@router.post("/signals/scan/all-b3")
def scan_all_b3():
    """Varre o universo LÍQUIDO da B3 (curados + B3 + brapi, pré-filtrados por
    volume e limitados a top_n). Mais lento que /scan/all — use com moderação."""
    signal_service.run_scan(universe="liquido")
    sinais = signal_service.last_scan_signals()
    return {"message": f"{len(sinais)} sinal(is) encontrado(s)",
            "universe": "all-b3", "data": sinais}


@router.post("/signals/scan/{ticker}")
def scan_ticker(ticker: str = Path(pattern=r"^[A-Za-z0-9]{4,8}$")):
    sinal = signal_service.scan_single(ticker)
    if not sinal:
        return {"sinal": None, "message": "Nenhum sinal detectado"}
    return {"sinal": sinal}


@router.get("/signals/scan/{ticker}")
def scan_ticker_get(ticker: str = Path(pattern=r"^[A-Za-z0-9]{4,8}$")):
    return scan_ticker(ticker)

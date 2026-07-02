"""Ponto de entrada da API FastAPI.

Responsável apenas por compor a aplicação: ciclo de vida (lifespan),
middlewares (CORS, rate limit), métricas e registro dos routers. Toda a lógica
de negócio vive em backend/services e os endpoints em backend/api/routers.
"""
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from backend.api.routers import backtest, config, health, market, scan, signals
from backend.core.cache import redis_status
from backend.core.logging_config import configure_logging
from backend.services import scheduler, signal_service
from backend.services.event_service import registrar_copom_datas
from backend.services.telegram_service import load_telegram_config

load_dotenv()

configure_logging(level=logging.INFO)
logger = logging.getLogger("b3_api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import asyncio
    main_loop = asyncio.get_running_loop()
    signal_service.set_main_loop(main_loop)

    load_telegram_config()
    signal_service.rebuild_historico_sinais()

    # Fase 3: cadastra calendário Copom (fail-safe — não pode derrubar o boot)
    try:
        registrar_copom_datas(ano=2026)
    except Exception as e:
        logger.warning(f"Falha ao registrar calendário Copom no boot: {e}")

    # Valida e loga estado do Redis logo no boot para facilitar diagnóstico
    rs = redis_status()
    if rs["status"] == "disabled":
        logger.info(
            "REDIS_URL não configurada — usando cache TTL em memória (fallback). "
            "Para cache distribuído entre instâncias, adicione REDIS_URL no Render."
        )
    elif rs["status"] == "connected":
        logger.info("Redis conectado e operacional.")
    else:
        logger.warning(
            f"Redis configurado mas indisponível (status={rs['status']}) — "
            "caindo para cache TTL em memória."
        )

    scheduler.start()
    yield
    scheduler.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(title="B3 Options Signals API", lifespan=lifespan)

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    app.mount("/metrics", make_asgi_app())

    allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(signals.router)
    app.include_router(scan.router)
    app.include_router(backtest.router)
    app.include_router(market.router)
    app.include_router(config.router)
    return app


app = create_app()

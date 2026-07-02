"""Agendador de jobs (APScheduler).

Define os jobs de scan periódico e de limpeza. O objeto ``scheduler`` é
compartilhado com o endpoint /health para reportar estado e próximas execuções.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.services.iv_history_service import coletar_iv_diaria
from backend.services.liquidity_service import coletar_liquidity_diaria
from backend.services.signal_service import cleanup_old_signals, run_scan

logger = logging.getLogger("b3_api")

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")


def start():
    """Registra os jobs e inicia o scheduler."""
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
    scheduler.add_job(
        coletar_iv_diaria,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=0, timezone="America/Sao_Paulo"),
        id="iv_history_job",
        name="Coleta diaria de IV ATM (pos-fechamento)",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.add_job(
        coletar_liquidity_diaria,
        trigger=CronTrigger(day_of_week="mon-fri", hour=18, minute=0, timezone="America/Sao_Paulo"),
        id="liquidity_job",
        name="Coleta diaria de OI/bid-ask/VXBR (pos-fechamento)",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler iniciado")


def shutdown():
    scheduler.shutdown(wait=False)

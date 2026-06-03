from fastapi import APIRouter

from backend.core.cache import redis_status
from backend.services import signal_service
from backend.services.scheduler import scheduler

router = APIRouter(tags=["Health"])


@router.get("/health")
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
        "last_scan": signal_service.last_scan_ts(),
        "components": {
            "api": "ok",
            "market_data": "ok",
            "redis": rs["status"],
            "scheduler": "running" if sched_running else "stopped",
        },
        "redis": rs,
        "scheduler_jobs": jobs,
    }

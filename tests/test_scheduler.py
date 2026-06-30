"""Teste de wiring do scheduler — confirma que o job de IV está registrado."""
from backend.services import scheduler as sch


def test_start_registra_job_iv_history(monkeypatch):
    monkeypatch.setattr(sch.scheduler, "start", lambda: None)
    ids_antes = {j.id for j in sch.scheduler.get_jobs()}
    sch.start()
    ids_depois = {j.id for j in sch.scheduler.get_jobs()}
    assert "iv_history_job" in ids_depois - ids_antes or "iv_history_job" in ids_depois


def test_start_registra_job_cleanup(monkeypatch):
    """Confirma que cleanup_old_signals esta agendado (job cleanup_job)."""
    monkeypatch.setattr(sch.scheduler, "start", lambda: None)
    ids_antes = {j.id for j in sch.scheduler.get_jobs()}
    sch.start()
    ids_depois = {j.id for j in sch.scheduler.get_jobs()}
    assert "cleanup_job" in ids_depois - ids_antes or "cleanup_job" in ids_depois


def test_start_registra_job_scan(monkeypatch):
    """Confirma que run_scan esta agendado (job scan_job)."""
    monkeypatch.setattr(sch.scheduler, "start", lambda: None)
    ids_antes = {j.id for j in sch.scheduler.get_jobs()}
    sch.start()
    ids_depois = {j.id for j in sch.scheduler.get_jobs()}
    assert "scan_job" in ids_depois - ids_antes or "scan_job" in ids_depois

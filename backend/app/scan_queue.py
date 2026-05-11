import logging
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.scanner import create_scan_job, scan


logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=get_settings().max_concurrent_scans)


def submit_scan(user_id: int, started_by: int | None = None) -> int:
    job_id = create_scan_job(user_id, started_by, status="queued")
    _executor.submit(_run_scan, user_id, started_by, job_id)
    return job_id


def _run_scan(user_id: int, started_by: int | None, job_id: int) -> None:
    try:
        scan(user_id=user_id, started_by=started_by, job_id=job_id)
    except Exception:
        logger.exception("Queued scan job %s failed", job_id)

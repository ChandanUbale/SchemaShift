"""
jobs.py — In-process job runner and progress store.

Design notes:
- Jobs run as FastAPI BackgroundTasks (in-process, same worker).
- State is persisted to SQLite so the UI can poll or receive SSE updates.
- No Celery / Redis — the demo scale (~10k rows) does not require a distributed queue.
- Each job has: job_id (UUID), status, progress_pct, error.

Statuses: PENDING → RUNNING → DONE | FAILED
"""

import uuid
from enum import Enum
from typing import Callable, Any

from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Job status enum
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# In-memory progress cache (for SSE; SQLite is the persistent store)
# ---------------------------------------------------------------------------

_progress_cache: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_job(db: Session, job_type: str, connection_id: int | None = None) -> str:
    """
    Persist a new job record in SQLite and return its job_id.

    TODO: Insert a MigrationJob row (or ProfilingJob) into the DB.
    """
    job_id = str(uuid.uuid4())
    _progress_cache[job_id] = {
        "job_id": job_id,
        "job_type": job_type,
        "status": JobStatus.PENDING,
        "progress_pct": 0,
        "error": None,
    }
    # TODO: db.add(...); db.commit()
    return job_id


def update_progress(job_id: str, progress_pct: int, status: JobStatus = JobStatus.RUNNING, error: str | None = None) -> None:
    """
    Update in-memory cache (SSE reads this) and persist to SQLite.

    TODO: db.query(MigrationJob).filter_by(job_id=job_id).update(...)
    """
    if job_id in _progress_cache:
        _progress_cache[job_id].update({
            "status": status,
            "progress_pct": progress_pct,
            "error": error,
        })


def get_job_status(job_id: str) -> dict | None:
    """Return current job state from the in-memory cache."""
    return _progress_cache.get(job_id)


def run_job_in_background(job_id: str, fn: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Wrap a callable to update job status before/after execution.
    Called from a FastAPI BackgroundTask.

    TODO: wrap fn(), catch exceptions, call update_progress accordingly.
    """
    update_progress(job_id, 0, JobStatus.RUNNING)
    try:
        fn(*args, **kwargs)
        update_progress(job_id, 100, JobStatus.DONE)
    except Exception as exc:
        update_progress(job_id, 0, JobStatus.FAILED, error=str(exc))
        raise

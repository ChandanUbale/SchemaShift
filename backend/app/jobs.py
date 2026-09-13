"""
jobs.py — In-process job runner and progress store.

Design notes:
- Jobs run as FastAPI BackgroundTasks (in-process, same worker).
- State is persisted to SQLite so the UI can poll or receive SSE updates.
- No Celery / Redis — the demo scale (~10k rows) does not require a distributed queue.
- Each job has: job_id (UUID), status, progress_pct, error.

Statuses: PENDING → RUNNING → DONE | FAILED
"""

import asyncio
import json
import uuid
from enum import Enum
from typing import AsyncGenerator, Callable, Any

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
    """
    update_progress(job_id, 0, JobStatus.RUNNING)
    try:
        fn(*args, **kwargs)
        update_progress(job_id, 100, JobStatus.DONE)
    except Exception as exc:
        update_progress(job_id, 0, JobStatus.FAILED, error=str(exc))
        raise


# ---------------------------------------------------------------------------
# SSE generator — streams job progress to the browser
# ---------------------------------------------------------------------------

_TERMINAL_STATUSES = {JobStatus.DONE, JobStatus.FAILED}
_POLL_INTERVAL_S = 0.5


async def sse_generator(job_id: str) -> AsyncGenerator[str, None]:
    """
    Async generator for Server-Sent Events.

    Usage in a router endpoint::

        from fastapi.responses import StreamingResponse
        from app.jobs import sse_generator

        @router.get("/{job_id}/stream")
        async def stream_progress(job_id: str):
            return StreamingResponse(
                sse_generator(job_id),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

    Protocol:
    - Emits ``data: <json>\\n\\n`` events with the full job snapshot.
    - Emits a final ``event: done\\ndata: {}\\n\\n`` when the job terminates.
    - Emits ``event: error\\ndata: <json>\\n\\n`` if the job_id is unknown.
    - Polls the in-memory cache every ``_POLL_INTERVAL_S`` seconds.
    """
    if job_id not in _progress_cache:
        payload = json.dumps({"detail": f"job {job_id!r} not found"})
        yield f"event: error\ndata: {payload}\n\n"
        return

    last_pct: int = -1

    while True:
        snapshot = _progress_cache.get(job_id)

        if snapshot is None:
            # Job was evicted; treat as unknown.
            payload = json.dumps({"detail": f"job {job_id!r} disappeared"})
            yield f"event: error\ndata: {payload}\n\n"
            return

        current_pct = snapshot["progress_pct"]

        # Only emit when progress actually changes (reduces noise).
        if current_pct != last_pct:
            last_pct = current_pct
            data = json.dumps({
                "job_id": snapshot["job_id"],
                "status": snapshot["status"],
                "progress_pct": snapshot["progress_pct"],
                "error": snapshot["error"],
            })
            yield f"data: {data}\n\n"

        if snapshot["status"] in _TERMINAL_STATUSES:
            yield "event: done\ndata: {}\n\n"
            return

        await asyncio.sleep(_POLL_INTERVAL_S)

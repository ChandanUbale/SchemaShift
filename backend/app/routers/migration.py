"""
routers/migration.py — Dry run, execute, progress SSE, approval, and cleanup.

Hard write boundary:
  - dry_run   → ZERO target writes
  - execute   → writes ONLY after user approval + plan_id
  - cleanup   → drops this job's target tables/collections
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.migration import (
    DryRunRequest,
    DryRunResult,
    MigrationApproveRequest,
    MigrationProgressResponse,
    CleanupRequest,
)

router = APIRouter()


@router.post("/dry-run", response_model=DryRunResult, status_code=202)
def start_dry_run(payload: DryRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Sample the source, run the transformer, collect issues — NO target writes.
    Returns a job_id; client polls /migration/{job_id}/status.

    TODO:
    - create_job(db, "dry_run")
    - background_tasks.add_task(dry_runner.run, job_id, payload)
    """
    raise NotImplementedError("TODO: implement start_dry_run")


@router.post("/execute", status_code=202)
def execute_migration(
    payload: MigrationApproveRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start the real migration. Requires approved=True and a valid plan_id.
    Writes in batches (BATCH_SIZE). Retries failed batches a fixed number of times.
    Extra confirmation is enforced by the caller when profiling risk is High.

    TODO:
    - Validate plan_id exists and approved=True
    - create_job(db, "migration")
    - background_tasks.add_task(batch_executor.run, job_id, payload)
    """
    raise NotImplementedError("TODO: implement execute_migration")


@router.get("/{job_id}/status", response_model=MigrationProgressResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll-based fallback. Returns current job progress from SQLite."""
    raise NotImplementedError("TODO: implement get_job_status")


@router.get("/{job_id}/stream")
async def stream_progress(job_id: str):
    """
    Server-Sent Events stream for live progress updates.
    Delegates to jobs.sse_generator which polls the in-memory progress cache.
    """
    from app.jobs import sse_generator  # local import to avoid circular import at module level

    return StreamingResponse(
        sse_generator(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/cleanup", status_code=204)
def cleanup_target(payload: CleanupRequest, db: Session = Depends(get_db)):
    """
    Drop this job's migrated tables/collections from the target.
    No automatic rollback — explicit user action only.

    TODO: call writer_factory.get_writer(target_type).cleanup(job_id)
    """
    raise NotImplementedError("TODO: implement cleanup_target")

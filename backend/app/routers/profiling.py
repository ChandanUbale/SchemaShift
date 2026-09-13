"""routers/profiling.py — Column/collection profiling endpoints (read-only)."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.profiling import ProfilingRequest, ProfilingResult

router = APIRouter()


@router.post("/", status_code=202)
def start_profiling(
    payload: ProfilingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start a profiling job as a background task.
    Returns immediately with a job_id; client polls /profiling/{job_id}.

    Profiling reads source only — zero target writes.
    Sampling: up to PROFILE_SAMPLE_SIZE rows (default 10k).

    TODO:
    - create_job(db, "profiling")
    - background_tasks.add_task(run_profiling_job, job_id, payload)
    - return {"job_id": job_id}
    """
    raise NotImplementedError("TODO: implement start_profiling")


@router.get("/{job_id}", response_model=ProfilingResult)
def get_profiling_result(job_id: str, db: Session = Depends(get_db)):
    """Return the current profiling job status and results."""
    raise NotImplementedError("TODO: implement get_profiling_result")

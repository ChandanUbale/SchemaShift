"""routers/validation.py — Post-migration validation and final report endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.validation import ValidationRequest, ValidationResult, FinalReport

router = APIRouter()


@router.post("/", status_code=202)
def start_validation(
    payload: ValidationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Start validation as a background task. Reads source + target — no writes.
    Runs: count validator → aggregate validator → checksum validator → relationship validator.

    TODO:
    - create_job(db, "validation")
    - background_tasks.add_task(run_validation, job_id, payload)
    """
    raise NotImplementedError("TODO: implement start_validation")


@router.get("/{migration_job_id}/result", response_model=ValidationResult)
def get_validation_result(migration_job_id: int, db: Session = Depends(get_db)):
    """Return the validation result for a completed migration job."""
    raise NotImplementedError("TODO: implement get_validation_result")


@router.get("/{migration_job_id}/report", response_model=FinalReport)
def get_final_report(migration_job_id: int, db: Session = Depends(get_db)):
    """
    Return the full final report combining:
    1. Profiling risk (data quality before migration)
    2. Migration execution stats
    3. Validation correctness (after migration)

    TODO: compose from ProfilingJob + MigrationJob + ValidationReport DB records.
    """
    raise NotImplementedError("TODO: implement get_final_report")


@router.get("/{migration_job_id}/report.html")
def download_html_report(migration_job_id: int, db: Session = Depends(get_db)):
    """Serve the generated HTML report file for download."""
    raise NotImplementedError("TODO: implement download_html_report")

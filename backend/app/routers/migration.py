"""
routers/migration.py — Dry run, execute, progress SSE, approval, and cleanup.

Hard write boundary:
  - dry_run   → ZERO target writes
  - execute   → writes ONLY after user approval + plan_id
  - cleanup   → drops this job's target tables/collections
"""

from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.jobs import JobStatus, _progress_cache, create_job, get_job_status, update_progress
from app.models.connection import Connection
from app.models.migration import MigrationJob
from app.schemas.migration import (
    CleanupRequest,
    DryRunRequest,
    DryRunResult,
    MigrationApproveRequest,
    MigrationProgressResponse,
)
from app.services.discovery.connector_factory import ConnectorFactory
from app.services.migration.dry_runner import DryRunner, default_plan
from app.services.migration.transformer import Transformer

router = APIRouter()

_SHOP_RELATIONAL = ("customers", "orders", "order_items")
_SHOP_DOCUMENT = ("customers",)


def _open_connector(conn_model: Connection):
    if conn_model.source_type == "mysql":
        return ConnectorFactory.get_connector("mysql", conn_model.dsn)
    if conn_model.source_type == "mongodb":
        parsed = urlparse(conn_model.dsn)
        db_name = parsed.path.lstrip("/")
        return ConnectorFactory.get_connector("mongodb", conn_model.dsn, db_name=db_name)
    raise ValueError(f"Unsupported source_type: {conn_model.source_type}")


def _entity_names(conn_model: Connection, direction: str) -> list[str]:
    schema = conn_model.schema_json or {}
    names = [entity["name"] for entity in schema.get("entities") or [] if entity.get("name")]
    if names:
        return names
    if direction == "document_to_relational":
        return list(_SHOP_DOCUMENT)
    return list(_SHOP_RELATIONAL)


def _store_issues(job_id: str, issues: list[dict], sample_size: int) -> None:
    if job_id in _progress_cache:
        _progress_cache[job_id]["issues"] = issues
        _progress_cache[job_id]["sample_size"] = sample_size
        _progress_cache[job_id]["audit_log"] = issues


def run_dry_run(job_id: str, source_connection_id: int, plan_id: str) -> None:
    """Background: sample source only, transform in memory, persist issues. No writers."""
    db = SessionLocal()
    try:
        update_progress(job_id, 0, JobStatus.RUNNING)
        conn_model = db.query(Connection).filter(Connection.id == source_connection_id).first()
        if not conn_model:
            raise ValueError(f"Connection {source_connection_id} not found")

        plan = default_plan(conn_model.source_type, plan_id)
        connector = _open_connector(conn_model)
        connector.connect()
        try:
            sample_n = settings.profile_sample_size
            tables: dict[str, list] = {}
            for name in _entity_names(conn_model, plan["direction"]):
                try:
                    tables[name] = connector.fetch_sample(name, sample_n)
                except Exception:
                    tables[name] = []
        finally:
            connector.disconnect()

        update_progress(job_id, 50, JobStatus.RUNNING)
        if plan["direction"] == "document_to_relational":
            root = next(iter(tables), "customers")
            source_data = tables.get(root) or tables.get("customers") or []
            sample_size = len(source_data)
        else:
            source_data = tables
            sample_size = sum(len(rows) for rows in tables.values())

        issues = DryRunner.run(source_data, Transformer(plan), plan)
        _store_issues(job_id, issues, sample_size)

        job_row = db.query(MigrationJob).filter(MigrationJob.job_id == job_id).first()
        if job_row:
            job_row.status = JobStatus.DONE.value
            job_row.progress_pct = 100
            job_row.audit_log = issues
            job_row.completed_at = datetime.utcnow()
            db.commit()

        update_progress(job_id, 100, JobStatus.DONE)
    except Exception as exc:
        update_progress(job_id, 0, JobStatus.FAILED, error=str(exc))
        job_row = db.query(MigrationJob).filter(MigrationJob.job_id == job_id).first()
        if job_row:
            job_row.status = JobStatus.FAILED.value
            job_row.error = str(exc)
            db.commit()
        raise
    finally:
        db.close()


@router.post("/dry-run", response_model=DryRunResult, status_code=202)
def start_dry_run(payload: DryRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Sample the source, run the transformer, collect issues — NO target writes.
    Returns a job_id; client polls /migration/{job_id}/status then /dry-run.
    """
    conn_model = db.query(Connection).filter(Connection.id == payload.source_connection_id).first()
    if not conn_model:
        raise HTTPException(status_code=404, detail="Connection not found")

    job_id = create_job(db, "dry_run", connection_id=payload.source_connection_id)
    db.add(MigrationJob(
        job_id=job_id,
        source_connection_id=payload.source_connection_id,
        target_connection_id=payload.source_connection_id,
        plan_id=payload.plan_id,
        is_dry_run=True,
        status=JobStatus.PENDING.value,
        audit_log=[],
    ))
    db.commit()
    _store_issues(job_id, [], 0)
    background_tasks.add_task(run_dry_run, job_id, payload.source_connection_id, payload.plan_id)
    return DryRunResult(job_id=job_id, issues=[], total_issues=0, sample_size=0)


@router.get("/{job_id}/dry-run", response_model=DryRunResult)
def get_dry_run_result(job_id: str, db: Session = Depends(get_db)):
    """Return issues collected by a dry-run job (from cache or MigrationJob.audit_log)."""
    cache = get_job_status(job_id)
    job_row = db.query(MigrationJob).filter(MigrationJob.job_id == job_id).first()
    if not cache and not job_row:
        raise HTTPException(status_code=404, detail="Dry-run job not found")

    issues = (cache or {}).get("issues")
    if issues is None and job_row is not None:
        issues = job_row.audit_log or []
    issues = issues or []
    sample_size = int((cache or {}).get("sample_size") or 0)
    return DryRunResult(
        job_id=job_id,
        issues=issues,
        total_issues=len(issues),
        sample_size=sample_size,
    )


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
def read_job_status(job_id: str, db: Session = Depends(get_db)):
    """Poll-based fallback. Returns current job progress from cache or SQLite."""
    cache = get_job_status(job_id)
    job_row = db.query(MigrationJob).filter(MigrationJob.job_id == job_id).first()
    if not cache and not job_row:
        raise HTTPException(status_code=404, detail="Job not found")

    status = (cache or {}).get("status") or (job_row.status if job_row else "unknown")
    pct = (cache or {}).get("progress_pct")
    if pct is None:
        pct = job_row.progress_pct if job_row else 0
    return MigrationProgressResponse(
        job_id=job_id,
        status=str(status),
        progress_pct=float(pct or 0),
        batches_done=job_row.batches_done if job_row else 0,
        batches_total=job_row.batches_total if job_row else None,
        error=(cache or {}).get("error") if cache else (job_row.error if job_row else None),
    )


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

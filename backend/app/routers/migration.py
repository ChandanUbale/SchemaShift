"""
routers/migration.py — Dry run, execute, progress SSE, approval, and cleanup.

Hard write boundary:
  - dry_run   → ZERO target writes
    - execute   → writes ONLY after user approval + successful dry-run
  - cleanup   → drops this job's target tables/collections
"""

from datetime import datetime
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.jobs import JobStatus, _progress_cache, create_job, get_job_status, status_text, update_progress
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
from app.services.migration.batch_executor import BatchExecutor
from app.services.migration.cleanup import (
    cleanup_entry,
    entities_from_audit,
    require_cleanup_allowed,
    restore_writer_entities_from_audit,
)
from app.services.migration.dry_runner import DryRunner
from app.services.migration.execute_gate import (
    apply_target_collection,
    require_plan_id,
    require_successful_dry_run,
)
from app.services.migration.plan_builder import (
    build_plan,
    collections_to_read,
    schema_from_connector,
    select_schema_entities,
)
from app.services.migration.safety import assert_distinct_targets
from app.services.migration.transformer import Transformer
from app.services.migration.writer_factory import WriterFactory

router = APIRouter()

def _open_connector(conn_model: Connection):
    if conn_model.source_type == "mysql":
        return ConnectorFactory.get_connector("mysql", conn_model.dsn)
    if conn_model.source_type == "mongodb":
        parsed = urlparse(conn_model.dsn)
        db_name = parsed.path.lstrip("/")
        return ConnectorFactory.get_connector("mongodb", conn_model.dsn, db_name=db_name)
    raise ValueError(f"Unsupported source_type: {conn_model.source_type}")


def _open_writer(target_type: str, dsn: str):
    if target_type == "mongodb":
        parsed = urlparse(dsn)
        db_name = parsed.path.lstrip("/").split("?")[0]
        if not db_name:
            raise ValueError("MongoDB target connection string must include a database name.")
        return WriterFactory.get_writer("mongodb", dsn, db_name=db_name)
    return WriterFactory.get_writer("mysql", dsn)


def _database_name(conn_model: Connection) -> str:
    parsed = urlparse(conn_model.dsn.replace("mysql+pymysql", "mysql"))
    return parsed.path.lstrip("/").split("?")[0]


def _ensure_schema(conn_model: Connection, connector, db: Session) -> dict:
    schema = conn_model.schema_json or {}
    if schema.get("entities"):
        return schema
    schema = schema_from_connector(connector, conn_model.source_type, _database_name(conn_model))
    conn_model.schema_json = schema
    db.commit()
    return schema


def _entity_names(conn_model: Connection, plan: dict) -> list[str]:
    names = collections_to_read(plan)
    if names:
        return names
    schema = conn_model.schema_json or {}
    names = [entity["name"] for entity in schema.get("entities") or [] if entity.get("name")]
    if names:
        return names
    raise ValueError("No source entities are available in the discovered schema.")


def _store_issues(job_id: str, issues: list[dict], sample_size: int) -> None:
    if job_id in _progress_cache:
        _progress_cache[job_id]["issues"] = issues
        _progress_cache[job_id]["sample_size"] = sample_size
        _progress_cache[job_id]["audit_log"] = issues


def _latest_dry_run(db: Session, plan_id: str) -> MigrationJob | None:
    return (
        db.query(MigrationJob)
        .filter(
            MigrationJob.plan_id == plan_id,
            MigrationJob.is_dry_run.is_(True),
            MigrationJob.status == JobStatus.DONE.value,
        )
        .order_by(MigrationJob.id.desc())
        .first()
    )


def run_dry_run(job_id: str, source_connection_id: int, plan_id: str, entity_names: list[str] | None = None) -> None:
    """Background: sample source only, transform in memory, persist issues. No writers."""
    db = SessionLocal()
    try:
        update_progress(job_id, 0, JobStatus.RUNNING)
        conn_model = db.query(Connection).filter(Connection.id == source_connection_id).first()
        if not conn_model:
            raise ValueError(f"Connection {source_connection_id} not found")

        connector = _open_connector(conn_model)
        connector.connect()
        try:
            schema = _ensure_schema(conn_model, connector, db)
            schema = select_schema_entities(schema, entity_names)
            target_type = "mysql" if conn_model.source_type == "mongodb" else "mongodb"
            plan = build_plan(schema, conn_model.source_type, target_type, plan_id)
            sample_n = settings.dry_run_sample_size
            tables: dict[str, list] = {}
            for name in _entity_names(conn_model, plan):
                try:
                    tables[name] = connector.fetch_sample(name, sample_n)
                except Exception:
                    tables[name] = []
        finally:
            connector.disconnect()

        update_progress(job_id, 50, JobStatus.RUNNING)
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


def run_migration_job(
    job_id: str,
    source_connection_id: int,
    target_connection_id: int,
    plan: dict,
) -> None:
    """Background: the only path that is allowed to call writer.write_batch()."""
    db = SessionLocal()
    connector = None
    try:
        update_progress(job_id, 0, JobStatus.RUNNING)
        source = db.query(Connection).filter(Connection.id == source_connection_id).first()
        target = db.query(Connection).filter(Connection.id == target_connection_id).first()
        if not source or not target:
            raise ValueError("Connection not found")

        connector = _open_connector(source)
        connector.connect()
        writer = _open_writer(plan.get("target_type") or "mongodb", target.dsn)
        result = BatchExecutor.run(
            job_id,
            connector,
            writer,
            Transformer(plan),
            plan,
            batch_size=settings.batch_size,
        )
        failed = int(result.get("batches_failed") or 0)
        job_row = db.query(MigrationJob).filter(MigrationJob.job_id == job_id).first()
        if job_row:
            job_row.audit_log = result.get("audit_log") or []
            job_row.batches_total = result.get("batches_total")
            job_row.batches_done = max((result.get("batches_total") or 0) - failed, 0)
            job_row.progress_pct = 100
            job_row.status = JobStatus.FAILED.value if failed else JobStatus.DONE.value
            job_row.error = ((get_job_status(job_id) or {}).get("error") or f"{failed} batch(es) failed") if failed else None
            job_row.completed_at = datetime.utcnow()
            db.commit()
    except Exception as exc:
        update_progress(job_id, 0, JobStatus.FAILED, error=str(exc))
        job_row = db.query(MigrationJob).filter(MigrationJob.job_id == job_id).first()
        if job_row:
            job_row.status = JobStatus.FAILED.value
            job_row.error = str(exc)
            db.commit()
        raise
    finally:
        if connector is not None:
            try:
                connector.disconnect()
            except Exception:
                pass
        db.close()


@router.post("/dry-run", response_model=DryRunResult, status_code=202)
def start_dry_run(payload: DryRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Sample the source, run the transformer, collect issues — NO target writes.
    Creates a migration plan from the discovered schema and returns its plan_id with the job_id.
    """
    conn_model = db.query(Connection).filter(Connection.id == payload.source_connection_id).first()
    if not conn_model:
        raise HTTPException(status_code=404, detail="Connection not found")

    plan_id = str(uuid4())
    job_id = create_job(db, "dry_run", connection_id=payload.source_connection_id)
    db.add(MigrationJob(
        job_id=job_id,
        source_connection_id=payload.source_connection_id,
        target_connection_id=payload.source_connection_id,
        plan_id=plan_id,
        is_dry_run=True,
        status=JobStatus.PENDING.value,
        audit_log=[],
    ))
    db.commit()
    _store_issues(job_id, [], 0)
    background_tasks.add_task(
        run_dry_run,
        job_id,
        payload.source_connection_id,
        plan_id,
        payload.entity_names,
    )
    return DryRunResult(job_id=job_id, plan_id=plan_id, issues=[], total_issues=0, sample_size=0)


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
        plan_id=job_row.plan_id if job_row else None,
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
    Start the real migration. POST is the user's approval.
    Writes only after dry-run succeeded and source/target safety checks pass.
    """
    try:
        require_plan_id(payload.plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    source = db.query(Connection).filter(Connection.id == payload.source_connection_id).first()
    target = db.query(Connection).filter(Connection.id == payload.target_connection_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Connection not found")
    expected_target_type = "mysql" if source.source_type == "mongodb" else "mongodb"
    if target.source_type != expected_target_type:
        raise HTTPException(
            status_code=400,
            detail=f"Target engine is fixed to {expected_target_type} for a {source.source_type} source.",
        )

    try:
        require_successful_dry_run(_latest_dry_run(db, payload.plan_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    assert_distinct_targets(source.dsn, target.dsn, payload.in_place_optimisation)

    schema = source.schema_json or {}
    if not schema.get("entities"):
        probe = _open_connector(source)
        probe.connect()
        try:
            schema = _ensure_schema(source, probe, db)
        finally:
            probe.disconnect()
    target_type = expected_target_type
    try:
        schema = select_schema_entities(schema, payload.entity_names)
        plan = build_plan(schema, source.source_type, target_type, payload.plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        plan = apply_target_collection(plan, payload.target_collection_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = create_job(db, "migration", connection_id=payload.source_connection_id)
    db.add(MigrationJob(
        job_id=job_id,
        source_connection_id=payload.source_connection_id,
        target_connection_id=payload.target_connection_id,
        plan_id=payload.plan_id,
        is_dry_run=False,
        approved=True,
        status=JobStatus.PENDING.value,
        audit_log=[],
    ))
    db.commit()
    background_tasks.add_task(
        run_migration_job,
        job_id,
        payload.source_connection_id,
        payload.target_connection_id,
        plan,
    )
    return {"job_id": job_id}


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
        status=status_text(status),
        progress_pct=float(pct or 0),
        batches_done=job_row.batches_done if job_row else 0,
        batches_total=job_row.batches_total if job_row else None,
        error=(cache or {}).get("error") if cache else (job_row.error if job_row else None),
        audit_log=(cache or {}).get("audit_log") or (job_row.audit_log if job_row else []) or [],
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
    No automatic rollback — explicit user action only. Never touches the source.
    """
    job = db.query(MigrationJob).filter(MigrationJob.job_id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    try:
        require_cleanup_allowed(job, payload.target_connection_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    target = db.query(Connection).filter(Connection.id == payload.target_connection_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Connection not found")

    writer = _open_writer(target.source_type, target.dsn)
    entities = entities_from_audit(job.audit_log, target.source_type)
    restore_writer_entities_from_audit(writer, entities)
    writer.cleanup(payload.job_id)

    log = list(job.audit_log or [])
    log.append(cleanup_entry())
    job.audit_log = log
    db.commit()

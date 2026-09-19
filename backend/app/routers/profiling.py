"""routers/profiling.py — Column/collection profiling endpoints (read-only)."""

from urllib.parse import urlparse
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.jobs import create_job, update_progress, get_job_status, JobStatus
from app.models.connection import Connection
from app.models.profiling import ProfilingJob
from app.schemas.profiling import ProfilingRequest, ProfilingResult
from app.services.discovery.connector_factory import ConnectorFactory
from app.services.profiling.column_profiler import ColumnProfiler
from app.services.profiling.quality_checker import QualityChecker
from app.services.profiling.volume_estimator import VolumeEstimator

router = APIRouter()


def run_profiling(job_id: str, connection_id: int, sample_size: int | None) -> None:
    """
    Background task that runs the full profiling pipeline.
    Opens its own DB session since it runs in a background thread.
    """
    db = SessionLocal()
    try:
        update_progress(job_id, 0, JobStatus.RUNNING)

        # Load connection
        conn_model = db.query(Connection).filter(Connection.id == connection_id).first()
        if not conn_model:
            raise ValueError(f"Connection {connection_id} not found")

        # Build connector
        if conn_model.source_type == "mysql":
            connector = ConnectorFactory.get_connector("mysql", conn_model.dsn)
        elif conn_model.source_type == "mongodb":
            parsed = urlparse(conn_model.dsn)
            db_name = parsed.path.lstrip("/")
            connector = ConnectorFactory.get_connector("mongodb", conn_model.dsn, db_name=db_name)
        else:
            raise ValueError(f"Unsupported source_type: {conn_model.source_type}")

        connector.connect()
        n = sample_size or 10000

        counts = connector.estimate_counts()
        table_profiles = []

        total_invalid = 0
        total_orphans = 0
        total_dupes = 0
        total_rows_sampled = 0

        entities = conn_model.schema_json.get("entities", []) if conn_model.schema_json else []

        for entity in entities:
            name = entity["name"]
            rows = connector.fetch_sample(name, n)
            col_profiles = ColumnProfiler.profile_table(rows)

            # Detect duplicate PKs
            pk_cols = [c["name"] for c in entity.get("columns", []) if c.get("primary_key")]
            dupes = 0
            if pk_cols:
                dupes = QualityChecker.detect_duplicate_pks(rows, pk_cols[0])
                total_dupes += dupes

            # Sum invalid dates across all columns
            for cp in col_profiles:
                total_invalid += cp.get("invalid_dates", 0)

            total_rows_sampled += len(rows)

            table_profiles.append({
                "table": name,
                "row_count": counts.get(name, len(rows)),
                "columns": col_profiles,
                "duplicate_pk_count": dupes,
            })

        # Orphan FK check (MySQL only)
        if conn_model.source_type == "mysql":
            for entity in entities:
                child_name = entity["name"]
                child_rows = next(
                    (t for t in table_profiles if t["table"] == child_name), None
                )
                for fk in entity.get("foreign_keys", []):
                    parent_name = fk["ref_table"]
                    parent_rows = connector.fetch_sample(parent_name, n)
                    parent_ids = {row.get(fk["ref_column"]) for row in parent_rows}
                    if child_rows:
                        raw_rows = connector.fetch_sample(child_name, n)
                        orphans = QualityChecker.detect_orphan_fks(
                            raw_rows, fk["column"], parent_ids
                        )
                        total_orphans += orphans

        connector.disconnect()

        risk_score = QualityChecker.compute_risk_score(
            total_invalid, total_orphans, total_dupes, total_rows_sampled
        )
        risk_label = QualityChecker.label_risk(risk_score)

        results = {
            "tables": table_profiles,
            "risk_score": risk_score,
            "risk_label": risk_label,
        }

        # Persist results
        job_row = db.query(ProfilingJob).filter(ProfilingJob.job_id == job_id).first()
        if job_row:
            job_row.results = results
            job_row.risk_label = risk_label
            job_row.risk_score = risk_score
            db.commit()

        update_progress(job_id, 100, JobStatus.DONE)

    except Exception as exc:
        update_progress(job_id, 0, JobStatus.FAILED, error=str(exc))
        raise
    finally:
        db.close()


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
    """
    job_id = create_job(db, "profiling", connection_id=payload.connection_id)
    background_tasks.add_task(
        run_profiling, job_id, payload.connection_id, payload.sample_size
    )
    return {"job_id": job_id}


@router.get("/{job_id}", response_model=ProfilingResult)
def get_profiling_result(job_id: str, db: Session = Depends(get_db)):
    """Return the current profiling job status and results."""
    # Try in-memory cache first
    cache = get_job_status(job_id)

    job_row = db.query(ProfilingJob).filter(ProfilingJob.job_id == job_id).first()
    if not job_row and not cache:
        raise HTTPException(status_code=404, detail="Profiling job not found")

    status = (cache or {}).get("status", job_row.status if job_row else "unknown")
    results = job_row.results if job_row else {}
    tables = results.get("tables", []) if results else []
    risk_label = results.get("risk_label") if results else None
    risk_score = results.get("risk_score") if results else None

    return ProfilingResult(
        job_id=job_id,
        status=str(status),
        risk_label=risk_label,
        risk_score=risk_score,
        tables=tables,
    )

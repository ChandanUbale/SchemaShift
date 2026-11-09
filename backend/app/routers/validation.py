"""routers/validation.py — Post-migration validation and final report endpoints."""

import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.jobs import JobStatus, create_job, update_progress
from app.models.connection import Connection
from app.models.migration import MigrationJob
from app.models.validation import ValidationReport
from app.schemas.validation import FinalReport, ValidationRequest, ValidationResult
from app.services.discovery.connector_factory import ConnectorFactory
from app.services.validation import run_count_and_aggregate
from app.services.validation.checksum_validator import ChecksumValidator
from app.services.validation.relationship_validator import RelationshipValidator
from app.services.validation.report_generator import ReportGenerator

router = APIRouter()

def _numeric_fields(source_model: Connection, src_counts: dict, tgt_counts: dict) -> dict[str, list[str]]:
    common = set(src_counts) & set(tgt_counts)
    numeric_types = {"tinyint", "smallint", "mediumint", "int", "integer", "bigint", "decimal", "numeric", "float", "double", "number"}
    result: dict[str, list[str]] = {}
    for entity in (source_model.schema_json or {}).get("entities") or []:
        name = entity.get("name")
        if name not in common:
            continue
        fields = [
            column["name"] for column in entity.get("columns") or []
            if column.get("name") and str(column.get("data_type") or "").lower() in numeric_types
        ]
        if fields:
            result[name] = fields
    return result


def _checksum_entity(src_counts: dict, tgt_counts: dict) -> str | None:
    common = sorted(name for name, count in src_counts.items() if count and tgt_counts.get(name))
    return common[0] if common else None


def _fk_map(source_model: Connection) -> list[dict[str, str]]:
    fks: list[dict[str, str]] = []
    for entity in (source_model.schema_json or {}).get("entities") or []:
        for fk in entity.get("foreign_keys") or []:
            if not fk.get("column") or not fk.get("ref_table"):
                continue
            fks.append({
                "child_table": entity["name"],
                "fk_field": fk["column"],
                "parent_table": fk["ref_table"],
                "pk_field": fk.get("ref_column") or "id",
            })
    return fks


def _open_connector(conn_model: Connection):
    if conn_model.source_type == "mysql":
        return ConnectorFactory.get_connector("mysql", conn_model.dsn)
    if conn_model.source_type == "mongodb":
        parsed = urlparse(conn_model.dsn)
        db_name = parsed.path.lstrip("/")
        return ConnectorFactory.get_connector("mongodb", conn_model.dsn, db_name=db_name)
    raise ValueError(f"Unsupported source_type: {conn_model.source_type}")


def _load_migration_job(db: Session, key: str) -> MigrationJob | None:
    job = db.query(MigrationJob).filter(MigrationJob.job_id == key).first()
    if job:
        return job
    if key.isdigit():
        return db.query(MigrationJob).filter(MigrationJob.id == int(key)).first()
    return None


def _records_migrated(job: MigrationJob) -> int:
    return sum(
        int(entry.get("rows") or 0)
        for entry in (job.audit_log or [])
        if entry.get("ok") and entry.get("entity") != "cleanup"
    )


def _duration_seconds(job: MigrationJob) -> float:
    if job.created_at and job.completed_at:
        return max((job.completed_at - job.created_at).total_seconds(), 0.0)
    return 0.0


def _to_result(row: ValidationReport) -> ValidationResult:
    return ValidationResult(
        count_match_pct=float(row.count_match_pct or 0),
        aggregate_match=(row.aggregate_match == "yes"),
        sample_matched=row.sample_matched or "0/0",
        relationship_checks=row.relationship_checks or "failed",
        details=row.details or {},
    )


def run_validation(job_id: str, payload: ValidationRequest) -> None:
    db = SessionLocal()
    source = target = None
    try:
        update_progress(job_id, 0, JobStatus.RUNNING)
        source_model = db.query(Connection).filter(Connection.id == payload.source_connection_id).first()
        target_model = db.query(Connection).filter(Connection.id == payload.target_connection_id).first()
        if not source_model or not target_model:
            raise ValueError("Connection not found")

        migration = _load_migration_job(db, payload.migration_job_id)
        if not migration:
            raise ValueError("Migration job not found")

        source = _open_connector(source_model)
        target = _open_connector(target_model)
        source.connect()
        target.connect()

        src_counts = source.estimate_counts() or {}
        tgt_counts = target.estimate_counts() or {}
        if payload.entity_names is not None:
            requested = set(payload.entity_names)
            available = {entity.get("name") for entity in (source_model.schema_json or {}).get("entities", [])}
            unknown = requested - available
            if unknown:
                raise ValueError(f"Unknown source entities: {', '.join(sorted(unknown))}")
            if not requested:
                raise ValueError("Select at least one table or collection to validate.")
            src_counts = {name: count for name, count in src_counts.items() if name in requested}
            tgt_counts = {name: count for name, count in tgt_counts.items() if name in requested}
        numeric_fields = _numeric_fields(source_model, src_counts, tgt_counts)
        counts_aggs = run_count_and_aggregate(source, target, numeric_fields)
        update_progress(job_id, 40, JobStatus.RUNNING)

        sample_n = payload.sample_size or 100
        checksum_entity = _checksum_entity(src_counts, tgt_counts)
        src_rows, tgt_rows = [], []
        if checksum_entity:
            try:
                src_rows = source.fetch_sample(checksum_entity, sample_n)
            except Exception:
                src_rows = []
            try:
                tgt_rows = target.fetch_sample(checksum_entity, sample_n)
            except Exception:
                tgt_rows = []
        checksum = ChecksumValidator.validate(src_rows, tgt_rows, "id")
        update_progress(job_id, 70, JobStatus.RUNNING)

        fk_map = [fk for fk in _fk_map(source_model) if fk["child_table"] in src_counts and fk["parent_table"] in src_counts]
        relationships = RelationshipValidator.validate_fk_integrity(target, fk_map)

        validation_result = {
            "count_match_pct": counts_aggs["counts"]["match_pct"],
            "aggregate_match": bool(counts_aggs["aggregates"]["match"]),
            "sample_matched": checksum["summary"],
            "relationship_checks": "passed" if relationships["passed"] else "failed",
            "details": {
                "counts": counts_aggs["counts"],
                "aggregates": counts_aggs["aggregates"],
                "checksum": checksum,
                "relationships": relationships,
            },
        }

        failed_batches = 0
        if migration.batches_total is not None and migration.batches_done is not None:
            failed_batches = max(int(migration.batches_total) - int(migration.batches_done), 0)
        migration_stats = {
            "records_migrated": _records_migrated(migration),
            "batches_total": int(migration.batches_total or 0),
            "batches_failed": failed_batches,
            "duration_seconds": _duration_seconds(migration),
        }

        output_path = str(Path(tempfile.gettempdir()) / "schemashift-reports" / f"{job_id}.html")
        report = ReportGenerator.generate(migration_stats, validation_result, output_path)

        db.add(ValidationReport(
            migration_job_id=migration.id,
            count_match_pct=validation_result["count_match_pct"],
            aggregate_match="yes" if validation_result["aggregate_match"] else "no",
            sample_matched=validation_result["sample_matched"],
            relationship_checks=validation_result["relationship_checks"],
            details={**validation_result["details"], "report": report, "job_id": job_id},
            html_report_path=output_path,
        ))
        db.commit()
        update_progress(job_id, 100, JobStatus.DONE)
    except Exception as exc:
        update_progress(job_id, 0, JobStatus.FAILED, error=str(exc))
        raise
    finally:
        for connector in (source, target):
            if connector is not None:
                try:
                    connector.disconnect()
                except Exception:
                    pass
        db.close()


@router.post("/", status_code=202)
def start_validation(
    payload: ValidationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start validation as a background task. Reads source + target — no writes."""
    if not _load_migration_job(db, payload.migration_job_id):
        raise HTTPException(status_code=404, detail="Migration job not found")
    job_id = create_job(db, "validation", connection_id=payload.source_connection_id)
    background_tasks.add_task(run_validation, job_id, payload)
    return {"job_id": job_id}


def _report_row(db: Session, migration_job_id: str) -> tuple[MigrationJob, ValidationReport]:
    migration = _load_migration_job(db, migration_job_id)
    if not migration:
        raise HTTPException(status_code=404, detail="Migration job not found")
    row = (
        db.query(ValidationReport)
        .filter(ValidationReport.migration_job_id == migration.id)
        .order_by(ValidationReport.id.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Validation result not found")
    return migration, row


@router.get("/{migration_job_id}/result", response_model=ValidationResult)
def get_validation_result(migration_job_id: str, db: Session = Depends(get_db)):
    """Return the validation result for a completed migration job."""
    _migration, row = _report_row(db, migration_job_id)
    return _to_result(row)


@router.get("/{migration_job_id}/report", response_model=FinalReport)
def get_final_report(migration_job_id: str, db: Session = Depends(get_db)):
    """Full final report: migration stats and validation correctness."""
    migration, row = _report_row(db, migration_job_id)
    details = row.details or {}
    report = details.get("report") or {}
    failed_batches = 0
    if migration.batches_total is not None and migration.batches_done is not None:
        failed_batches = max(int(migration.batches_total) - int(migration.batches_done), 0)
    return FinalReport(
        records_migrated=_records_migrated(migration),
        batches_total=int(migration.batches_total or 0),
        batches_failed=failed_batches,
        duration_seconds=_duration_seconds(migration),
        validation=_to_result(row),
        html_report_path=row.html_report_path,
        json_report=report,
    )


@router.get("/{migration_job_id}/report.html")
def download_html_report(migration_job_id: str, db: Session = Depends(get_db)):
    """Serve the generated HTML report file for download."""
    _migration, row = _report_row(db, migration_job_id)
    html = None
    if row.html_report_path:
        path = Path(row.html_report_path)
        if path.is_file():
            html = path.read_text(encoding="utf-8")
    if not html:
        details = row.details or {}
        html = (details.get("report") or {}).get("html")
    if not html:
        raise HTTPException(status_code=404, detail="HTML report not found")
    if "Back to SchemaShift" not in html:
        html = html.replace(
            "<body>",
            '<body><p><a href="javascript:history.back()">← Back to SchemaShift</a></p>',
            1,
        )
    return HTMLResponse(content=html)

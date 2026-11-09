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
from app.services.migration.plan_builder import build_plan, select_schema_entities
from app.services.migration.transformer import Transformer
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
            if column.get("name")
            and (source_model.source_type != "mongodb" or "." not in column["name"])
            and str(column.get("data_type") or "").lower() in numeric_types
        ]
        if fields:
            result[name] = fields
    return result


def _validation_mapping(source_model: Connection, entity_names: list[str] | None = None):
    schema = source_model.schema_json or {}
    selected_schema = select_schema_entities(schema, entity_names)
    target_type = "mysql" if source_model.source_type == "mongodb" else "mongodb"
    plan = build_plan(selected_schema, source_model.source_type, target_type)
    entities = [entity for entity in selected_schema.get("entities") or [] if entity.get("name")]
    target_names: dict[str, str] = {}
    source_primary_keys: dict[str, str] = {}
    target_primary_keys: dict[str, str] = {}
    field_mappings: dict[str, dict[str, str]] = {}

    if plan.get("direction") == "document_to_relational":
        for spec in plan.get("flatten") or []:
            if (spec.get("from_path") or "$") not in ("$", ""):
                continue
            source_name = spec.get("collection") or spec.get("table")
            if source_name:
                target_names[source_name] = spec["table"]
                source_primary_keys[source_name] = "_id"
                target_primary_keys[source_name] = "id"
                field_mappings[source_name] = spec.get("rename") or {}
    elif plan.get("direction") == "relational_to_document":
        trees = list(plan.get("model_trees") or [])
        if not trees and plan.get("model_tree"):
            trees = [plan["model_tree"]]
        for tree in trees:
            source_name = tree.get("from_table") or tree.get("collection")
            if source_name:
                target_names[source_name] = tree.get("collection") or source_name
                pk = next((
                    column.get("name") for entity in entities if entity.get("name") == source_name
                    for column in entity.get("columns") or [] if column.get("primary_key")
                ), "id")
                source_primary_keys[source_name] = pk
                target_primary_keys[source_name] = pk
                field_mappings[source_name] = {}
    else:
        for entity in entities:
            name = entity["name"]
            target_names[name] = name
            pk = next((column.get("name") for column in entity.get("columns") or [] if column.get("primary_key")), "id")
            source_primary_keys[name] = pk
            target_primary_keys[name] = pk
            field_mappings[name] = {}

    return selected_schema, target_names, source_primary_keys, target_primary_keys, field_mappings, plan


def _validate_entity_samples(
    source,
    target,
    entity_names: list[str],
    target_names: dict[str, str],
    source_primary_keys: dict[str, str],
    target_primary_keys: dict[str, str],
    sample_size: int,
    plan: dict,
) -> dict:
    per_entity = {}
    total_checked = 0
    total_matched = 0
    transformer = Transformer(plan) if plan.get("direction") == "document_to_relational" else None
    for entity in entity_names:
        source_pk = source_primary_keys.get(entity, "id")
        target_pk = target_primary_keys.get(entity, "id")
        source_rows = source.fetch_sample(entity, sample_size)
        ids = [row.get(source_pk) for row in source_rows if row.get(source_pk) is not None]
        if not ids:
            result = ChecksumValidator.validate(source_rows, [], source_pk_field=source_pk, target_pk_field=target_pk)
            result["note"] = f"No values for source key {source_pk!r}; sample comparison is inconclusive."
            result["source_sample_size"] = len(source_rows)
            result["target_rows_fetched"] = 0
            per_entity[entity] = result
            continue
        fetch_by_ids = getattr(target, "fetch_by_ids", None)
        if ids and callable(fetch_by_ids):
            target_rows = fetch_by_ids(target_names.get(entity, entity), target_pk, ids)
        else:
            target_rows = []
        comparison_rows = source_rows
        comparison_source_pk = source_pk
        json_fields: set[str] = set()
        if transformer is not None:
            transformed = transformer.transform_batch({entity: source_rows}, "document_to_relational")
            comparison_rows = transformed.get(target_names.get(entity, entity), [])
            comparison_source_pk = target_pk
            root_spec = next((
                spec for spec in plan.get("flatten") or []
                if spec.get("collection") == entity and (spec.get("from_path") or "$") in ("$", "")
            ), {})
            rename = root_spec.get("rename") or {}
            json_fields.update(rename.get(field, field) for field in root_spec.get("json_fields") or [])
            known_fields = {rename.get(field, field) for field in root_spec.get("fields") or []}
            json_fields.update(
                key for row in comparison_rows for key in row
                if key not in known_fields and key != target_pk
            )
        result = ChecksumValidator.validate(
            comparison_rows,
            target_rows,
            source_pk_field=comparison_source_pk,
            target_pk_field=target_pk,
            json_fields=json_fields,
        )
        result["source_sample_size"] = len(source_rows)
        result["target_rows_fetched"] = len(target_rows)
        per_entity[entity] = result
        total_checked += int(result["checked"])
        total_matched += int(result["matched"])
    return {
        "checked": total_checked,
        "matched": total_matched,
        "summary": f"{total_matched}/{total_checked}" if total_checked else "0/0",
        "per_entity": per_entity,
        "note": "For each entity with source keys, compares a source sample with target rows fetched using those same keys.",
    }


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

        selected_schema, target_names, source_primary_keys, target_primary_keys, field_mappings, plan = _validation_mapping(
            source_model, payload.entity_names
        )
        source_entities = [entity["name"] for entity in selected_schema.get("entities") or [] if entity.get("name")]
        source_exact_counts = source.count_entities() or {}
        target_exact_counts = target.count_entities() or {}
        src_counts = {name: int(source_exact_counts.get(name, 0) or 0) for name in source_entities}
        tgt_counts = {
            name: int(target_exact_counts.get(target_names.get(name, name), 0) or 0)
            for name in source_entities
        }
        numeric_fields = _numeric_fields(source_model, src_counts, tgt_counts)
        counts_aggs = run_count_and_aggregate(
            source,
            target,
            numeric_fields,
            source_counts=src_counts,
            target_counts=tgt_counts,
            entity_mapping=target_names,
            source_primary_keys=source_primary_keys,
            target_primary_keys=target_primary_keys,
            field_mappings=field_mappings,
        )
        update_progress(job_id, 40, JobStatus.RUNNING)

        sample_n = payload.sample_size or 100
        checksum = _validate_entity_samples(
            source,
            target,
            source_entities,
            target_names,
            source_primary_keys,
            target_primary_keys,
            sample_n,
            plan,
        )
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

"""schemas/validation.py — Pydantic API contracts for validation results and final report."""

from pydantic import BaseModel


class ValidationRequest(BaseModel):
    migration_job_id: int
    source_connection_id: int
    target_connection_id: int
    sample_size: int = 100


class ValidationResult(BaseModel):
    """
    Post-migration validation — kept separate from profiling risk score.
    """
    count_match_pct: float          # e.g. 99.8
    aggregate_match: bool           # SUM / AVG match on selected numeric fields
    sample_matched: str             # e.g. "100/100"
    relationship_checks: str        # "passed" | "failed"
    details: dict = {}


class FinalReport(BaseModel):
    """Combines all three stages for the final report page."""
    # 1 — data quality before migration
    risk_label: str                 # low | medium | high
    risk_score: float

    # 2 — migration execution stats
    records_migrated: int
    batches_total: int
    batches_failed: int
    duration_seconds: float

    # 3 — validation correctness after migration
    validation: ValidationResult

    # Report artefacts
    html_report_path: str | None = None
    json_report: dict = {}

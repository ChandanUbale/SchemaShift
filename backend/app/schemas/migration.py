"""schemas/migration.py — Pydantic API contracts for dry-run, execute, and progress."""

from pydantic import BaseModel, Field


class DryRunRequest(BaseModel):
    source_connection_id: int
    entity_names: list[str] | None = None


class DryRunIssue(BaseModel):
    table_or_collection: str
    issue_type: str        # e.g. "invalid_date", "orphan_fk", "duplicate_pk"
    row_count: int
    description: str


class DryRunResult(BaseModel):
    job_id: str
    plan_id: str | None = None
    issues: list[DryRunIssue] = []
    total_issues: int = 0
    sample_size: int = 0


class MigrationApproveRequest(BaseModel):
    job_id: str
    plan_id: str
    source_connection_id: int
    target_connection_id: int
    entity_names: list[str] | None = None
    target_collection_name: str | None = Field(default=None, max_length=120)
    in_place_optimisation: bool = False  # must be explicit


class MigrationProgressResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: float
    batches_done: int
    batches_total: int | None
    error: str | None = None
    audit_log: list = []


class CleanupRequest(BaseModel):
    job_id: str
    target_connection_id: int

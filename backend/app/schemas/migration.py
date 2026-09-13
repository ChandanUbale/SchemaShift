"""schemas/migration.py — Pydantic API contracts for dry-run, execute, and progress."""

from pydantic import BaseModel
from typing import Literal


class DryRunRequest(BaseModel):
    source_connection_id: int
    plan_id: str  # from recommendation


class DryRunIssue(BaseModel):
    table_or_collection: str
    issue_type: str        # e.g. "invalid_date", "orphan_fk", "duplicate_pk"
    row_count: int
    description: str


class DryRunResult(BaseModel):
    job_id: str
    issues: list[DryRunIssue] = []
    total_issues: int = 0
    sample_size: int = 0


class MigrationApproveRequest(BaseModel):
    job_id: str
    plan_id: str
    source_connection_id: int
    target_connection_id: int
    override_recommendation: Literal["mysql", "mongodb"] | None = None  # manual override
    in_place_optimisation: bool = False  # must be explicit


class MigrationProgressResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: float
    batches_done: int
    batches_total: int | None
    error: str | None = None


class CleanupRequest(BaseModel):
    job_id: str
    target_connection_id: int

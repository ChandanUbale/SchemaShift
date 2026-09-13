"""schemas/profiling.py — Pydantic API contracts for profiling jobs and results."""

from pydantic import BaseModel
from typing import Any, Literal


class ProfilingRequest(BaseModel):
    connection_id: int
    sample_size: int | None = None  # overrides PROFILE_SAMPLE_SIZE env var


class ColumnProfile(BaseModel):
    column: str
    null_rate: float
    distinct_count: int
    duplicate_count: int
    min_value: Any | None = None
    max_value: Any | None = None
    invalid_dates: int = 0
    orphan_fk_count: int = 0


class TableProfile(BaseModel):
    table: str
    row_count: int
    columns: list[ColumnProfile] = []


class ProfilingResult(BaseModel):
    job_id: str
    status: str
    risk_label: Literal["low", "medium", "high"] | None = None
    risk_score: float | None = None  # (invalid + orphan + dupe) / total * 100
    tables: list[TableProfile] = []

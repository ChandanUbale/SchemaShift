"""schemas/recommendation.py — Pydantic API contracts for the recommendation engine."""

from pydantic import BaseModel
from typing import Literal


class WorkloadForm(BaseModel):
    """Short structured form — not a real query log."""
    mostly_reads: bool = False
    frequent_joins: bool = False
    nested_together_access: bool = False
    transactional_writes: bool = False
    analytical_aggregations: bool = False


class ReasonCode(BaseModel):
    code: str
    message: str
    weight: float


class RecommendationRequest(BaseModel):
    connection_id: int
    workload: WorkloadForm


class RecommendationResult(BaseModel):
    """
    Output of the rule-based scoring engine.
    Always populated even when Ollama is down.
    """
    recommended_model: Literal["relational", "document"]
    target_type: Literal["mysql", "mongodb"]
    confidence: int  # 0–100
    reasons: list[ReasonCode]
    ai_explanation: str | None = None  # populated only when USE_LOCAL_LLM=true and Ollama is up
    plan_id: str | None = None         # UUID for the generated model plan
    generated_ddl: str | None = None   # MySQL DDL or None (document path returns model_tree)
    model_tree: dict | None = None     # nested MongoDB shape or None (relational path returns ddl)

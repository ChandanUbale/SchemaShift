"""
services/recommendation/scoring_engine.py — Deterministic relational-vs-document rule engine.

This is the core decision maker. It is NOT an LLM.
Weights are documented here so judges can inspect them.

Signals scored:
  - Number/depth of FK relationships        → relational ↑
  - Frequent joins / fetched-together       → relational ↑
  - Nested / embedded structure             → document ↑
  - Read-heavy, flexible fields             → document ↑
  - Transactional writes / integrity needs  → relational ↑
  - Aggregation / scan-style access         → document ↑ (or relational if analytical)

Output:
  recommended_model: "relational" | "document"
  target_type:       "mysql"      | "mongodb"
  confidence:        0–100
  reasons:           [{ code, message, weight }]
"""

from typing import Any


WEIGHTS = {
    # signals that push toward relational
    "high_fk_count":          +30,
    "frequent_joins":         +25,
    "transactional_writes":   +20,
    "integrity_needs":        +15,
    "normalized_schema":      +10,

    # signals that push toward document
    "nested_embedded":        -30,
    "few_joins":              -20,
    "read_heavy":             -15,
    "flexible_fields":        -15,
    "aggregation_scan":       -10,
}


class ScoringEngine:

    @staticmethod
    def score(profiling_result: dict[str, Any], workload: dict[str, Any]) -> dict[str, Any]:
        """
        Run the rule engine and return a recommendation.

        Args:
            profiling_result: output of the profiling job (tables, FKs, nesting depth, etc.)
            workload:         WorkloadForm dict (mostly_reads, frequent_joins, etc.)

        Returns:
            {
                "recommended_model": "relational" | "document",
                "target_type":       "mysql"      | "mongodb",
                "confidence":        int (0–100),
                "reasons":           [{"code": str, "message": str, "weight": int}],
                "raw_score":         int,  # positive = relational, negative = document
            }

        TODO:
        - Accumulate weighted signals from profiling_result and workload
        - positive raw_score → relational → mysql
        - negative raw_score → document   → mongodb
        - map |raw_score| to confidence 0–100
        """
        raise NotImplementedError("TODO: implement ScoringEngine.score")

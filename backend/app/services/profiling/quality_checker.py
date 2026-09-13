"""
services/profiling/quality_checker.py — Data quality issue detection.

Detects:
  - Duplicate PKs / _id values
  - Orphan FK records (relational)
  - Broken _id references (MongoDB)
  - Invalid dates (date fields that fail parsing)

Computes the risk score used to label profiling risk: Low / Medium / High.
  risk_score = (invalid_records + orphan_records + duplicate_keys) / total_sampled * 100
  Low < 1%, Medium < 5%, High >= 5%
"""

from typing import Any, Literal


RiskLabel = Literal["low", "medium", "high"]


class QualityChecker:

    @staticmethod
    def detect_duplicate_pks(rows: list[dict[str, Any]], pk_field: str) -> int:
        """
        Count rows where pk_field is duplicated.
        TODO: count values that appear more than once.
        """
        raise NotImplementedError("TODO: implement detect_duplicate_pks")

    @staticmethod
    def detect_orphan_fks(
        child_rows: list[dict[str, Any]],
        fk_field: str,
        parent_ids: set[Any],
    ) -> int:
        """
        Count child rows where fk_field value is not in parent_ids.
        TODO: {row[fk_field] for row in child_rows if row[fk_field] not in parent_ids}
        """
        raise NotImplementedError("TODO: implement detect_orphan_fks")

    @staticmethod
    def detect_invalid_dates(values: list[Any]) -> int:
        """
        Count values that look like dates/strings but fail ISO 8601 parsing.
        TODO: attempt datetime.fromisoformat() or dateutil.parse() on each value.
        """
        raise NotImplementedError("TODO: implement detect_invalid_dates")

    @staticmethod
    def compute_risk_score(invalid: int, orphans: int, duplicates: int, total: int) -> float:
        """
        risk_score = (invalid + orphans + duplicates) / total * 100
        Returns 0.0 if total == 0.
        """
        if total == 0:
            return 0.0
        return (invalid + orphans + duplicates) / total * 100

    @staticmethod
    def label_risk(risk_score: float) -> RiskLabel:
        """Low < 1%, Medium < 5%, High >= 5%."""
        if risk_score < 1.0:
            return "low"
        if risk_score < 5.0:
            return "medium"
        return "high"

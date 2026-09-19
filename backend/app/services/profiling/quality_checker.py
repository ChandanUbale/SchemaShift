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
        Count rows where pk_field value appears more than once.
        Returns 0 if pk_field is missing from all rows.
        """
        if not rows or pk_field not in rows[0]:
            return 0

        from collections import Counter
        pk_values = [row.get(pk_field) for row in rows if row.get(pk_field) is not None]
        counts = Counter(pk_values)
        # Count total rows that are duplicates (appear more than once)
        return sum(count for count in counts.values() if count > 1)

    @staticmethod
    def detect_orphan_fks(
        child_rows: list[dict[str, Any]],
        fk_field: str,
        parent_ids: set[Any],
    ) -> int:
        """
        Count child rows whose fk_field value is not None and not in parent_ids.
        """
        return sum(
            1 for row in child_rows
            if row.get(fk_field) is not None and row.get(fk_field) not in parent_ids
        )

    @staticmethod
    def detect_invalid_dates(values: list[Any]) -> int:
        """
        Count values that look like date strings but fail ISO 8601 parsing.
        Already-parsed date/datetime objects are considered valid.
        """
        from datetime import date, datetime

        invalid = 0
        for v in values:
            if v is None:
                continue
            # Already a proper date or datetime — valid
            if isinstance(v, (date, datetime)):
                continue
            # String — try parsing
            if isinstance(v, str):
                # Explicitly reject the zero date
                if v == '0000-00-00' or v.startswith('0000-00-00'):
                    invalid += 1
                    continue
                try:
                    datetime.fromisoformat(v.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    invalid += 1
        return invalid

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

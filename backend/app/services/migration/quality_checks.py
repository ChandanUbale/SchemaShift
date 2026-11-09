"""Data-quality checks used by migration dry runs and validation."""

from typing import Any


class QualityChecker:
    @staticmethod
    def detect_duplicate_pks(rows: list[dict[str, Any]], pk_field: str) -> int:
        if not rows or pk_field not in rows[0]:
            return 0
        from collections import Counter

        values = [row.get(pk_field) for row in rows if row.get(pk_field) is not None]
        return sum(count for count in Counter(values).values() if count > 1)

    @staticmethod
    def detect_orphan_fks(
        child_rows: list[dict[str, Any]],
        fk_field: str,
        parent_ids: set[Any],
    ) -> int:
        return sum(
            1 for row in child_rows
            if row.get(fk_field) is not None and row.get(fk_field) not in parent_ids
        )

    @staticmethod
    def detect_invalid_dates(values: list[Any]) -> int:
        from datetime import date, datetime

        invalid = 0
        for value in values:
            if value is None or isinstance(value, (date, datetime)):
                continue
            if isinstance(value, str):
                if value == "0000-00-00" or value.startswith("0000-00-00"):
                    invalid += 1
                    continue
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    invalid += 1
        return invalid
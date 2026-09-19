"""
services/profiling/column_profiler.py — Per-column / per-field statistical profiling.

Works on a list of sampled rows/documents returned by connector.fetch_sample().
Does NOT call the database directly — receives data from the connector.
"""

from datetime import date, datetime
from typing import Any

from app.services.profiling.quality_checker import QualityChecker


class ColumnProfiler:

    @staticmethod
    def profile_column(column_name: str, values: list[Any]) -> dict[str, Any]:
        """
        Compute statistics for a single column/field from sampled values.

        Returns:
            {
                "column": str,
                "null_rate": float,
                "distinct_count": int,
                "duplicate_count": int,
                "min_value": Any | None,
                "max_value": Any | None,
                "invalid_dates": int,
            }
        """
        if not values:
            return {
                "column": column_name,
                "null_rate": 0.0,
                "distinct_count": 0,
                "duplicate_count": 0,
                "min_value": None,
                "max_value": None,
                "invalid_dates": 0,
            }

        total = len(values)
        null_count = sum(1 for v in values if v is None)
        null_rate = null_count / total

        non_null = [v for v in values if v is not None]
        distinct_values = set(str(v) for v in non_null)
        distinct_count = len(distinct_values)
        duplicate_count = len(non_null) - distinct_count

        # min/max only for numeric and date types
        numeric_or_date = [
            v for v in non_null
            if isinstance(v, (int, float, datetime, date))
        ]
        min_value = min(numeric_or_date) if numeric_or_date else None
        max_value = max(numeric_or_date) if numeric_or_date else None

        invalid_dates = QualityChecker.detect_invalid_dates(values)

        return {
            "column": column_name,
            "null_rate": round(null_rate, 4),
            "distinct_count": distinct_count,
            "duplicate_count": duplicate_count,
            "min_value": str(min_value) if min_value is not None else None,
            "max_value": str(max_value) if max_value is not None else None,
            "invalid_dates": invalid_dates,
        }

    @staticmethod
    def profile_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Profile all columns in a sampled table/collection.
        Returns a list of per-column profile dicts.
        """
        if not rows:
            return []

        # Collect all keys across all rows
        all_keys: set[str] = set()
        for row in rows:
            all_keys.update(row.keys())

        result = []
        for key in sorted(all_keys):
            values = [row.get(key) for row in rows]
            result.append(ColumnProfiler.profile_column(key, values))

        return result

"""
services/profiling/column_profiler.py — Per-column / per-field statistical profiling.

Works on a list of sampled rows/documents returned by connector.fetch_sample().
Does NOT call the database directly — receives data from the connector.
"""

from typing import Any


class ColumnProfiler:

    @staticmethod
    def profile_column(column_name: str, values: list[Any]) -> dict[str, Any]:
        """
        Compute statistics for a single column/field from sampled values.

        Returns:
            {
                "column": str,
                "null_rate": float,          # fraction of None values
                "distinct_count": int,
                "duplicate_count": int,
                "min_value": Any | None,
                "max_value": Any | None,
                "invalid_dates": int,        # values that look like dates but fail parsing
            }

        TODO: implement null_rate, distinct_count, duplicate_count, min, max, invalid_dates.
        """
        raise NotImplementedError("TODO: implement ColumnProfiler.profile_column")

    @staticmethod
    def profile_table(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Profile all columns in a sampled table/collection.
        Returns a list of per-column profile dicts.
        TODO: transpose rows → columns, call profile_column for each.
        """
        raise NotImplementedError("TODO: implement ColumnProfiler.profile_table")

"""
services/profiling/volume_estimator.py — Estimate source data volume and expected target storage.

Order-of-magnitude estimates are sufficient for the demo.
Uses connector.estimate_counts() and average row size heuristics.
"""

from typing import Any


class VolumeEstimator:

    @staticmethod
    def estimate_source_volume(counts: dict[str, int], avg_row_bytes: int = 512) -> dict[str, Any]:
        """
        Estimate total data volume per table/collection.

        Args:
            counts:        {table_name: row_count} from connector.estimate_counts()
            avg_row_bytes: rough average row size in bytes (configurable per entity)

        Returns:
            {
                "tables": {table_name: {"row_count": int, "estimated_bytes": int}},
                "total_rows": int,
                "total_estimated_mb": float,
            }
        """
        tables = {}
        total_bytes = 0

        for table_name, row_count in counts.items():
            estimated_bytes = row_count * avg_row_bytes
            tables[table_name] = {
                "row_count": row_count,
                "estimated_bytes": estimated_bytes,
            }
            total_bytes += estimated_bytes

        return {
            "tables": tables,
            "total_rows": sum(counts.values()),
            "total_estimated_mb": round(total_bytes / 1_000_000, 2),
        }

    @staticmethod
    def estimate_target_overhead(source_type: str, target_type: str, source_bytes: int) -> int:
        """
        Heuristic overhead multiplier for target storage.
        - mysql → mongodb: 1.4x  (embedding copies parent fields)
        - mongodb → mysql: 1.1x
        - same type: 1.0x
        Returns estimated target bytes.
        """
        if source_type == "mysql" and target_type == "mongodb":
            return int(source_bytes * 1.4)
        if source_type == "mongodb" and target_type == "mysql":
            return int(source_bytes * 1.1)
        return source_bytes

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

        TODO: implement estimation logic.
        """
        raise NotImplementedError("TODO: implement VolumeEstimator.estimate_source_volume")

    @staticmethod
    def estimate_target_overhead(source_type: str, target_type: str, source_bytes: int) -> int:
        """
        Heuristic overhead multiplier for target storage.
        e.g. MySQL → MongoDB may embed related rows, increasing doc size.
        Returns estimated target bytes.
        TODO: apply source→target multiplier (1.0–2.0 for MVP).
        """
        raise NotImplementedError("TODO: implement VolumeEstimator.estimate_target_overhead")

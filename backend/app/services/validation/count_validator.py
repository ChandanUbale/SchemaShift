"""services/validation/count_validator.py — Record count comparison (source vs target)."""

from typing import Any


class CountValidator:

    @staticmethod
    def validate(
        source_counts: dict[str, int],
        target_counts: dict[str, int],
    ) -> dict[str, Any]:
        """
        Compare row/document counts per entity between source and target.

        Returns:
            {
                "total_source": int,
                "total_target": int,
                "match_pct": float,          # e.g. 99.8
                "per_entity": {
                    entity_name: {"source": int, "target": int, "match": bool}
                }
            }

        TODO: compute totals, per-entity match, overall match_pct.
        """
        raise NotImplementedError("TODO: implement CountValidator.validate")

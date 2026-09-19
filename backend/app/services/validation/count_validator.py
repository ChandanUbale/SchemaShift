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
        """
        total_source = sum(source_counts.values())
        total_target = sum(target_counts.values())
        
        if total_source > 0:
            match_pct = round(100.0 * total_target / total_source, 1)
        elif total_source == 0 and total_target == 0:
            match_pct = 100.0
        else:
            match_pct = 0.0
            
        all_keys = set(source_counts.keys()).union(set(target_counts.keys()))
        per_entity = {}
        for key in all_keys:
            s_val = source_counts.get(key, 0)
            t_val = target_counts.get(key, 0)
            per_entity[key] = {
                "source": s_val,
                "target": t_val,
                "match": s_val == t_val
            }
            
        return {
            "total_source": total_source,
            "total_target": total_target,
            "match_pct": match_pct,
            "per_entity": per_entity
        }

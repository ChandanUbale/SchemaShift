"""services/validation/aggregate_validator.py — Aggregate comparison (SUM/AVG) source vs target."""

from typing import Any


class AggregateValidator:

    @staticmethod
    def _extract_sum(rows: list[dict[str, Any]], field: str) -> float:
        """Helper to extract and sum a field, supporting dotted paths and arrays."""
        def _get_val(doc, parts):
            if not parts:
                return doc
            if isinstance(doc, dict):
                return _get_val(doc.get(parts[0]), parts[1:])
            if isinstance(doc, list):
                return sum((_get_val(item, parts) or 0) for item in doc)
            return doc

        total = 0.0
        parts = field.split(".")
        for row in rows:
            val = _get_val(row, parts)
            try:
                total += float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                pass
        return total

    @staticmethod
    def validate(
        source_connector,
        target_connector,
        numeric_fields: dict[str, list[str]],   # {table: [col1, col2]}
        tolerance: float = 0.001,
    ) -> dict[str, Any]:
        """
        Compare SUM of selected numeric columns between source and target via sampling.
        """
        all_match = True
        details = {}

        for entity, fields in numeric_fields.items():
            # Use fetch_sample for a universal approach (10,000 rows should be enough for MVP)
            src_rows = source_connector.fetch_sample(entity, 10000)
            
            # For MongoDB targets, the entity might not exist at the root, 
            # but we attempt to fetch it or rely on Lavanya passing the correct mapping.
            try:
                tgt_rows = target_connector.fetch_sample(entity, 10000)
            except Exception:
                tgt_rows = []

            entity_details = {}
            for field in fields:
                src_sum = AggregateValidator._extract_sum(src_rows, field)
                tgt_sum = AggregateValidator._extract_sum(tgt_rows, field)
                
                # Check match using tolerance
                diff = abs(src_sum - tgt_sum)
                max_val = max(abs(src_sum), 1.0)
                match = diff <= (tolerance * max_val)
                
                if not match:
                    all_match = False
                    
                entity_details[field] = {
                    "source_sum": round(src_sum, 4),
                    "target_sum": round(tgt_sum, 4),
                    "match": match
                }
            details[entity] = entity_details

        return {
            "match": all_match,
            "details": details
        }

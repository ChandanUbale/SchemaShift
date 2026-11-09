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
                if hasattr(val, "to_decimal"):
                    val = val.to_decimal()
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
        entity_mapping: dict[str, str] | None = None,
        source_primary_keys: dict[str, str] | None = None,
        target_primary_keys: dict[str, str] | None = None,
        field_mappings: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        Compare SUM of selected numeric columns between source and target via sampling.
        """
        all_match = True
        details = {}
        entity_mapping = entity_mapping or {}
        source_primary_keys = source_primary_keys or {}
        target_primary_keys = target_primary_keys or {}
        field_mappings = field_mappings or {}

        for entity, fields in numeric_fields.items():
            target_entity = entity_mapping.get(entity, entity)
            src_pk = source_primary_keys.get(entity, "id")
            tgt_pk = target_primary_keys.get(entity, src_pk)
            fetch_source_batch = getattr(source_connector, "fetch_batch", None)
            src_rows = (fetch_source_batch(entity, 0, 10000) if callable(fetch_source_batch)
                        else source_connector.fetch_sample(entity, 10000))
            ids = [row.get(src_pk) for row in src_rows if row.get(src_pk) is not None]
            fetch_target_by_ids = getattr(target_connector, "fetch_by_ids", None)
            try:
                if ids and callable(fetch_target_by_ids):
                    tgt_rows = fetch_target_by_ids(target_entity, tgt_pk, ids)
                else:
                    tgt_rows = target_connector.fetch_sample(target_entity, 10000)
            except Exception:
                tgt_rows = []

            entity_details = {}
            for field in fields:
                src_sum = AggregateValidator._extract_sum(src_rows, field)
                target_field = field_mappings.get(entity, {}).get(field, field)
                tgt_sum = AggregateValidator._extract_sum(tgt_rows, target_field)
                
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
            entity_details["_sample"] = {
                "source_rows": len(src_rows),
                "target_rows_with_matching_ids": len(tgt_rows),
                "source_primary_key": src_pk,
                "target_entity": target_entity,
            }
            details[entity] = entity_details

        return {
            "match": all_match,
            "details": details
        }

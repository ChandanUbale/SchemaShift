"""services/validation/checksum_validator.py — Sample/checksum comparison source vs target."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class ChecksumValidator:

    @staticmethod
    def _canonical_value(value: Any, parse_json: bool = False) -> Any:
        """Normalize common source/SQL representations before hashing."""
        if parse_json and isinstance(value, str):
            try:
                value = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                pass
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, (int, float, Decimal)):
            try:
                number = Decimal(str(value))
                if number.is_finite():
                    normalized = format(number.normalize(), "f")
                    if "." in normalized:
                        normalized = normalized.rstrip("0").rstrip(".")
                    return {"__number__": normalized or "0"}
                return {"__number__": str(number)}
            except Exception:
                return {"__number__": str(value)}
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: ChecksumValidator._canonical_value(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [ChecksumValidator._canonical_value(item) for item in value]
        return value

    @staticmethod
    def checksum_row(row: dict[str, Any], json_fields: set[str] | None = None) -> str:
        """Deterministic hash of a row's values (excluding _id / auto-generated id)."""
        json_fields = json_fields or set()
        canonical = json.dumps(
            {
                key: ChecksumValidator._canonical_value(value, parse_json=key in json_fields)
                for key, value in row.items() if key not in ("_id", "id")
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def _pk(row: dict[str, Any], pk_field: str) -> Any:
        if row.get(pk_field) is not None:
            return row[pk_field]
        if pk_field == "id" and row.get("_id") is not None:
            return str(row["_id"])
        return None

    @staticmethod
    def _compare_payload(row: dict[str, Any]) -> dict[str, Any]:
        return {
            k: v for k, v in row.items()
            if k not in ("_id", "id")
        }

    @staticmethod
    def validate(
        source_sample: list[dict[str, Any]],
        target_sample: list[dict[str, Any]],
        pk_field: str = "id",
        source_pk_field: str | None = None,
        target_pk_field: str | None = None,
        json_fields: set[str] | None = None,
    ) -> dict[str, Any]:
        source_pk_field = source_pk_field or pk_field
        target_pk_field = target_pk_field or pk_field
        source_map = {}
        for row in source_sample:
            pk = ChecksumValidator._pk(row, source_pk_field)
            if pk is not None:
                source_map[pk] = ChecksumValidator.checksum_row(
                    ChecksumValidator._compare_payload(row), json_fields
                )
        target_map = {}
        for row in target_sample:
            pk = ChecksumValidator._pk(row, target_pk_field)
            if pk is not None:
                target_map[pk] = ChecksumValidator.checksum_row(
                    ChecksumValidator._compare_payload(row), json_fields
                )
        source_keys = set(source_map)
        target_keys = set(target_map)
        common_keys = source_keys & target_keys
        mismatched = [pk for pk in common_keys if source_map[pk] != target_map[pk]]
        missing_in_target = source_keys - target_keys
        checked = len(source_keys)
        matched = len(common_keys) - len(mismatched)
        mismatched.extend(pk for pk in missing_in_target if pk not in mismatched)
        return {
            "checked": checked,
            "matched": matched,
            "summary": f"{matched}/{checked}" if checked else "0/0",
            "mismatched_pks": mismatched,
            "missing_in_target": len(missing_in_target),
            "note": "Compares all sample fields except source/target identifiers.",
        }

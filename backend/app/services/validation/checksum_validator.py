"""services/validation/checksum_validator.py — Sample/checksum comparison source vs target."""

import hashlib
from typing import Any


class ChecksumValidator:

    @staticmethod
    def checksum_row(row: dict[str, Any]) -> str:
        """
        Compute a deterministic hash of a row's values (excluding _id / auto-generated fields).
        TODO: sort keys, encode values as str, SHA-256 hash.
        """
        canonical = str(sorted((k, str(v)) for k, v in row.items() if k not in ("_id", "id")))
        return hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def validate(
        source_sample: list[dict[str, Any]],
        target_sample: list[dict[str, Any]],
        pk_field: str = "id",
    ) -> dict[str, Any]:
        """
        Compare checksums of matched source and target rows (joined on pk_field).

        Returns:
            {
                "checked": int,
                "matched": int,
                "summary": "100/100",
                "mismatched_pks": [...]
            }

        TODO: build {pk: checksum} dicts for source and target, compare.
        """
        raise NotImplementedError("TODO: implement ChecksumValidator.validate")

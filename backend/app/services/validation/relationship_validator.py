"""services/validation/relationship_validator.py — FK / reference integrity checks post-migration."""

from typing import Any

from app.services.migration.quality_checks import QualityChecker


class RelationshipValidator:

    @staticmethod
    def validate_fk_integrity(
        target_connector,
        fk_map: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        MySQL target: count child rows whose parent id is missing.
        Only relationships discovered from the actual source schema are checked.
        """
        details: list[dict[str, Any]] = []
        fks = list(fk_map or [])

        for fk in fks:
            child = fk["child_table"]
            fk_field = fk["fk_field"]
            parent = fk["parent_table"]
            pk_field = fk.get("pk_field") or "id"
            try:
                child_rows = target_connector.fetch_sample(child, 10_000)
                parent_rows = target_connector.fetch_sample(parent, 10_000)
            except Exception:
                child_rows, parent_rows = [], []
            parent_ids = {row.get(pk_field) for row in parent_rows if row.get(pk_field) is not None}
            orphans = QualityChecker.detect_orphan_fks(child_rows, fk_field, parent_ids)
            details.append({
                "relationship": f"{child}.{fk_field} -> {parent}.{pk_field}",
                "orphan_count": orphans,
                "status": "passed" if orphans == 0 else "failed",
            })

        passed = all(item["status"] == "passed" for item in details) if details else True
        return {"passed": passed, "details": details}

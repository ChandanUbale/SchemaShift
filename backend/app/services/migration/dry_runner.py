"""
services/migration/dry_runner.py — Dry run: detect issues WITHOUT writing to the target.

Hard rule: this module never imports writers or WriterFactory, and never calls write_batch.
It reads a source sample, runs the transformer in memory, and returns issues.
"""

from collections import Counter
from datetime import date, datetime
from typing import Any

from app.services.profiling.quality_checker import QualityChecker

_REQUIRED = {
    "customers": ("name", "email"),
    "order_items": ("quantity",),
    "items": ("quantity",),
}

_REL_ORPHANS = (
    ("orders", "customer_id", "customers"),
    ("order_items", "order_id", "orders"),
)


def default_plan(source_type: str, plan_id: str | None = None) -> dict[str, Any]:
    """Shop fixture plan when recommendation_plans is not available yet."""
    if (source_type or "").lower() == "mongodb":
        return {
            "plan_id": plan_id,
            "direction": "document_to_relational",
            "target_type": "mysql",
            "flatten": [
                {"table": "customers", "from_path": "$"},
                {"table": "orders", "from_path": "$.orders", "parent_fk": "customer_id"},
                {"table": "order_items", "from_path": "$.orders.items", "parent_fk": "order_id"},
            ],
        }
    return {
        "plan_id": plan_id,
        "direction": "relational_to_document",
        "target_type": "mongodb",
    }


def _issue(table: str, issue_type: str, row_count: int, description: str) -> dict[str, Any] | None:
    if row_count <= 0:
        return None
    return {
        "table_or_collection": table,
        "issue_type": issue_type,
        "row_count": row_count,
        "description": description,
    }


def _pk(row: dict[str, Any]) -> Any:
    if row.get("id") is not None:
        return row["id"]
    if row.get("_id") is not None:
        return str(row["_id"])
    return None


def _looks_like_date_field(name: str) -> bool:
    lowered = name.lower()
    return "date" in lowered or lowered.endswith("_at") or "time" in lowered


def _count_invalid_dates(values: list[Any]) -> int:
    """Same rules as QualityChecker.detect_invalid_dates (copied; no writer imports)."""
    invalid = 0
    for value in values:
        if value is None or isinstance(value, (date, datetime)):
            continue
        if isinstance(value, str):
            if value == "0000-00-00" or value.startswith("0000-00-00"):
                invalid += 1
                continue
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                invalid += 1
    return invalid


def _date_values(rows: list[dict[str, Any]]) -> list[Any]:
    values = []
    for row in rows:
        for key, value in row.items():
            if isinstance(value, (list, dict)):
                continue
            if _looks_like_date_field(key):
                values.append(value)
    return values


def _explode_documents(docs: list[dict[str, Any]]) -> dict[str, list[dict]]:
    customers: list[dict] = []
    orders: list[dict] = []
    items: list[dict] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        customers.append(doc)
        for order in doc.get("orders") or []:
            if not isinstance(order, dict):
                continue
            orders.append(order)
            for item in order.get("items") or []:
                if isinstance(item, dict):
                    items.append(item)
    return {"customers": customers, "orders": orders, "order_items": items}


def _as_tables(source_data: Any, direction: str) -> dict[str, list[dict]]:
    if isinstance(source_data, dict):
        values = {key: list(rows or []) for key, rows in source_data.items()}
        if direction == "document_to_relational" and len(values) == 1:
            only = next(iter(values.values()))
            if only and isinstance(only[0], dict) and isinstance(only[0].get("orders"), list):
                return _explode_documents(only)
        return values
    if isinstance(source_data, list):
        if direction == "document_to_relational" or (
            source_data and isinstance(source_data[0], dict) and isinstance(source_data[0].get("orders"), list)
        ):
            return _explode_documents(source_data)
        return {"customers": source_data}
    return {}


def _scan_table(name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not rows:
        return issues

    pk_field = "id" if any("id" in row for row in rows) else "_id"
    dupes = QualityChecker.detect_duplicate_pks(rows, pk_field)
    if pk_field == "_id" and dupes == 0:
        dupes = QualityChecker.detect_duplicate_pks(rows, "id")
    # Counter fallback when the first row lacks the pk key QualityChecker requires
    if dupes == 0:
        keys = [_pk(row) for row in rows if _pk(row) is not None]
        dupes = sum(count for count in Counter(keys).values() if count > 1)
    found = _issue(
        name, "duplicate_pk", dupes,
        f"{dupes} row(s) share a duplicate id/_id in the {name} sample",
    )
    if found:
        issues.append(found)

    invalid = _count_invalid_dates(_date_values(rows))
    found = _issue(
        name, "invalid_date", invalid,
        f"{invalid} date value(s) in {name} failed ISO-8601 parsing",
    )
    if found:
        issues.append(found)

    for field in _REQUIRED.get(name, ()):
        missing = sum(1 for row in rows if row.get(field) is None)
        found = _issue(
            name, "missing_field", missing,
            f"{missing} {name} row(s) have required field '{field}' as null",
        )
        if found:
            issues.append(found)
    return issues


def _scan_orphans(tables: dict[str, list[dict]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for child, fk_field, parent in _REL_ORPHANS:
        child_rows = tables.get(child) or []
        parent_ids = {_pk(row) for row in tables.get(parent) or [] if _pk(row) is not None}
        orphans = QualityChecker.detect_orphan_fks(child_rows, fk_field, parent_ids)
        found = _issue(
            child, "orphan_fk", orphans,
            f"{orphans} {child} row(s) have {fk_field} missing from sampled {parent}",
        )
        if found:
            issues.append(found)
    return issues


def _try_transform(source_data: Any, transformer, plan: dict[str, Any]) -> dict[str, Any] | None:
    direction = plan.get("direction") or "relational_to_document"
    try:
        if direction == "relational_to_document":
            tables = source_data if isinstance(source_data, dict) else {"customers": source_data}
            transformer.transform_batch(tables, direction)
            return None
        docs = source_data if isinstance(source_data, list) else next(iter(source_data.values()), [])
        try:
            transformer.transform_batch(
                source_data if isinstance(source_data, dict) else {"customers": docs},
                direction,
            )
            return None
        except (NotImplementedError, ValueError):
            for doc in docs or []:
                if isinstance(doc, dict):
                    transformer.transform_row(doc, direction)
            return None
    except NotImplementedError:
        return None
    except TypeError as exc:
        return _issue("transform", "type_mismatch", 1, str(exc))
    except Exception as exc:
        msg = str(exc)
        if "does not support" in msg or "TODO" in msg:
            return None
        return _issue("transform", "transform_error", 1, msg)


class DryRunner:

    @staticmethod
    def run(
        source_data: Any,
        transformer,
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Transform a source sample in memory and collect issues. No target writes.

        source_data:
            relational_to_document → {table: rows}
            document_to_relational → list[dict] documents (or {collection: docs})
        """
        plan = plan or {}
        direction = plan.get("direction") or "relational_to_document"
        tables = _as_tables(source_data, direction)
        issues: list[dict[str, Any]] = []
        for name, rows in tables.items():
            issues.extend(_scan_table(name, rows))
        issues.extend(_scan_orphans(tables))
        transform_issue = _try_transform(source_data, transformer, plan)
        if transform_issue:
            issues.append(transform_issue)
        return issues

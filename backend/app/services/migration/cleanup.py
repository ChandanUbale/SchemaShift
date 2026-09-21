"""
Explicit target cleanup/reset for a finished migration job.

Never opens the source connection. Never deletes audit_log entries.
"""

from typing import Any

SOURCE_CLEANUP_FORBIDDEN = "Cleanup must not drop the source"
DRY_RUN_HAS_NO_TARGET = "Dry-run jobs have no target to clean up"
TARGET_MISMATCH = "target_connection_id does not match this job"

_SHOP_MYSQL = ("order_items", "orders", "customers")
_SHOP_MONGO = ("customers",)
_MYSQL_DROP_RANK = {"order_items": 0, "orders": 1, "customers": 2}


def entities_from_audit(audit_log: list[dict] | None, target_type: str) -> list[str]:
    """Unique entity names from the job audit log, children first for MySQL FKs."""
    names: list[str] = []
    seen: set[str] = set()
    for entry in audit_log or []:
        entity = entry.get("entity")
        if not entity or entity == "cleanup" or entity in seen:
            continue
        seen.add(entity)
        names.append(entity)
    if not names:
        names = list(_SHOP_MONGO if (target_type or "").lower() == "mongodb" else _SHOP_MYSQL)
    if (target_type or "").lower() == "mysql":
        names.sort(key=lambda name: _MYSQL_DROP_RANK.get(name, 50))
    return names


def require_cleanup_allowed(job: Any, target_connection_id: int) -> None:
    if job is None:
        raise ValueError("Job not found")
    if getattr(job, "is_dry_run", False):
        raise ValueError(DRY_RUN_HAS_NO_TARGET)
    source_id = getattr(job, "source_connection_id", None)
    if source_id is not None and source_id == target_connection_id:
        raise ValueError(SOURCE_CLEANUP_FORBIDDEN)
    job_target = getattr(job, "target_connection_id", None)
    if job_target is not None and job_target != target_connection_id:
        raise ValueError(TARGET_MISMATCH)


def seed_writer_for_cleanup(writer, entities: list[str]) -> None:
    """
    Fresh writer instances have empty in-memory tracking sets.
    Fill them from the job audit log so writer.cleanup(job_id) drops the right entities.
    """
    if hasattr(writer, "_created_tables"):
        if getattr(writer, "_conn", None) is None and hasattr(writer, "_get_connection"):
            writer._conn = writer._get_connection()
        writer._created_tables.update(entities)
    if hasattr(writer, "_collection_names"):
        if getattr(writer, "_db", None) is None and hasattr(writer, "prepare"):
            writer.prepare(getattr(writer, "_plan", None) or {})
        writer._collection_names.update(entities)


def cleanup_entry() -> dict[str, Any]:
    return {
        "batch_index": -1,
        "entity": "cleanup",
        "rows": 0,
        "ok": True,
        "attempts": 1,
        "error": None,
    }

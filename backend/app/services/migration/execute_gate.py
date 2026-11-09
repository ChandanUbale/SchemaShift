"""
Approval checks for POST /api/migration/execute.

Raises ValueError with the API error message. The router turns those into HTTP 400.
Does not write to any target.
"""

from typing import Any

DRY_RUN_REQUIRED = "Run dry-run before execute"
PLAN_REQUIRED = "plan_id does not exist"


def require_plan_id(plan_id: str | None) -> None:
    if not (plan_id or "").strip():
        raise ValueError(PLAN_REQUIRED)


def _status_is_done(status: Any) -> bool:
    return str(getattr(status, "value", status)).lower() == "done"


def require_successful_dry_run(job: Any) -> None:
    if job is None or not _status_is_done(getattr(job, "status", None)):
        raise ValueError(DRY_RUN_REQUIRED)


def apply_target_collection(plan: dict[str, Any], collection_name: str | None) -> dict[str, Any]:
    """Rename the primary MongoDB output collection when the user requested one."""
    name = (collection_name or "").strip()
    if not name or (plan or {}).get("target_type") != "mongodb":
        return plan
    if "\x00" in name or name.startswith("system."):
        raise ValueError("Choose a valid non-system MongoDB collection name.")

    out = dict(plan)
    if out.get("model_tree"):
        out["model_tree"] = {**out["model_tree"], "collection": name}
    trees = out.get("model_trees")
    if trees:
        out["model_trees"] = [
            {**tree, "collection": name} if index == 0 else tree
            for index, tree in enumerate(trees)
        ]
    return out

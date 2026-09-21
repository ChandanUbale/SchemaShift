"""
Approval checks for POST /api/migration/execute.

Raises ValueError with the API error message. The router turns those into HTTP 400.
Does not write to any target.
"""

from typing import Any

DRY_RUN_REQUIRED = "Run dry-run before execute"
HIGH_RISK_REQUIRED = "Profiling risk is High. Set confirm_high_risk=true to proceed."
PLAN_REQUIRED = "plan_id does not exist"


def shop_plan(source_type: str, plan_id: str | None = None) -> dict[str, Any]:
    """Fixture plan when recommendation_plans is not persisted yet."""
    if (source_type or "").lower() == "mongodb":
        return {
            "plan_id": plan_id,
            "direction": "document_to_relational",
            "target_type": "mysql",
        }
    return {
        "plan_id": plan_id,
        "direction": "relational_to_document",
        "target_type": "mongodb",
    }


def require_plan_id(plan_id: str | None) -> None:
    if not (plan_id or "").strip():
        raise ValueError(PLAN_REQUIRED)


def _status_is_done(status: Any) -> bool:
    return str(getattr(status, "value", status)).lower() == "done"


def require_successful_dry_run(job: Any) -> None:
    if job is None or not _status_is_done(getattr(job, "status", None)):
        raise ValueError(DRY_RUN_REQUIRED)


def require_high_risk_confirm(risk_label: str | None, confirm_high_risk: bool) -> None:
    if risk_label is None:
        return
    if str(risk_label).lower() == "high" and not confirm_high_risk:
        raise ValueError(HIGH_RISK_REQUIRED)


def apply_override(plan: dict[str, Any], override: str | None) -> dict[str, Any]:
    """User override wins for this job only — do not rescore."""
    out = dict(plan)
    if override in ("mysql", "mongodb") and override != out.get("target_type"):
        out["target_type"] = override
        out["direction"] = (
            "document_to_relational" if override == "mysql" else "relational_to_document"
        )
    return out

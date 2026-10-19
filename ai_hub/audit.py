"""Structured offline audit metadata. Never write secrets or user prompts."""
from datetime import datetime, timezone
from uuid import uuid4

ALLOWED_EVENTS = {"planned", "disabled", "provider_selected", "permission_pending",
                  "permission_configured", "budget_rejected", "quality_rejected", "test_failed"}

def event(kind, project_id, reason, provider=None, estimated_cost="0"):
    if kind not in ALLOWED_EVENTS:
        raise ValueError("Unknown audit event")
    if not isinstance(project_id, str) or not project_id or len(project_id) > 100:
        raise ValueError("Invalid project ID")
    if reason not in {"feature_flag_off", "lowest_cost_meeting_quality_and_budget",
                      "no_quality_qualified_provider_within_budget",
                      "permission_required", "test_only"}:
        raise ValueError("Unknown reason code")
    return {"event_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind, "project_id": project_id, "reason_code": reason,
            "provider": provider, "estimated_cost": str(estimated_cost)}

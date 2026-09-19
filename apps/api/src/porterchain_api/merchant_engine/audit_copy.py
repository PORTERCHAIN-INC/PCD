"""English labels for merchant company audit rows (not RBAC catalogs)."""

from __future__ import annotations

from typing import Any

ACTION_SUMMARIES: dict[str, str] = {
    "privacy.delete_requested": "Deletion requested",
    "privacy.erasure_completed": "Contact details erased",
    "contacts.created": "Contact added",
    "contacts.updated": "Contact updated",
    "contacts.deleted": "Contact removed",
    "invoice.reminded": "Invoice reminder sent",
    "team.seat_added": "Teammate added",
    "team.removed": "Teammate turned off",
    "team.role_updated": "Teammate role changed",
    "merchant.owner_seat_added": "Owner seat added",
    "merchant.member_seat_added": "Teammate added",
    "merchant.terms_updated": "Payment terms updated",
    "support.ticket_created": "Support ticket opened",
    "claim.opened": "Claim opened",
    "settings.notifications": "Notification preferences updated",
    "settings.branding": "Branding updated",
    "api_key.created": "API key created",
    "api_key.revoked": "API key revoked",
}


def summarize_audit_action(action: str) -> str:
    mapped = ACTION_SUMMARIES.get(action)
    if mapped:
        return mapped
    words = action.replace(".", " ").replace("_", " ").split()
    return " ".join(part.capitalize() for part in words if part) or "Company update"


def serialize_audit_log(row: Any, *, include_payload: bool = False) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": row.id,
        "action": row.action,
        "summary": summarize_audit_action(row.action),
        "actor_user_id": row.actor_user_id,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
    if include_payload:
        item["payload"] = row.payload or {}
    return item

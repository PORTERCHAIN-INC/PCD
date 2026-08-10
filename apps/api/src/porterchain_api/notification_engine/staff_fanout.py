"""RBAC-based staff fan-out for ops / finance / support topics."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.admin_models import AdminUser
from porterchain_api.domain.admin_states import AdminRole

StaffTopic = Literal["ops", "finance", "support"]

TOPIC_MODULE: dict[StaffTopic, str] = {
    "ops": "dispatch",
    "finance": "finance",
    "support": "support",
}

STAFF_SENTINEL_PREFIX = "__staff:"
FANOUT_CAP = 100


def staff_sentinel(topic: StaffTopic) -> str:
    return f"{STAFF_SENTINEL_PREFIX}{topic}__"


def parse_staff_topic(recipient_id: str) -> StaffTopic | None:
    if not recipient_id.startswith(STAFF_SENTINEL_PREFIX) or not recipient_id.endswith("__"):
        return None
    topic = recipient_id[len(STAFF_SENTINEL_PREFIX) : -2]
    if topic in TOPIC_MODULE:
        return topic  # type: ignore[return-value]
    return None


def roles_for_topic(topic: StaffTopic) -> frozenset[str]:
    module = TOPIC_MODULE[topic]
    allowed = MODULE_PERMISSIONS[module]
    return frozenset(r.value if isinstance(r, AdminRole) else str(r) for r in allowed)


def resolve_staff_recipients(
    db: Session,
    topic: StaffTopic,
    *,
    limit: int = FANOUT_CAP,
) -> list[AdminUser]:
    roles = roles_for_topic(topic)
    return (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True), AdminUser.role.in_(roles))
        .order_by(AdminUser.created_at.desc())
        .limit(limit)
        .all()
    )


def expand_staff_specs(db: Session, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace `__staff:{topic}__` recipient_ids with real AdminUser rows.

    Inbox principal is always recipient_type=admin for staff portals.
    """
    out: list[dict[str, Any]] = []
    for spec in specs:
        topic = parse_staff_topic(str(spec.get("recipient_id") or ""))
        if topic is None:
            out.append(spec)
            continue
        users = resolve_staff_recipients(db, topic)
        tags = dict(spec.get("search_tags") or {})
        tags["fanout_topic"] = topic
        for user in users:
            expanded = {
                **spec,
                "recipient_type": "admin",
                "recipient_id": user.id,
                "search_tags": tags,
            }
            if spec.get("channel") == "email":
                if not user.email:
                    continue
                expanded["recipient_address"] = user.email
            out.append(expanded)
    return out

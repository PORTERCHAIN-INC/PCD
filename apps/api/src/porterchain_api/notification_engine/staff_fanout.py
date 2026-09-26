"""RBAC-based staff fan-out for ops / finance / support topics."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.admin_models import AdminUser
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.notification_engine.models import NotificationDevice

StaffTopic = Literal["ops", "finance", "support", "growth"]

TOPIC_MODULE: dict[StaffTopic, str] = {
    "ops": "dispatch",
    "finance": "finance",
    "support": "support",
    "growth": "crm",
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


def _admin_ids_with_active_push(db: Session, user_ids: list[str]) -> set[str]:
    if not user_ids:
        return set()
    rows = (
        db.query(NotificationDevice.user_id)
        .filter(
            NotificationDevice.user_role == "admin",
            NotificationDevice.user_id.in_(user_ids),
            NotificationDevice.is_active.is_(True),
        )
        .distinct()
        .all()
    )
    return {str(r[0]) for r in rows if r[0]}


def expand_staff_specs(db: Session, specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replace `__staff:{topic}__` recipient_ids with real AdminUser rows.

    Inbox principal is always recipient_type=admin for staff portals.

    Push fan-out (Jeff Dean): only queue FCM for admins with an active device.
    High/critical staff without a device get an email fallback row instead of a
    doomed push that burns retries.
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
        channel = str(spec.get("channel") or "")
        priority = str(spec.get("priority") or "normal")
        push_capable: set[str] = set()
        if channel == "push":
            push_capable = _admin_ids_with_active_push(db, [u.id for u in users])

        for user in users:
            expanded = {
                **spec,
                "recipient_type": "admin",
                "recipient_id": user.id,
                "search_tags": tags,
            }
            ctx = dict(spec.get("context") or {})
            if user.email:
                ctx.setdefault("email", user.email)
                ctx.setdefault("contact_email", user.email)
            phone = user.phone
            if not phone and user.porterchain_user_id:
                from porterchain_api.user_models import PorterchainUser

                pc = db.get(PorterchainUser, user.porterchain_user_id)
                if pc and pc.phone:
                    phone = pc.phone
            if phone:
                ctx.setdefault("phone", phone)
                ctx.setdefault("contact_phone", phone)
            expanded["context"] = ctx

            if channel == "email":
                if not user.email:
                    continue
                expanded["recipient_address"] = user.email
                out.append(expanded)
                continue

            if channel == "push":
                if user.id in push_capable:
                    out.append(expanded)
                    continue
                # No device: fail closed via email for ops risk only.
                if priority in ("critical", "high") and user.email:
                    email_spec = {
                        **expanded,
                        "channel": "email",
                        "recipient_address": user.email,
                        "search_tags": {**tags, "fallback_reason": "no_active_push_device"},
                    }
                    out.append(email_spec)
                continue

            out.append(expanded)
    return out

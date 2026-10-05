"""Zepto bounce and complaint — stop retrying an address that rejected the mail."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationRecord

_BOUNCE_EVENTS = frozenset(
    {
        "hardbounce",
        "hard_bounce",
        "softbounce",
        "soft_bounce",
        "bounce",
        "complaint",
        "spam",
    }
)


def _clean(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    if "@" not in text:
        return None
    return text


def _walk_addresses(node: Any, found: list[str]) -> None:
    if isinstance(node, dict):
        for key in ("address", "email", "recipient"):
            cleaned = _clean(node.get(key))
            if cleaned:
                found.append(cleaned)
        email_address = node.get("email_address")
        if isinstance(email_address, dict):
            cleaned = _clean(email_address.get("address"))
            if cleaned:
                found.append(cleaned)
        for value in node.values():
            _walk_addresses(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_addresses(item, found)


def is_bounce_event(body: dict[str, Any]) -> bool:
    raw = body.get("event_name") or body.get("event") or body.get("type") or ""
    if isinstance(raw, list):
        names = [str(item).lower() for item in raw]
    else:
        names = [str(raw).lower()]
    return any(name in _BOUNCE_EVENTS or "bounce" in name or "complaint" in name for name in names)


def extract_bounced_addresses(body: dict[str, Any]) -> list[str]:
    found: list[str] = []
    _walk_addresses(body, found)
    seen: set[str] = set()
    unique: list[str] = []
    for address in found:
        if address in seen:
            continue
        seen.add(address)
        unique.append(address)
    return unique


def mark_addresses_bounced(db: Session, addresses: list[str]) -> int:
    """Mark open email rows bounced so the retry sweep will not send them again."""
    if not addresses:
        return 0
    lowered = {address.lower() for address in addresses}
    rows = (
        db.query(NotificationRecord)
        .filter(
            NotificationRecord.channel == "email",
            NotificationRecord.status.in_(("queued", "failed", "deferred")),
        )
        .all()
    )
    marked = 0
    for row in rows:
        address = (row.recipient_address or "").strip().lower()
        if address not in lowered:
            continue
        row.status = "bounced"
        row.failure_reason = "email_bounced"
        row.next_retry_at = None
        marked += 1
    if marked:
        db.commit()
    return marked


def address_is_bounced(db: Session, recipient: str) -> bool:
    address = (recipient or "").strip().lower()
    if "@" not in address:
        return False
    rows = (
        db.query(NotificationRecord.recipient_address)
        .filter(NotificationRecord.channel == "email", NotificationRecord.status == "bounced")
        .all()
    )
    return any((row[0] or "").strip().lower() == address for row in rows)

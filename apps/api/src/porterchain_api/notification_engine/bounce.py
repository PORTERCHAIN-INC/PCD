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
    """True when the address is on the active suppression list."""
    from porterchain_api.notification_engine.models import EmailSuppression

    address = (recipient or "").strip().lower()
    if "@" not in address:
        return False
    row = db.get(EmailSuppression, address)
    return bool(row is not None and row.active)


#: Webhook event name -> what it means for one message.
_TRACK_EVENTS: dict[str, str] = {
    "delivered": "delivered",
    "email_delivered": "delivered",
    "delivery": "delivered",
    "email_open": "opened",
    "open": "opened",
    "opened": "opened",
    "email_link_click": "clicked",
    "click": "clicked",
    "hardbounce": "hard_bounce",
    "hard_bounce": "hard_bounce",
    "softbounce": "soft_bounce",
    "soft_bounce": "soft_bounce",
    "bounce": "hard_bounce",
    "complaint": "complaint",
    "spam": "complaint",
}


def event_kinds(body: dict[str, Any]) -> list[str]:
    raw = body.get("event_name") or body.get("event") or body.get("type") or ""
    names = raw if isinstance(raw, list) else [raw]
    out = []
    for name in names:
        kind = _TRACK_EVENTS.get(str(name).strip().lower())
        if kind and kind not in out:
            out.append(kind)
    return out


def _find_refs(node: Any, found: list[str]) -> None:
    if isinstance(node, dict):
        for key in ("client_reference", "request_id", "message_id"):
            val = node.get(key)
            if isinstance(val, str) and 4 <= len(val) <= 128:
                found.append(val.strip())
        for value in node.values():
            _find_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            _find_refs(item, found)


def suppress(db: Session, address: str, *, reason: str, source: str = "zeptomail", notification_id: str | None = None) -> None:
    from datetime import UTC, datetime

    from porterchain_api.notification_engine.models import EmailSuppression

    email = (address or "").strip().lower()
    if "@" not in email:
        return
    row = db.get(EmailSuppression, email)
    if row is None:
        db.add(
            EmailSuppression(
                email=email, reason=reason, source=source, active=True, bounce_count=1, notification_id=notification_id
            )
        )
    else:
        row.active = True
        row.reason = reason
        row.bounce_count = int(row.bounce_count or 0) + 1
        row.notification_id = notification_id or row.notification_id
        row.released_at = None
        row.released_by = None
        row.updated_at = datetime.now(UTC)
    db.flush()


def record_tracking_event(db: Session, body: dict[str, Any]) -> dict[str, int]:
    """Apply one ZeptoMail webhook: per-message delivered/opened/bounced + suppression.

    Hard bounces and complaints suppress the address. Soft bounces only mark the
    message (the mailbox may be full today, fine tomorrow).
    """
    from datetime import UTC, datetime

    kinds = event_kinds(body)
    refs: list[str] = []
    _find_refs(body, refs)
    rows = (
        db.query(NotificationRecord).filter(NotificationRecord.provider_message_id.in_(set(refs))).all()
        if refs
        else []
    )
    now = datetime.now(UTC)
    updated = 0
    for row in rows:
        for kind in kinds:
            if kind == "delivered":
                row.delivered_at = row.delivered_at or now
                if row.delivery_status not in ("opened", "clicked", "hard_bounce", "complaint"):
                    row.delivery_status = "delivered"
            elif kind in ("opened", "clicked"):
                row.opened_at = row.opened_at or now
                if kind == "clicked":
                    row.clicked_at = row.clicked_at or now
                row.delivered_at = row.delivered_at or now
                row.delivery_status = kind
            else:
                row.bounced_at = row.bounced_at or now
                row.delivery_status = kind
                if row.status in ("sent", "queued", "failed", "deferred"):
                    row.status = "bounced"
                    row.failure_reason = f"email_{kind}"
        updated += 1
    suppressed = 0
    hard = [k for k in kinds if k in ("hard_bounce", "complaint")]
    if hard:
        targets = {(r.recipient_address or "").strip().lower(): r.id for r in rows if r.recipient_address}
        if not targets:
            # No message match: fall back to addresses in the payload, never our own senders.
            targets = {a: None for a in extract_bounced_addresses(body) if not a.endswith("@porterchain.com")}
        for address, nid in targets.items():
            suppress(db, address, reason=hard[0], notification_id=nid)
            suppressed += 1
        mark_addresses_bounced(db, list(targets))
    db.commit()
    return {"messages": updated, "suppressed": suppressed}

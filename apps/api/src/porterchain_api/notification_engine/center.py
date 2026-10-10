"""Admin notification center: one read model for the log, dead letters, suppressions,
speed metrics, templates, the event x persona matrix and the daily ops digest."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, time, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import (
    EmailSuppression,
    NotificationDeliveryLog,
    NotificationRecord,
)

logger = logging.getLogger(__name__)
TORONTO = ZoneInfo("America/Toronto")
OUTBOUND = ("email", "sms", "push")
DELIVERED_STATES = ("delivered", "opened", "clicked")
BOUNCE_STATES = ("hard_bounce", "soft_bounce", "complaint")


# --- log ---------------------------------------------------------------------------


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _latency_ms(r: NotificationRecord) -> int | None:
    if r.sent_at and r.created_at:
        return max(0, int((r.sent_at - r.created_at).total_seconds() * 1000))
    return None


def row_dict(r: NotificationRecord) -> dict[str, Any]:
    persona = "receiver" if r.recipient_type == "consignee" else r.recipient_type
    return {
        "id": r.id,
        "created_at": _iso(r.created_at),
        "event": r.event_type,
        "template": r.template_key,
        "channel": r.channel,
        "persona": persona,
        "recipient": r.recipient_address,
        "title": r.title,
        "status": r.status,
        "delivery": r.delivery_status,
        "failure": r.failure_reason,
        "retries": r.retry_count,
        "latency_ms": _latency_ms(r),
        "sent_at": _iso(r.sent_at),
        "delivered_at": _iso(r.delivered_at) if r.channel != "email" or r.delivery_status in DELIVERED_STATES else None,
        "opened_at": _iso(r.opened_at) if r.channel == "email" else None,
        "bounced_at": _iso(r.bounced_at),
        "order_id": (r.search_tags or {}).get("order_id"),
        "tracking_number": (r.search_tags or {}).get("tracking_number"),
    }


def list_log(
    db: Session,
    *,
    persona: str | None = None,
    event: str | None = None,
    status: str | None = None,
    channel: str | None = None,
    q: str | None = None,
    limit: int = 100,
    before: datetime | None = None,
) -> list[dict[str, Any]]:
    query = db.query(NotificationRecord).filter(NotificationRecord.is_sandbox.is_(False))
    if persona:
        types = ["consignee", "customer"] if persona == "receiver" else [persona]
        query = query.filter(NotificationRecord.recipient_type.in_(types))
    if event:
        query = query.filter(or_(NotificationRecord.event_type == event, NotificationRecord.template_key == event))
    if status:
        if status == "bounced":
            query = query.filter(or_(NotificationRecord.status == "bounced", NotificationRecord.delivery_status.in_(BOUNCE_STATES)))
        elif status in DELIVERED_STATES:
            query = query.filter(NotificationRecord.delivery_status == status)
        else:
            query = query.filter(NotificationRecord.status == status)
    if channel:
        query = query.filter(NotificationRecord.channel == channel)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(NotificationRecord.recipient_address).like(like),
                func.lower(NotificationRecord.title).like(like),
                NotificationRecord.id == q.strip(),
            )
        )
    if before:
        query = query.filter(NotificationRecord.created_at < before)
    rows = query.order_by(NotificationRecord.created_at.desc()).limit(max(1, min(limit, 500))).all()
    return [row_dict(r) for r in rows]


def detail(db: Session, notification_id: str) -> dict[str, Any] | None:
    r = db.get(NotificationRecord, notification_id)
    if r is None:
        return None
    logs = (
        db.query(NotificationDeliveryLog)
        .filter(NotificationDeliveryLog.notification_id == notification_id)
        .order_by(NotificationDeliveryLog.created_at.asc())
        .limit(50)
        .all()
    )
    suppressed = None
    if r.channel == "email" and r.recipient_address:
        sup = db.get(EmailSuppression, r.recipient_address.strip().lower())
        suppressed = bool(sup and sup.active)
    return {
        **row_dict(r),
        "body": r.body,
        "html": r.html_body,
        "priority": r.priority,
        "category": r.category,
        "deep_link": r.deep_link,
        "next_retry_at": _iso(r.next_retry_at),
        "suppressed": suppressed,
        "attempts": [
            {"at": _iso(x.created_at), "status": x.status, "error": x.error} for x in logs
        ],
        "replayable": r.status in ("failed", "dead_letter"),
    }


# --- dead letters / suppressions ---------------------------------------------------


def dead_letters(db: Session, *, limit: int = 100) -> list[dict[str, Any]]:
    rows = (
        db.query(NotificationRecord)
        .filter(NotificationRecord.status == "dead_letter")
        .order_by(NotificationRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [row_dict(r) for r in rows]


def replay(db: Session, notification_id: str) -> bool:
    from porterchain_api.notification_engine.engine import get_notification_engine

    return get_notification_engine().requeue(db, notification_id)


def replay_all(db: Session, *, limit: int = 50) -> int:
    ids = [r.id for r in db.query(NotificationRecord.id).filter(NotificationRecord.status == "dead_letter").limit(limit).all()]
    return sum(1 for nid in ids if replay(db, nid))


def suppressions(db: Session, *, include_released: bool = False, limit: int = 200) -> list[dict[str, Any]]:
    q = db.query(EmailSuppression)
    if not include_released:
        q = q.filter(EmailSuppression.active.is_(True))
    rows = q.order_by(EmailSuppression.updated_at.desc()).limit(limit).all()
    return [
        {
            "email": r.email,
            "reason": r.reason,
            "source": r.source,
            "active": r.active,
            "count": r.bounce_count,
            "since": _iso(r.created_at),
            "updated_at": _iso(r.updated_at),
            "released_by": r.released_by,
            "notification_id": r.notification_id,
        }
        for r in rows
    ]


def unsuppress(db: Session, email: str, *, author: str | None) -> bool:
    row = db.get(EmailSuppression, (email or "").strip().lower())
    if row is None or not row.active:
        return False
    row.active = False
    row.released_by = author
    row.released_at = datetime.now(UTC)
    db.commit()
    return True


# --- speed metrics -----------------------------------------------------------------


def _pct(values: list[int], p: float) -> int | None:
    if not values:
        return None
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round(p * (len(values) - 1)))))
    return values[k]


def metrics(db: Session, *, hours: int = 24, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    since = now - timedelta(hours=hours)
    rows = (
        db.query(
            NotificationRecord.channel,
            NotificationRecord.status,
            NotificationRecord.delivery_status,
            NotificationRecord.created_at,
            NotificationRecord.sent_at,
        )
        .filter(
            NotificationRecord.created_at >= since,
            NotificationRecord.channel.in_(OUTBOUND),
            NotificationRecord.is_sandbox.is_(False),
        )
        .limit(20000)
        .all()
    )
    email = [r for r in rows if r.channel == "email"]
    latencies = [
        int((r.sent_at - r.created_at).total_seconds() * 1000) for r in email if r.sent_at and r.created_at
    ]
    accepted = [r for r in email if r.sent_at]
    delivered = [r for r in accepted if r.delivery_status in DELIVERED_STATES]
    opened = [r for r in accepted if r.delivery_status in ("opened", "clicked")]
    bounced = [r for r in email if r.status == "bounced" or r.delivery_status in BOUNCE_STATES]
    failed_statuses = ("failed", "dead_letter", "bounced")
    buckets: dict[str, int] = {}
    start = since.replace(minute=0, second=0, microsecond=0)
    for i in range(hours + 1):
        buckets[(start + timedelta(hours=i)).isoformat()] = 0
    for r in rows:
        if r.status in failed_statuses and r.created_at:
            key = r.created_at.astimezone(UTC).replace(minute=0, second=0, microsecond=0).isoformat()
            if key in buckets:
                buckets[key] += 1
    tracked = sum(1 for r in accepted if r.delivery_status and r.delivery_status != "accepted")

    def rate(n: int, d: int) -> float | None:
        return round(100.0 * n / d, 1) if d else None

    return {
        "window_hours": hours,
        "emails": len(email),
        "accepted": len(accepted),
        "p50_ms": _pct(latencies, 0.50),
        "p95_ms": _pct(latencies, 0.95),
        "delivery_pct": rate(len(delivered), tracked),
        "open_pct": rate(len(opened), tracked),
        "bounce_pct": rate(len(bounced), len(accepted) + len([b for b in bounced if not b.sent_at])),
        "tracked": tracked,
        "queued": sum(1 for r in rows if r.status == "queued"),
        "held": sum(1 for r in rows if r.status == "held"),
        "failed": sum(1 for r in rows if r.status in failed_statuses),
        "dead_letters": db.query(func.count(NotificationRecord.id)).filter(NotificationRecord.status == "dead_letter").scalar() or 0,
        "suppressed": db.query(func.count(EmailSuppression.email)).filter(EmailSuppression.active.is_(True)).scalar() or 0,
        "failures_per_hour": [{"hour": k, "count": v} for k, v in buckets.items()],
        "lanes": _lanes(db, now),
    }


def _lanes(db: Session, now: datetime) -> dict[str, Any]:
    from porterchain_api.notification_engine.health_alert import lane_latency

    return lane_latency(db, now=now, minutes=60)


# --- templates ---------------------------------------------------------------------

SAMPLE: dict[str, Any] = {
    "merchant_name": "Bloor West Pharmacy",
    "company_name": "Bloor West Pharmacy",
    "tracking_number": "PC-20261009-4821",
    "order_number": "ORD-10482",
    "amount_display": "$24.50",
    "invoice_number": "INV-2041",
    "receipt_number": "R-88120",
    "eta_minutes": "18",
    "window_label": "Sat Oct 10, 10:00 AM–12:00 PM",
    "stops_away": 2,
    "public_track_url": "https://porterchain.com/en/track/PC-20261009-4821",
    "signed_track_url": "https://porterchain.com/en/track/PC-20261009-4821?t=sample",
    "manage_url_signed": "https://porterchain.com/en/track/PC-20261009-4821/manage?t=sample",
    "reschedule_url": "https://porterchain.com/en/track/PC-20261009-4821/manage?t=sample",
    "website_url": "https://porterchain.com",
    "support_email": "support@porterchain.com",
    "reason": "No one home, no safe place",
    "reason_line": " Reason: no one home.",
    "message": "Sample message",
    "title": "Sample title",
    "body": "Sample body",
    "contact_name": "Jordan",
    "quote_id": "Q-1042",
    "claim_number": "CL-77",
    "ticket_number": "T-311",
    "code": "482913",
    "dead_letter": "7",
    "failure_rate": "30%",
}


def template_catalog(db: Session) -> list[dict[str, Any]]:
    from porterchain_api.notification_engine.customer_fr import has_french
    from porterchain_api.notification_engine.receiver_emails import RECEIVER_TEMPLATES
    from porterchain_api.notification_engine.template_copy import active_copy
    from porterchain_api.notification_engine.templates import TEMPLATE_META, TEMPLATES

    out = []
    for key in sorted(TEMPLATES):
        receiver = key in RECEIVER_TEMPLATES
        out.append(
            {
                "key": key,
                "category": TEMPLATE_META.get(key, {}).get("category", "operational"),
                "receiver": receiver,
                "french": receiver or has_french(key),
                "edited_en": active_copy(key, "en") is not None,
                "edited_fr": active_copy(key, "fr") is not None,
            }
        )
    return out


def preview(template: str, *, lang: str = "en", audience: str | None = None, draft: dict[str, str] | None = None) -> dict[str, str]:
    from porterchain_api.notification_engine.receiver_emails import RECEIVER_TEMPLATES
    from porterchain_api.notification_engine.templates import TEMPLATES, render_email

    if template not in TEMPLATES:
        raise LookupError("template_not_found")
    from porterchain_api.notification_engine.customer_fr import has_french

    aud = audience or ("receiver" if template in RECEIVER_TEMPLATES or has_french(template) else "business")
    ctx = {**SAMPLE, "audience": aud, "lang": lang if aud == "receiver" else "en"}
    if draft:
        ctx["copy_subject"] = draft.get("subject") or ""
        ctx["copy_intro"] = draft.get("intro") or ""
        ctx["skip_copy_override"] = True
    subject, text, html = render_email(template, ctx)
    return {"template": template, "lang": ctx["lang"], "audience": aud, "subject": subject, "text": text, "html": html}


def send_test(db: Session, template: str, *, lang: str, admin_id: str, admin_email: str) -> dict[str, Any]:
    """Queue one test email to the signed-in admin only (local: Mailpit / log-only)."""
    from porterchain_api.notification_engine.engine import get_notification_engine

    if not admin_email or "@" not in admin_email:
        raise ValueError("admin_email_missing")
    p = preview(template, lang=lang)
    rec = get_notification_engine().dispatch(
        db,
        event_type="notification.template_test",
        template_key=template,
        channel="email",
        recipient_type="admin",
        recipient_id=admin_id,
        recipient_address=admin_email,
        context={**SAMPLE, "audience": p["audience"], "lang": p["lang"], "test_send": True},
        category="security",
        priority="normal",
        correlation_id=str(uuid4()),
        search_tags={"template_test": True},
    )
    db.commit()
    return {"queued": rec is not None, "id": rec.id if rec else None, "to": admin_email}


# --- matrix ------------------------------------------------------------------------

_SAMPLE_PAYLOAD = {
    "order_id": "matrix-order",
    "customer_id": "c",
    "merchant_id": "m",
    "driver_id": "d",
    "email": "customer@example.test",
    "receiver_email": "receiver@example.test",
    "merchant_email": "merchant@example.test",
    "order_number": "O",
    "tracking_number": "T",
    "invoice_number": "I",
    "claim_id": "cl",
    "ticket_id": "tk",
    "status": "IN_TRANSIT",
    "priority": "high",
}
CX_ROWS = ("out_for_delivery", "next_stop", "eta_20", "delivered", "attempted", "rescheduled", "schedule_request")


def matrix(db: Session) -> dict[str, Any]:
    from porterchain_api.notification_engine.center_settings import (
        LOCKED_TEMPLATES,
        PERSONAS,
        matrix_off,
    )
    from porterchain_api.notification_engine.event_router import (
        WATCHED_EVENTS,
        _specs_for_event,
    )

    off = matrix_off(db)
    rows = []
    for kind in CX_ROWS:
        event = f"cx.{kind}"
        rows.append(
            {
                "event": event,
                "group": "Receiver emails",
                "cells": {"receiver": {"channels": ["email"], "on": f"{event}|receiver" not in off, "locked": False}},
            }
        )
    for event in WATCHED_EVENTS:
        try:
            specs = _specs_for_event(str(event), dict(_SAMPLE_PAYLOAD))
        except Exception:  # noqa: BLE001 — a router branch needing real data just shows empty
            specs = []
        cells: dict[str, Any] = {}
        for spec in specs:
            persona = "receiver" if spec["recipient_type"] == "consignee" else spec["recipient_type"]
            if persona not in PERSONAS:
                continue
            cell = cells.setdefault(persona, {"channels": [], "on": f"{event}|{persona}" not in off, "locked": False})
            if spec["channel"] not in cell["channels"]:
                cell["channels"].append(spec["channel"])
            if spec.get("template_key") in LOCKED_TEMPLATES:
                cell["locked"] = True
        if cells:
            rows.append({"event": str(event), "group": "Platform events", "cells": cells})
    return {"personas": list(PERSONAS), "rows": rows}


# --- digest ------------------------------------------------------------------------


def _yesterday_window(now: datetime) -> tuple[datetime, datetime, str]:
    local = now.astimezone(TORONTO)
    day = local.date() - timedelta(days=1)
    start = datetime.combine(day, time.min, tzinfo=TORONTO)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC), day.isoformat()


def build_digest(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    from porterchain_api.booking_models import OrderEvent, OrderException

    now = now or datetime.now(UTC)
    start, end, label = _yesterday_window(now)

    def transitions(state: str) -> int:
        return (
            db.query(func.count(func.distinct(OrderEvent.order_id)))
            .filter(OrderEvent.to_state == state, OrderEvent.occurred_at >= start, OrderEvent.occurred_at < end)
            .scalar()
            or 0
        )

    exceptions = (
        db.query(func.count(OrderException.id))
        .filter(OrderException.created_at >= start, OrderException.created_at < end)
        .scalar()
        or 0
    )
    open_exceptions = db.query(func.count(OrderException.id)).filter(OrderException.status == "open").scalar() or 0
    m = metrics(db, hours=24, now=end)
    delivered = transitions("DELIVERED")
    failed = transitions("FAILED")
    return {
        "date": label,
        "delivered": delivered,
        "failed": failed,
        "success_pct": round(100.0 * delivered / (delivered + failed), 1) if (delivered + failed) else None,
        "exceptions_opened": exceptions,
        "exceptions_open_now": open_exceptions,
        "emails_accepted": m["accepted"],
        "email_p95_ms": m["p95_ms"],
        "bounce_pct": m["bounce_pct"],
        "dead_letters": m["dead_letters"],
    }


def maybe_send_digest(db: Session, *, now: datetime | None = None, force: bool = False) -> dict[str, Any]:
    """Once a day after send_hour (Toronto). Needs enabled AND approved."""
    from porterchain_api.notification_engine.center_settings import (
        DIGEST_DEFAULT,
        DIGEST_KEY,
        get_setting,
        set_setting,
    )

    now = now or datetime.now(UTC)
    cfg = get_setting(db, DIGEST_KEY, DIGEST_DEFAULT)
    if not (cfg.get("enabled") and cfg.get("approved")):
        return {"sent": False, "reason": "off"}
    local = now.astimezone(TORONTO)
    today = local.date().isoformat()
    if not force and (cfg.get("last_sent_date") == today or local.hour < int(cfg.get("send_hour") or 7)):
        return {"sent": False, "reason": "not_due"}
    digest = build_digest(db, now=now)
    from porterchain_api.notification_engine.staff_fanout import staff_sentinel
    from porterchain_api.platform.staff_notify import dispatch_staff_specs

    ctx = {f"d_{k}": ("" if v is None else str(v)) for k, v in digest.items()}
    ctx["title"] = f"Ops summary · {digest['date']}"
    dispatch_staff_specs(
        db,
        [
            {
                "template_key": "ops_daily_digest",
                "channel": "email",
                "recipient_type": "admin",
                "recipient_id": staff_sentinel("ops"),
                "context": ctx,
                "category": "orders",
                "priority": "normal",
            }
        ],
        event_type="notification.ops_digest",
        correlation_id=f"digest-{digest['date']}",
    )
    set_setting(db, DIGEST_KEY, {**cfg, "last_sent_date": today}, author=cfg.get("approved_by"))
    return {"sent": True, "digest": digest}

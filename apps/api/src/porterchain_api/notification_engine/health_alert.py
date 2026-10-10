"""Dead-letter / failure-rate alert to ops (admin bell + email).

Runs from the worker sweep. At most one alert per hour (cooldown), so a
bad hour pages once instead of on every sweep.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.notification_engine.models import NotificationRecord

logger = logging.getLogger(__name__)

WINDOW_MINUTES = 60
DEAD_LETTER_THRESHOLD = 5
FAILURE_RATE_THRESHOLD = 0.2
MIN_ATTEMPTS_FOR_RATE = 10
ALERT_COOLDOWN_SEC = 3600


def notification_health(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    """Counts for outbound channels (email/sms/push) created in the last hour."""
    now = now or datetime.now(UTC)
    since = now - timedelta(minutes=WINDOW_MINUTES)
    rows = (
        db.query(NotificationRecord.status, func.count(NotificationRecord.id))
        .filter(
            NotificationRecord.created_at >= since,
            NotificationRecord.channel.in_(("email", "sms", "push")),
            NotificationRecord.is_sandbox.is_(False),
        )
        .group_by(NotificationRecord.status)
        .all()
    )
    counts = {status: int(n) for status, n in rows}
    dead = counts.get("dead_letter", 0)
    failed = counts.get("failed", 0) + dead
    sent = counts.get("sent", 0) + counts.get("delivered", 0)
    attempts = sent + failed
    rate = (failed / attempts) if attempts else 0.0
    return {"dead_letter": dead, "failed": failed, "sent": sent, "attempts": attempts, "failure_rate": round(rate, 3)}


LATENCY_WINDOW_MINUTES = 30
MIN_SAMPLES_FOR_P95 = 20


def lane_latency(db: Session, *, now: datetime | None = None, minutes: int = LATENCY_WINDOW_MINUTES) -> dict[str, Any]:
    """p50/p95 created -> provider accepted per lane, against lanes.P95_TARGET_SEC."""
    from porterchain_api.notification_engine.lanes import NORMAL, P95_TARGET_SEC

    now = now or datetime.now(UTC)
    rows = (
        db.query(NotificationRecord.created_at, NotificationRecord.sent_at, NotificationRecord.search_tags)
        .filter(
            NotificationRecord.created_at >= now - timedelta(minutes=minutes),
            NotificationRecord.channel.in_(("email", "sms", "push")),
            NotificationRecord.sent_at.isnot(None),
            NotificationRecord.is_sandbox.is_(False),
        )
        .limit(20000)
        .all()
    )
    by_lane: dict[str, list[float]] = {}
    for created, sent, tags in rows:
        lane = (tags or {}).get("lane") or NORMAL
        by_lane.setdefault(lane, []).append(max(0.0, (sent - created).total_seconds()))
    out: dict[str, Any] = {}
    for lane, target in P95_TARGET_SEC.items():
        vals = sorted(by_lane.get(lane, []))
        p = (lambda q: vals[min(len(vals) - 1, int(round(q * (len(vals) - 1))))] if vals else None)
        p95 = p(0.95)
        out[lane] = {
            "n": len(vals),
            "p50_s": None if p(0.5) is None else round(p(0.5), 2),
            "p95_s": None if p95 is None else round(p95, 2),
            "target_s": target,
            "breach": bool(p95 is not None and len(vals) >= MIN_SAMPLES_FOR_P95 and p95 > target),
        }
    return out


def check_and_alert(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    stats = notification_health(db, now=now)
    stats["lanes"] = lane_latency(db, now=now)
    slow_lanes = [k for k, v in stats["lanes"].items() if v["breach"]]
    breach = bool(slow_lanes) or stats["dead_letter"] >= DEAD_LETTER_THRESHOLD or (
        stats["attempts"] >= MIN_ATTEMPTS_FOR_RATE and stats["failure_rate"] >= FAILURE_RATE_THRESHOLD
    )
    stats["alerted"] = False
    if not breach:
        return stats
    cooldown_since = (now or datetime.now(UTC)) - timedelta(seconds=ALERT_COOLDOWN_SEC)
    recent = (
        db.query(NotificationRecord.id)
        .filter(
            NotificationRecord.template_key == "notification_health_alert",
            NotificationRecord.created_at >= cooldown_since,
        )
        .first()
    )
    if recent is not None:
        stats["cooldown"] = True
        return stats
    from porterchain_api.notification_engine.staff_fanout import staff_sentinel
    from porterchain_api.platform.staff_notify import dispatch_staff_specs

    ctx = {
        "title": "Notification delivery is failing",
        "message": (
            f"Last {WINDOW_MINUTES} min: {stats['dead_letter']} dead letters, "
            f"{stats['failed']} failed of {stats['attempts']} sends "
            f"({int(stats['failure_rate'] * 100)}% failure). "
            + "".join(
                f"{lane} lane p95 {stats['lanes'][lane]['p95_s']}s > {stats['lanes'][lane]['target_s']}s target. "
                for lane in slow_lanes
            )
            + "Open the Delivery center."
        ),
        "dead_letter": str(stats["dead_letter"]),
        "failure_rate": f"{int(stats['failure_rate'] * 100)}%",
        "deep_link": "/notifications/delivery",
    }
    ops = staff_sentinel("ops")
    specs = [
        {
            "template_key": "notification_health_alert",
            "channel": channel,
            "recipient_type": "admin",
            "recipient_id": ops,
            "context": ctx,
            "category": "orders",
            "priority": "high",
            "deep_link": ctx["deep_link"],
        }
        for channel in ("in_app", "email")
    ]
    try:
        dispatch_staff_specs(
            db,
            specs,
            event_type="notification.health_alert",
            correlation_id=None,  # type: ignore[arg-type]
        )
        db.commit()
        stats["alerted"] = True
    except Exception:
        logger.exception("notification health alert failed")
        db.rollback()
    return stats

"""Speed dashboard + weekly win/loss summary (read-only).

Goal metric: every lead answered in under 5 minutes.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.crm_models import CrmLead

FAST_REPLY = timedelta(minutes=5)
MAX_ROWS = 20_000


def _aware(v: datetime | None) -> datetime | None:
    if v is None:
        return None
    return v if v.tzinfo else v.replace(tzinfo=UTC)


def _buyer_leads(db: Session, since: datetime) -> list[CrmLead]:
    return list(
        db.execute(
            select(CrmLead)
            .where(
                CrmLead.created_at >= since,
                CrmLead.intent_type != "driver_partner",
                CrmLead.merge_candidate_of.is_(None),
            )
            .limit(MAX_ROWS)
        ).scalars()
    )


def _pct(n: int, d: int) -> float | None:
    return round(100.0 * n / d, 1) if d else None


def _repeat_rate(db: Session, won: list[CrmLead]) -> tuple[int, int]:
    """Won leads with an order → how many ordered again (same customer / merchant)."""
    order_ids = [lead.order_id for lead in won if lead.order_id]
    if not order_ids:
        return 0, 0
    firsts = db.execute(
        select(Order.id, Order.customer_id, Order.merchant_id).where(
            Order.id.in_(order_ids)
        )
    ).all()
    repeat = 0
    for _oid, customer_id, merchant_id in firsts:
        col, val = (
            (Order.merchant_id, merchant_id)
            if merchant_id
            else (Order.customer_id, customer_id)
        )
        if not val:
            continue
        n = db.execute(select(func.count(Order.id)).where(col == val)).scalar_one()
        repeat += 1 if n >= 2 else 0
    return repeat, len(firsts)


def speed_window(
    db: Session, *, days: int, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    leads = _buyer_leads(db, now - timedelta(days=days))
    reply_minutes: list[float] = []
    fast = 0
    for lead in leads:
        created, first = _aware(lead.created_at), _aware(lead.first_response_at)
        if created and first and first >= created:
            delta = first - created
            reply_minutes.append(delta.total_seconds() / 60.0)
            fast += 1 if delta <= FAST_REPLY else 0
    quoted = [lead for lead in leads if lead.quoted_at]
    quoted_won = [lead for lead in quoted if lead.status == "won"]
    won = [lead for lead in leads if lead.status == "won"]
    repeat, booked = _repeat_rate(db, won)
    by_channel: dict[str, Counter] = defaultdict(Counter)
    for lead in leads:
        c = by_channel[lead.channel or "website"]
        c["leads"] += 1
        if lead.status in ("won", "lost"):
            c[lead.status] += 1
    channels = sorted(
        (
            {
                "channel": ch,
                "leads": c["leads"],
                "won": c["won"],
                "lost": c["lost"],
                "win_rate": _pct(c["won"], c["won"] + c["lost"]),
            }
            for ch, c in by_channel.items()
        ),
        key=lambda r: (-r["leads"], r["channel"]),
    )
    return {
        "days": days,
        "leads": len(leads),
        "answered": len(reply_minutes),
        "median_first_reply_minutes": round(median(reply_minutes), 1)
        if reply_minutes
        else None,
        "answered_within_5m_pct": _pct(fast, len(leads)),
        "quoted": len(quoted),
        "quote_to_booking_pct": _pct(len(quoted_won), len(quoted)),
        "booked": booked,
        "booking_to_repeat_pct": _pct(repeat, booked),
        "win_rate_by_channel": channels,
    }


def speed_dashboard(db: Session) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {
        "generated_at": now.isoformat(),
        "windows": [speed_window(db, days=d, now=now) for d in (7, 30)],
    }


def weekly_summary(db: Session, *, now: datetime | None = None) -> dict[str, Any]:
    """Wins and losses closed in the last 7 days, by channel, plus lost reasons."""
    now = now or datetime.now(UTC)
    since = now - timedelta(days=7)
    rows = list(
        db.execute(
            select(CrmLead).where(
                ((CrmLead.won_at >= since) & (CrmLead.status == "won"))
                | ((CrmLead.lost_at >= since) & (CrmLead.status == "lost"))
            )
        ).scalars()
    )
    by_channel: dict[str, Counter] = defaultdict(Counter)
    reasons: Counter = Counter()
    for lead in rows:
        by_channel[lead.channel or "website"][lead.status] += 1
        if lead.status == "lost":
            reasons[lead.lost_reason or "unspecified"] += 1
    channels = [
        {
            "channel": ch,
            "won": c["won"],
            "lost": c["lost"],
            "win_rate": _pct(c["won"], c["won"] + c["lost"]),
        }
        for ch, c in sorted(by_channel.items())
    ]
    won = sum(c["won"] for c in by_channel.values())
    lost = sum(c["lost"] for c in by_channel.values())
    return {
        "from": since.isoformat(),
        "to": now.isoformat(),
        "won": won,
        "lost": lost,
        "win_rate": _pct(won, won + lost),
        "by_channel": channels,
        "lost_reasons": [{"reason": r, "count": n} for r, n in reasons.most_common()],
    }

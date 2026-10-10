"""Rules-first customer intelligence. Deterministic, explainable, free.

- risk:    first order + high value, or a drop-off address with repeated failed deliveries
           → order flagged ``risk.review`` (ops sees it; nothing is auto-blocked).
- churn:   no order in 2× the customer's usual interval (min 30 days) → churn flag in admin.
- reorder: delivered retail order whose interval is due → a *draft* nudge; sending needs the
           ``reorder_nudges_enabled`` customer setting AND staff approval per batch.
- autofill: last-used addresses ranked by use count + recency.
"""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import pairwise
from statistics import median
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Customer, Order, Quote

HIGH_VALUE_FIRST_ORDER_CENTS = 30_000
FAILED_ADDRESS_THRESHOLD = 3
CHURN_MIN_DAYS = 30
DEFAULT_REORDER_DAYS = 14
FAILED_STATES = ("FAILED", "RETURN_TO_SENDER")
LIVE_STATES_EXCLUDED = ("CANCELLED",)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def address_key(addr: dict[str, Any] | None) -> str:
    if not isinstance(addr, dict):
        return ""
    if addr.get("place_id"):
        return f"pid:{str(addr['place_id'])[:120]}"
    text = " ".join(str(addr.get("formatted") or "").lower().replace(",", " ").split())
    return f"txt:{text[:120]}" if text else ""


# --------------------------------------------------------------------------- risk


def failed_deliveries_to(db: Session, addr: dict[str, Any] | None) -> int:
    key = address_key(addr)
    if not key:
        return 0
    rows = (
        db.query(Order.dropoff)
        .filter(Order.state.in_(FAILED_STATES))
        .order_by(Order.created_at.desc())
        .limit(500)
        .all()
    )
    return sum(1 for (d,) in rows if address_key(d) == key)


def risk_reasons(db: Session, quote: Quote, customer: Customer | None) -> list[str]:
    reasons: list[str] = []
    prior = 0
    if customer is not None:
        prior = (
            db.query(func.count(Order.id))
            .filter(Order.customer_id == customer.id, ~Order.state.in_(LIVE_STATES_EXCLUDED))
            .scalar()
            or 0
        )
    if prior == 0 and int(quote.amount_cents or 0) >= HIGH_VALUE_FIRST_ORDER_CENTS:
        reasons.append("first_order_high_value")
    if failed_deliveries_to(db, quote.dropoff) >= FAILED_ADDRESS_THRESHOLD:
        reasons.append("dropoff_repeated_failures")
    return reasons


def flag_order_risk(db: Session, quote: Quote, customer: Customer | None) -> list[str]:
    """Store risk reasons on the quote's consent blob; the order inherits it at confirmation."""
    reasons = risk_reasons(db, quote, customer)
    if reasons:
        consent = dict(quote.consent or {}) if isinstance(quote.consent, dict) else {}
        consent["risk_review"] = reasons
        quote.consent = consent
    return reasons


def order_risk(order: Order) -> list[str]:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    if meta.get("risk_review"):
        return list(meta["risk_review"])
    quote = order.quote
    consent = quote.consent if quote is not None and isinstance(quote.consent, dict) else {}
    return list(consent.get("risk_review") or [])


def remember_locale(quote: Quote, locale: str) -> None:
    consent = dict(quote.consent or {}) if isinstance(quote.consent, dict) else {}
    consent["locale"] = locale
    quote.consent = consent


def order_locale(order: Order) -> str:
    quote = order.quote
    consent = quote.consent if quote is not None and isinstance(quote.consent, dict) else {}
    return "fr" if consent.get("locale") == "fr" else "en"


# --------------------------------------------------------------------------- cadence / churn


def order_dates(db: Session, customer_id: str) -> list[datetime]:
    rows = (
        db.query(Order.created_at)
        .filter(Order.customer_id == customer_id, ~Order.state.in_(LIVE_STATES_EXCLUDED), Order.is_sandbox.is_(False))
        .order_by(Order.created_at.asc())
        .all()
    )
    return [d for d in (_aware(r) for (r,) in rows) if d is not None]


def usual_interval_days(dates: list[datetime]) -> float | None:
    if len(dates) < 2:
        return None
    gaps = [(b - a).total_seconds() / 86400 for a, b in pairwise(dates)]
    gaps = [g for g in gaps if g >= 0.5]
    return float(median(gaps)) if gaps else None


def churn(db: Session, customer_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    dates = order_dates(db, customer_id)
    if not dates:
        return {"status": "no_orders", "flag": False, "days_since_last": None, "usual_interval_days": None}
    interval = usual_interval_days(dates)
    since = (now - dates[-1]).total_seconds() / 86400
    threshold = max(CHURN_MIN_DAYS, 2 * interval) if interval else 60
    flag = since > threshold
    return {
        "status": "at_risk" if flag else "active",
        "flag": flag,
        "days_since_last": round(since, 1),
        "usual_interval_days": round(interval, 1) if interval else None,
        "threshold_days": round(threshold, 1),
        "rule": "No order in 2x the usual interval (min 30 days; 60 days for one-time customers).",
    }


def reorder_due(db: Session, customer_id: str, *, now: datetime | None = None) -> tuple[bool, str]:
    now = now or _now()
    dates = order_dates(db, customer_id)
    if not dates:
        return False, "no_orders"
    interval = usual_interval_days(dates) or DEFAULT_REORDER_DAYS
    interval = max(7.0, min(interval, 30.0))
    since = (now - dates[-1]).total_seconds() / 86400
    if since < interval:
        return False, "not_due"
    if since > interval * 3:
        return False, "lapsed"  # churn territory: a human should reach out, not a robot
    return True, f"Last order {since:.0f} days ago; usual interval {interval:.0f} days."

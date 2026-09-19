"""Order delivery SLA — promise deadline vs ASAP request time.

`scheduled_at` is the customer request time (often `now` for Send-now). It must NOT
be treated as the SLA deadline for INSTANT/EXPRESS bookings, or every new parcel
appears SLA-breached immediately.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_api.booking_engine.compliance_metadata import delivery_window_end
from porterchain_api.domain.states import OrderType

# Keep in sync with order_engine.buckets.DONE_STATES (avoid circular import via buckets).
_DONE_STATES = frozenset({"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"})

# Same-day / ASAP promise window when no explicit delivery_window is set.
DEFAULT_INSTANT_SLA_HOURS = 4
# Warn when the remaining promise window is this short.
AT_RISK_MINUTES = 30
# If scheduled_at is this far after create, treat as a true appointment (legacy data).
SCHEDULED_INTENT_MINUTES = 15


def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def resolve_sla_deadline(
    order: Any,
    *,
    instant_sla_hours: float = DEFAULT_INSTANT_SLA_HOURS,
) -> datetime | None:
    """Return the delivery promise deadline for SLA status (naive UTC), or None."""
    window_end = delivery_window_end(getattr(order, "compliance_metadata", None))
    if window_end is not None:
        return _naive_utc(window_end)

    scheduled = _naive_utc(getattr(order, "scheduled_at", None))
    created = _naive_utc(getattr(order, "created_at", None))
    order_type = str(getattr(order, "order_type", "") or "").upper()

    is_scheduled_type = order_type == OrderType.SCHEDULED.value
    if not is_scheduled_type and scheduled and created:
        if scheduled - created >= timedelta(minutes=SCHEDULED_INTENT_MINUTES):
            is_scheduled_type = True

    if is_scheduled_type and scheduled:
        return scheduled

    # INSTANT / EXPRESS / "now" — promise from create (or now if create missing).
    base = created or scheduled or datetime.now(UTC).replace(tzinfo=None)
    hours = max(float(instant_sla_hours), 0.25)
    return base + timedelta(hours=hours)


def order_sla_status(
    order: Any,
    now: datetime | None = None,
    *,
    instant_sla_hours: float = DEFAULT_INSTANT_SLA_HOURS,
    at_risk_minutes: int = AT_RISK_MINUTES,
) -> str:
    """Return `met` | `ok` | `at_risk` | `breached` for an order."""
    state = getattr(order, "state", None)
    if state in _DONE_STATES:
        return "met"

    ref = _naive_utc(now) or datetime.now(UTC).replace(tzinfo=None)
    deadline = resolve_sla_deadline(order, instant_sla_hours=instant_sla_hours)
    if deadline is None:
        return "ok"

    if ref > deadline:
        return "breached"
    if (deadline - ref) <= timedelta(minutes=max(int(at_risk_minutes), 1)):
        return "at_risk"
    return "ok"

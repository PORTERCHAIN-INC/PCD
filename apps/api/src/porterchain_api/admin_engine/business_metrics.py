"""§5.3.2–5.3.4 — platform business metrics (dispatch, on-time, support SLA)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.admin_models import SupportTicket
from porterchain_api.domain.states import OrderState
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.order_engine.buckets import DONE_STATES
from porterchain_api.support_engine.support_helpers import ticket_data

AUTO_DISPATCH_TARGET_PCT = 90.0
ON_TIME_TARGET_PCT = 95.0
SUPPORT_FIRST_RESPONSE_MAX_HOURS = 4.0
DEFAULT_WINDOW_DAYS = 7
ON_TIME_GRACE_MINUTES = 30

_DISPATCH_PIPELINE_STATES = (
    OrderState.DISPATCH_READY.value,
    OrderState.DRIVER_ASSIGNED.value,
    OrderState.DRIVER_ACCEPTED.value,
    OrderState.DRIVER_REJECTED.value,
    OrderState.DRIVER_EN_ROUTE.value,
    OrderState.AT_PICKUP.value,
    OrderState.PICKED_UP.value,
    OrderState.IN_TRANSIT.value,
    OrderState.AT_DESTINATION.value,
    OrderState.DELIVERED.value,
    OrderState.POD_COMPLETED.value,
    OrderState.INVOICED.value,
    OrderState.CLOSED.value,
)


def build_business_metric_alerts(metrics: dict) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for key, code, label in (
        ("auto_dispatch", "auto_dispatch_below_target", "Auto-dispatch"),
        ("on_time_delivery", "on_time_below_target", "On-time delivery"),
        ("support_first_response", "support_first_response_slo", "Support first response"),
    ):
        block = metrics.get(key) or {}
        if int(block.get("sample_size") or 0) == 0:
            continue
        if not block.get("meets_slo"):
            if key == "support_first_response":
                msg = (
                    f"{label} avg {block.get('avg_hours')}h exceeds "
                    f"{block.get('max_hours_target')}h (n={block.get('sample_size')})"
                )
            else:
                msg = (
                    f"{label} {block.get('pct')}% below target "
                    f"{block.get('slo_target_pct')}% (n={block.get('sample_size')})"
                )
            alerts.append({"level": "warning", "code": code, "message": msg})
    return alerts


def assess_auto_dispatch(db: Session, *, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    live = Order.is_sandbox.is_(False)
    eligible = (
        db.query(Order)
        .filter(
            live,
            Order.created_at >= cutoff,
            Order.state.in_(_DISPATCH_PIPELINE_STATES),
        )
        .count()
    )
    dispatched = (
        db.query(Order)
        .filter(
            live,
            Order.created_at >= cutoff,
            Order.state.in_(_DISPATCH_PIPELINE_STATES),
            Order.assigned_driver_id.isnot(None),
        )
        .count()
    )
    pct = 100.0 if eligible == 0 else round(dispatched / eligible * 100, 2)
    return {
        "window_days": window_days,
        "eligible_orders": eligible,
        "auto_dispatched_orders": dispatched,
        "pct": pct,
        "slo_target_pct": AUTO_DISPATCH_TARGET_PCT,
        "meets_slo": eligible == 0 or pct >= AUTO_DISPATCH_TARGET_PCT,
        "sample_size": eligible,
    }


def assess_on_time_delivery(db: Session, *, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    delivered_orders = (
        db.query(Order)
        .filter(
            Order.is_sandbox.is_(False),
            Order.created_at >= cutoff,
            Order.state.in_(DONE_STATES),
        )
        .all()
    )
    if not delivered_orders:
        return {
            "window_days": window_days,
            "delivered_orders": 0,
            "on_time_orders": 0,
            "pct": 100.0,
            "slo_target_pct": ON_TIME_TARGET_PCT,
            "meets_slo": True,
            "sample_size": 0,
            "grace_minutes": ON_TIME_GRACE_MINUTES,
        }

    grace = timedelta(minutes=ON_TIME_GRACE_MINUTES)
    on_time = 0
    for order in delivered_orders:
        event = (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order.id, OrderEvent.event_type == "order.delivered")
            .order_by(OrderEvent.occurred_at.desc())
            .first()
        )
        delivered_at = event.occurred_at if event else order.updated_at
        if delivered_at and delivered_at.tzinfo is None:
            delivered_at = delivered_at.replace(tzinfo=UTC)
        scheduled = order.scheduled_at
        if scheduled and scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=UTC)
        if not scheduled or not delivered_at:
            on_time += 1
            continue
        if delivered_at <= scheduled + grace:
            on_time += 1

    total = len(delivered_orders)
    pct = round(on_time / total * 100, 2)
    return {
        "window_days": window_days,
        "delivered_orders": total,
        "on_time_orders": on_time,
        "pct": pct,
        "slo_target_pct": ON_TIME_TARGET_PCT,
        "meets_slo": pct >= ON_TIME_TARGET_PCT,
        "sample_size": total,
        "grace_minutes": ON_TIME_GRACE_MINUTES,
    }


def assess_support_first_response(db: Session, *, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    tickets = db.query(SupportTicket).filter(SupportTicket.created_at >= cutoff).all()
    durations: list[float] = []
    within_slo = 0
    for ticket in tickets:
        data = ticket_data(ticket)
        if not data.get("first_response_at") or not ticket.created_at:
            continue
        created = ticket.created_at.replace(tzinfo=UTC) if ticket.created_at.tzinfo is None else ticket.created_at
        first = datetime.fromisoformat(str(data["first_response_at"]).replace("Z", "+00:00"))
        hours = (first - created).total_seconds() / 3600
        durations.append(hours)
        if hours <= SUPPORT_FIRST_RESPONSE_MAX_HOURS:
            within_slo += 1

    responded = len(durations)
    avg_hours = round(sum(durations) / responded, 2) if responded else 0.0
    pct_within = 100.0 if responded == 0 else round(within_slo / responded * 100, 2)
    meets = responded == 0 or avg_hours <= SUPPORT_FIRST_RESPONSE_MAX_HOURS
    return {
        "window_days": window_days,
        "tickets_with_response": responded,
        "avg_hours": avg_hours,
        "pct_within_slo": pct_within,
        "max_hours_target": SUPPORT_FIRST_RESPONSE_MAX_HOURS,
        "meets_slo": meets,
        "sample_size": responded,
    }


def assess_business_metrics(db: Session, *, window_days: int = DEFAULT_WINDOW_DAYS) -> dict:
    auto_dispatch = assess_auto_dispatch(db, window_days=window_days)
    on_time_delivery = assess_on_time_delivery(db, window_days=window_days)
    support_first_response = assess_support_first_response(db, window_days=window_days)
    result = {
        "auto_dispatch": auto_dispatch,
        "on_time_delivery": on_time_delivery,
        "support_first_response": support_first_response,
    }
    result["alerts"] = build_business_metric_alerts(result)
    return result

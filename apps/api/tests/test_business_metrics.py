"""Business metrics tests (§5.3.2–5.3.4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.business_metrics import (
    AUTO_DISPATCH_TARGET_PCT,
    ON_TIME_TARGET_PCT,
    SUPPORT_FIRST_RESPONSE_MAX_HOURS,
    assess_auto_dispatch,
    assess_business_metrics,
    assess_on_time_delivery,
    assess_support_first_response,
)
from porterchain_api.admin_models import SupportTicket
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.support_engine.support_helpers import set_ticket_data


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def test_assess_auto_dispatch_structure(db: Session) -> None:
    result = assess_auto_dispatch(db, window_days=7)
    assert result["slo_target_pct"] == AUTO_DISPATCH_TARGET_PCT
    assert isinstance(result["pct"], (int, float))
    assert isinstance(result["meets_slo"], bool)


def test_assess_auto_dispatch_counts_assigned(db: Session) -> None:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DRIVER_ASSIGNED.value,
        amount_cents=3200,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        is_sandbox=False,
    )
    db.add(order)
    db.commit()
    result = assess_auto_dispatch(db, window_days=7)
    assert result["auto_dispatched_orders"] >= 1
    assert result["pct"] >= 0


def test_assess_auto_dispatch_excludes_sandbox(db: Session) -> None:
    before = assess_auto_dispatch(db, window_days=7)
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DRIVER_ASSIGNED.value,
        amount_cents=3200,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        is_sandbox=True,
    )
    db.add(order)
    db.commit()
    after = assess_auto_dispatch(db, window_days=7)
    assert after["eligible_orders"] == before["eligible_orders"]
    assert after["auto_dispatched_orders"] == before["auto_dispatched_orders"]


def test_assess_on_time_delivery_delivered_event(db: Session) -> None:
    scheduled = datetime.now(UTC) + timedelta(hours=2)
    order = Order(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DELIVERED.value,
        amount_cents=3200,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=scheduled,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    db.add(
        OrderEvent(
            order_id=order.id,
            event_type="order.delivered",
            occurred_at=scheduled - timedelta(minutes=10),
        )
    )
    db.commit()
    result = assess_on_time_delivery(db, window_days=7)
    assert result["delivered_orders"] >= 1
    assert result["slo_target_pct"] == ON_TIME_TARGET_PCT


def test_assess_support_first_response_within_slo(db: Session) -> None:
    ticket = SupportTicket(
        id=str(uuid4()),
        subject="Test SLA",
        status="open",
        priority="normal",
        category="other",
        created_at=datetime.now(UTC) - timedelta(hours=1),
    )
    set_ticket_data(ticket, first_response_at=(datetime.now(UTC) - timedelta(minutes=30)).isoformat())
    db.add(ticket)
    db.commit()
    result = assess_support_first_response(db, window_days=7)
    assert result["tickets_with_response"] >= 1
    assert result["avg_hours"] <= SUPPORT_FIRST_RESPONSE_MAX_HOURS
    assert result["meets_slo"] is True


def test_assess_business_metrics_bundle(db: Session) -> None:
    bundle = assess_business_metrics(db)
    assert "auto_dispatch" in bundle
    assert "on_time_delivery" in bundle
    assert "support_first_response" in bundle
    assert "alerts" in bundle

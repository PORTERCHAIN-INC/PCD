"""Customer self-service order cancellation (pre-pickup, ownership-scoped)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Customer, Order


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _make_customer(db: Session, suffix: str) -> Customer:
    customer = Customer(clerk_user_id=f"cust_clerk_{suffix}", email=f"cust-{suffix}@cancel.test")
    db.add(customer)
    db.flush()
    return customer


def _make_order(db: Session, *, customer_id: str, state: OrderState) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        customer_id=customer_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_customer_can_cancel_pre_pickup_order(db: Session) -> None:
    customer = _make_customer(db, uuid4().hex[:8])
    order = _make_order(db, customer_id=customer.id, state=OrderState.BOOKED)
    db.commit()

    result = CustomerService().cancel_order(db, customer.id, order.id)

    assert result["state"] == OrderState.CANCELLED.value
    assert result["refund_pending"] is True
    assert result["order_id"] == order.id

    db.refresh(order)
    assert order.state == OrderState.CANCELLED.value


def test_customer_cannot_cancel_other_customers_order(db: Session) -> None:
    customer_a = _make_customer(db, uuid4().hex[:8])
    customer_b = _make_customer(db, uuid4().hex[:8])
    order_b = _make_order(db, customer_id=customer_b.id, state=OrderState.BOOKED)
    db.commit()

    with pytest.raises(LookupError, match="order_not_found"):
        CustomerService().cancel_order(db, customer_a.id, order_b.id)


def test_customer_cannot_cancel_delivered_order(db: Session) -> None:
    customer = _make_customer(db, uuid4().hex[:8])
    order = _make_order(db, customer_id=customer.id, state=OrderState.DELIVERED)
    db.commit()

    with pytest.raises(ValueError, match="order_not_cancellable"):
        CustomerService().cancel_order(db, customer.id, order.id)

    db.refresh(order)
    assert order.state == OrderState.DELIVERED.value  # unchanged

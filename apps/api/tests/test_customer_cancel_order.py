"""Customer self-service order cancellation + refund (pre-pickup, ownership-scoped)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_engine.refund_service import PaymentRefundService
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState, PaymentStatus
from porterchain_api.models import Customer, Order, Payment, Quote


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _make_customer(db: Session, suffix: str) -> Customer:
    customer = Customer(clerk_user_id=f"cust_clerk_{suffix}", email=f"cust-{suffix}@cancel.test")
    db.add(customer)
    db.flush()
    return customer


def _make_quote(db: Session, customer_id: str) -> Quote:
    quote = Quote(
        customer_id=customer_id,
        pickup=_addr(),
        dropoff=_addr(),
        vehicle_class="car",
        package_type="looseParcel",
        scheduled_at=datetime.now(UTC),
        amount_cents=2500,
        currency="cad",
        pricing_breakdown={"items": []},
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(quote)
    db.flush()
    return quote


def _make_order(db: Session, *, quote_id: str, customer_id: str, state: OrderState) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        quote_id=quote_id,
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


def _make_payment(db: Session, *, quote_id, order_id, customer_id, status: str) -> Payment:
    payment = Payment(
        quote_id=quote_id,
        order_id=order_id,
        customer_id=customer_id,
        status=status,
        amount_cents=2500,
        currency="cad",
    )
    db.add(payment)
    db.flush()
    return payment


def _setup(db: Session, state: OrderState, *, with_payment: bool = True):
    customer = _make_customer(db, uuid4().hex[:8])
    quote = _make_quote(db, customer.id)
    order = _make_order(db, quote_id=quote.id, customer_id=customer.id, state=state)
    if with_payment:
        _make_payment(
            db,
            quote_id=quote.id,
            order_id=order.id,
            customer_id=customer.id,
            status=PaymentStatus.SUCCEEDED.value,
        )
    db.commit()
    return customer, order


def test_customer_cancel_refunds_paid_order(db: Session, settings) -> None:
    customer, order = _setup(db, OrderState.BOOKED)

    result = CustomerService().cancel_order(db, settings, customer.id, order.id)

    assert result["state"] == OrderState.CANCELLED.value
    assert result["refunded"] is True  # mock refund in local
    assert result["refund_pending"] is False
    assert result["refund_amount_cents"] == 2500

    db.refresh(order)
    assert order.state == OrderState.CANCELLED.value
    payment = db.query(Payment).filter(Payment.order_id == order.id).one()
    assert payment.status == PaymentStatus.REFUNDED.value


def test_cancel_without_payment_is_not_pending(db: Session, settings) -> None:
    customer, order = _setup(db, OrderState.DISPATCH_READY, with_payment=False)

    result = CustomerService().cancel_order(db, settings, customer.id, order.id)

    assert result["state"] == OrderState.CANCELLED.value
    assert result["refunded"] is False
    assert result["refund_pending"] is False  # nothing to refund


def test_customer_cannot_cancel_other_customers_order(db: Session, settings) -> None:
    _customer_a = _make_customer(db, uuid4().hex[:8])
    customer_b, order_b = _setup(db, OrderState.BOOKED)

    with pytest.raises(LookupError, match="order_not_found"):
        CustomerService().cancel_order(db, settings, _customer_a.id, order_b.id)


def test_customer_cannot_cancel_delivered_order(db: Session, settings) -> None:
    customer, order = _setup(db, OrderState.DELIVERED)

    with pytest.raises(ValueError, match="order_not_cancellable"):
        CustomerService().cancel_order(db, settings, customer.id, order.id)

    db.refresh(order)
    assert order.state == OrderState.DELIVERED.value  # unchanged


def test_refund_manual_required_when_stripe_unavailable(db: Session) -> None:
    # Production settings (no mock) with a captured payment but no Stripe intent
    # on the order -> create_refund returns None -> manual follow-up required.
    prod_settings = Settings(
        _env_file=None,
        app_env="production",
        jwt_secret="a" * 64,
        stripe_secret="sk_live_x",
        stripe_mock=False,
        clerk_secret_key="sk_test_ci",
        clerk_jwks_url="https://clerk.example.test/.well-known/jwks.json",
    )
    customer, order = _setup(db, OrderState.BOOKED)
    assert prod_settings.allow_stripe_mock is False

    outcome = PaymentRefundService().refund_order(db, prod_settings, order)

    assert outcome.refunded is False
    assert outcome.reason == "manual_required"
    assert outcome.pending is True
    payment = db.query(Payment).filter(Payment.order_id == order.id).one()
    assert payment.status == PaymentStatus.SUCCEEDED.value  # unchanged; needs manual refund

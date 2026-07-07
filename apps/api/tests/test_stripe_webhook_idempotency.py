"""Stripe webhook idempotency — duplicate events are no-ops (DD-01c)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
from porterchain_api.config import Settings
from porterchain_api.models import DomainEvent, Order, Payment
from porterchain_api.schemas import AddressInput, CreateQuoteRequest, WebsitePricingSnapshot


def _setup_quote(db: Session, settings: Settings):
    session_id = f"stripe-webhook-{datetime.now(UTC).timestamp()}"
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session_id,
            pickup=AddressInput(formatted="1 King St W, Toronto", lat=43.6488, lng=-79.3817),
            dropoff=AddressInput(formatted="2 Bay St, Toronto", lat=43.6476, lng=-79.3797),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=4.0,
            scheduled_at=datetime.now(UTC).replace(microsecond=0),
            schedule_mode="now",
            website_pricing=WebsitePricingSnapshot(
                customer_price_cad=45.0,
                driver_payout_cad=30.0,
                platform_margin_cad=15.0,
                distance_km=6.0,
                duration_minutes=18.0,
                engine_vehicle_id="cargo_van",
                breakdown={"base": 10.0, "distance": 35.0},
            ),
        ),
        ip_address="127.0.0.1",
    )
    quote, customer, _ = BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email="stripe.webhook@test.porterchain.com",
        phone="+1 416-555-0300",
        clerk_user_id="clerk_stripe_webhook",
        anonymous_session_id=session_id,
        consent={
            "terms_accepted": True,
            "privacy_accepted": True,
            "dangerous_goods_confirmed": True,
        },
    )
    payment = db.query(Payment).filter(Payment.quote_id == quote.id).one()
    return quote, customer, payment


def _checkout_completed_event(*, event_id: str, quote_id: str, customer_id: str, payment_id: str) -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {
                    "quote_id": quote_id,
                    "customer_id": customer_id,
                    "payment_id": payment_id,
                },
                "payment_intent": "pi_test_webhook",
                "payment_method_types": ["card"],
                "amount_total": 4500,
                "currency": "cad",
            }
        },
    }


def test_duplicate_stripe_webhook_is_no_op(db: Session, settings: Settings) -> None:
    quote, customer, payment = _setup_quote(db, settings)
    svc = StripeWebhookService()
    event = _checkout_completed_event(
        event_id=str(uuid4()),
        quote_id=quote.id,
        customer_id=customer.id,
        payment_id=payment.id,
    )

    first = svc.handle(db, settings, event)
    order_count_after_first = db.query(Order).filter(Order.quote_id == quote.id).count()
    webhook_events = db.query(DomainEvent).filter(DomainEvent.aggregate_id == event["id"]).count()

    second = svc.handle(db, settings, event)
    order_count_after_second = db.query(Order).filter(Order.quote_id == quote.id).count()

    assert first == {"status": "ok"}
    assert second == {"status": "duplicate"}
    assert order_count_after_first == 1
    assert order_count_after_second == 1
    assert webhook_events == 1


def test_stripe_webhook_missing_id_raises(db: Session, settings: Settings) -> None:
    svc = StripeWebhookService()
    with pytest.raises(ValueError, match="stripe_event_missing_id"):
        svc.handle(db, settings, {"type": "checkout.session.completed", "data": {"object": {}}})

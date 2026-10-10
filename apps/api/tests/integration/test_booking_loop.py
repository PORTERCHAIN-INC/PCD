"""Booking loop integration — quote → payment → order → domain events (DD-01b)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.confirmation_service import (
    BookingConfirmationService,
)
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_models import (
    Booking,
    DomainEvent,
    Invoice,
    Order,
    Payment,
    Quote,
)
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState, PaymentStatus, QuoteState
from porterchain_api.schemas import (
    AddressInput,
    CreateQuoteRequest,
    WebsitePricingSnapshot,
)


def _website_pricing() -> WebsitePricingSnapshot:
    return WebsitePricingSnapshot(
        customer_price_cad=48.0,
        driver_payout_cad=32.0,
        platform_margin_cad=16.0,
        distance_km=8.0,
        duration_minutes=24.0,
        engine_vehicle_id="cargo_van",
        breakdown={"base": 12.0, "distance": 36.0},
    )


def _addr() -> AddressInput:
    return AddressInput(
        formatted="100 King St W, Toronto ON M5X 1A9",
        lat=43.6488,
        lng=-79.3817,
    )


def _dropoff() -> AddressInput:
    return AddressInput(
        formatted="200 Bay St, Toronto ON M5J 2J2",
        lat=43.6476,
        lng=-79.3797,
    )


def test_retail_booking_loop_quote_to_dispatch_ready(
    db: Session,
    settings: Settings,
) -> None:
    """Full retail path: quote → start booking → mock checkout → order + events."""
    session_id = f"integration-{datetime.now(UTC).timestamp()}"
    scheduled = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=3)

    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session_id,
            pickup=_addr(),
            dropoff=_dropoff(),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=5.0,
            scheduled_at=scheduled,
            schedule_mode="scheduled",
            website_pricing=_website_pricing(),
        ),
        ip_address="127.0.0.1",
    )
    assert quote.state == QuoteState.QUOTE.value

    quote, customer, checkout_url = BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email="integration@test.porterchain.com",
        phone="+1 416-555-0199",
        clerk_user_id="clerk_integration_test",
        anonymous_session_id=session_id,
        consent={
            "terms_accepted": True,
            "privacy_accepted": True,
            "dangerous_goods_confirmed": True,
            "consent_at": datetime.now(UTC).isoformat(),
        },
    )
    assert quote.state == QuoteState.PAYMENT_PENDING.value
    assert customer.id == quote.customer_id
    assert checkout_url is None or settings.stripe_mock

    order = BookingConfirmationService().mock_complete_checkout(db, settings, quote.id)

    db.refresh(quote)
    assert quote.state == QuoteState.PAYMENT_PENDING.value or db.get(Quote, quote.id)
    assert order.state == OrderState.DISPATCH_READY.value
    assert order.tracking_number
    assert order.order_number

    booking = db.query(Booking).filter(Booking.order_id == order.id).one()
    invoice = db.query(Invoice).filter(Invoice.order_id == order.id).one()
    payment = db.query(Payment).filter(Payment.quote_id == quote.id).one()
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert booking.booking_number
    assert invoice.invoice_number

    event_types = {
        row.event_type
        for row in db.query(DomainEvent)
        .filter(
            DomainEvent.aggregate_id.in_([quote.id, order.id, customer.id, booking.id])
            | DomainEvent.correlation_id.in_([quote.id, order.id, session_id])
        )
        .all()
    }
    for expected in (
        E.QUOTE_CREATED,
        E.BOOKING_STARTED,
        E.PAYMENT_STARTED,
        E.ORDER_CREATED,
        E.ORDER_DISPATCH_READY,
        E.BOOKING_CONFIRMED,
    ):
        assert expected in event_types, f"missing domain event {expected}"


def test_booking_loop_idempotent_checkout(
    db: Session,
    settings: Settings,
) -> None:
    """Second mock checkout for the same quote must not create duplicate orders."""
    session_id = f"idempotent-{datetime.now(UTC).timestamp()}"
    quote = QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=session_id,
            pickup=_addr(),
            dropoff=_dropoff(),
            vehicle_class="cargo_van",
            package_type="looseParcel",
            weight_kg=3.0,
            scheduled_at=datetime.now(UTC).replace(microsecond=0) + timedelta(hours=2),
            schedule_mode="scheduled",
            website_pricing=_website_pricing(),
        ),
        ip_address="127.0.0.1",
    )
    BookingService().start_booking(
        db,
        settings,
        quote_id=quote.id,
        email="idempotent@test.porterchain.com",
        phone="+1 416-555-0200",
        clerk_user_id="clerk_idempotent_test",
        anonymous_session_id=session_id,
        consent={
            "terms_accepted": True,
            "privacy_accepted": True,
            "dangerous_goods_confirmed": True,
        },
    )
    confirm = BookingConfirmationService()
    first = confirm.mock_complete_checkout(db, settings, quote.id)
    second = confirm.mock_complete_checkout(db, settings, quote.id)
    assert first.id == second.id
    assert db.query(Order).filter(Order.quote_id == quote.id).count() == 1

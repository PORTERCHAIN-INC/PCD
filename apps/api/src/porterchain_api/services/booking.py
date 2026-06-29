"""Legacy booking module — delegates to booking_engine services."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event as emit_domain_event
from porterchain_api.booking_engine.booking_service import BookingService
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.numbers import generate_tracking_number
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.models import Customer, Order, Quote

_booking = BookingService()
_confirmation = BookingConfirmationService()
_customers = CustomerService()


def upsert_customer(db: Session, *, clerk_user_id: str, email: str, phone: str | None) -> Customer:
    return _customers.upsert(db, clerk_user_id=clerk_user_id, email=email, phone=phone)


def merge_anonymous_session(
    db: Session, quote: Quote, customer: Customer, anonymous_session_id: str | None
) -> None:
    _customers.merge_anonymous_session(db, quote, customer, anonymous_session_id)


def start_booking(
    db: Session,
    settings: Settings,
    *,
    quote_id: str,
    email: str,
    phone: str,
    clerk_user_id: str,
    anonymous_session_id: str | None,
) -> tuple[Quote, Customer, str | None]:
    return _booking.start_booking(
        db,
        settings,
        quote_id=quote_id,
        email=email,
        phone=phone,
        clerk_user_id=clerk_user_id,
        anonymous_session_id=anonymous_session_id,
    )


def complete_payment_and_create_order(
    db: Session,
    settings: Settings,
    quote: Quote,
    *,
    stripe_payment_intent_id: str | None = None,
    receipt_url: str | None = None,
) -> Order:
    return _confirmation.complete_payment_and_create_order(
        db,
        settings,
        quote,
        stripe_payment_intent_id=stripe_payment_intent_id,
        receipt_url=receipt_url,
    )


def record_abandoned_checkout(db: Session, quote: Quote, *, reason: str = "session_expired") -> None:
    _booking.record_abandoned_checkout(db, quote, reason=reason)


__all__ = [
    "complete_payment_and_create_order",
    "emit_domain_event",
    "generate_tracking_number",
    "merge_anonymous_session",
    "record_abandoned_checkout",
    "start_booking",
    "transition_order_state",
    "upsert_customer",
]

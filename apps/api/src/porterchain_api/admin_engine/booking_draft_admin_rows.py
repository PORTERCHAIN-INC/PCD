"""Admin booking-draft list/detail row — customer + payment + abandonment."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_draft_abandon import (
    ABANDONED_AFTER_MINUTES,
    ACTIVE_PRE_CONFIRM,
    is_abandoned,
)
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import Customer, Payment
from porterchain_api.domain.states import BookingDraftState


def draft_number(draft_id: str) -> str:
    return f"PBD-{draft_id[:8].upper()}"


def payment_for_draft(db: Session, draft: BookingDraft) -> Payment | None:
    if not draft.quote_id:
        return None
    return (
        db.query(Payment)
        .filter(Payment.quote_id == draft.quote_id)
        .order_by(Payment.created_at.desc())
        .first()
    )


def display_state(draft: BookingDraft) -> str:
    if draft.state == BookingDraftState.BOOKING_CONFIRMED.value and draft.order_id:
        return "CONVERTED_TO_ORDER"
    return draft.state


def draft_row(db: Session, draft: BookingDraft, now: datetime, *, merchant: Any | None) -> dict[str, Any]:
    customer = (
        db.query(Customer).filter(Customer.id == draft.customer_id).first()
        if draft.customer_id
        else None
    )
    payment = payment_for_draft(db, draft)
    expired = draft.state == BookingDraftState.EXPIRED.value or (
        draft.expires_at and now > draft.expires_at.replace(tzinfo=None)
    )
    return {
        "draft_id": draft.id,
        "draft_number": draft_number(draft.id),
        "session_id": draft.session_id,
        "visitor_id": draft.session_id,
        "customer_id": draft.customer_id,
        "customer_email": customer.email if customer else None,
        "merchant_id": merchant.id if merchant else None,
        "merchant_name": merchant.company_name if merchant else None,
        "quote_id": draft.quote_id,
        "booking_type": "merchant" if merchant else "individual",
        "state": draft.state,
        "display_state": display_state(draft),
        "current_step": draft.current_step,
        "payment_status": payment.status if payment else None,
        "vehicle_class": draft.vehicle_class,
        "amount_cents": draft.amount_cents,
        "currency": draft.currency,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
        "expires_at": draft.expires_at,
        "is_expired": expired,
        "is_abandoned": is_abandoned(draft, now),
        "booking_id": draft.booking_id,
        "order_id": draft.order_id,
    }

# Re-exports kept for existing importers (integration).
from porterchain_api.booking_draft_abandon import ACTIVE_PRE_CONFIRM  # noqa: E402, F401
from porterchain_api.booking_draft_abandon import ABANDONED_AFTER_MINUTES  # noqa: E402, F401

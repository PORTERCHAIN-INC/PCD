"""Booking draft compose — field apply, quote copy, payment lifecycle, dict view."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import Booking, Customer, Order, Payment, Quote
from porterchain_api.config import Settings
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.domain.states import BookingDraftState
from porterchain_api.schemas import CreateBookingDraftRequest, UpdateBookingDraftRequest


def create_or_update_draft(
    svc: Any,
    db: Session,
    settings: Settings,
    body: CreateBookingDraftRequest,
) -> BookingDraft:
    session_id = body.session_id
    existing = svc.find_active_draft(db, session_id=session_id)
    if existing and existing.state == BookingDraftState.DRAFT.value:
        return apply_update(svc, db, settings, existing, body, event_label="Draft Updated")

    draft = BookingDraft(
        session_id=session_id,
        state=BookingDraftState.DRAFT.value,
        current_step=body.current_step or "details",
        pickup=body.pickup.model_dump() if body.pickup else None,
        dropoff=body.dropoff.model_dump() if body.dropoff else None,
        additional_stops=[s.model_dump() for s in body.additional_stops] if body.additional_stops else None,
        vehicle_class=persist_vehicle_class(body.vehicle_class),
        package_type=body.package_type,
        weight_kg=body.weight_kg,
        dimensions=body.dimensions,
        declared_value_cents=body.declared_value_cents,
        special_instructions=body.special_instructions,
        promo_code=body.promo_code,
        estimated_pickup=body.estimated_pickup,
        estimated_delivery=body.estimated_delivery,
        schedule_mode=body.schedule_mode or "now",
        expires_at=svc._expires_at(settings),
    )
    db.add(draft)
    db.flush()
    svc._log_audit(
        db,
        draft,
        from_state=None,
        to_state=BookingDraftState.DRAFT.value,
        event_label="Draft Created",
        payload={"session_id": session_id},
    )
    db.commit()
    db.refresh(draft)
    return draft


def apply_update(
    svc: Any,
    db: Session,
    settings: Settings,
    draft: BookingDraft,
    body: CreateBookingDraftRequest | UpdateBookingDraftRequest,
    *,
    event_label: str,
) -> BookingDraft:
    if body.pickup:
        draft.pickup = body.pickup.model_dump()
    if body.dropoff:
        draft.dropoff = body.dropoff.model_dump()
    if body.additional_stops is not None:
        draft.additional_stops = [s.model_dump() for s in body.additional_stops]
    if body.vehicle_class is not None:
        draft.vehicle_class = persist_vehicle_class(body.vehicle_class)
    if body.package_type is not None:
        draft.package_type = body.package_type
    if body.weight_kg is not None:
        draft.weight_kg = body.weight_kg
    if body.dimensions is not None:
        draft.dimensions = body.dimensions
    if body.declared_value_cents is not None:
        draft.declared_value_cents = body.declared_value_cents
    if body.special_instructions is not None:
        draft.special_instructions = body.special_instructions
    if body.promo_code is not None:
        draft.promo_code = body.promo_code
    if body.estimated_pickup is not None:
        draft.estimated_pickup = body.estimated_pickup
    if body.estimated_delivery is not None:
        draft.estimated_delivery = body.estimated_delivery
    if body.schedule_mode is not None:
        draft.schedule_mode = body.schedule_mode
    if body.current_step is not None:
        draft.current_step = body.current_step
    draft.expires_at = svc._expires_at(settings)
    draft.updated_at = datetime.now(UTC)
    svc._log_audit(
        db,
        draft,
        from_state=draft.state,
        to_state=draft.state,
        event_label=event_label,
        payload={"current_step": draft.current_step},
    )
    db.commit()
    db.refresh(draft)
    return draft


def attach_quote(svc: Any, db: Session, quote: Quote, session_id: str | None) -> BookingDraft:
    existing = db.query(BookingDraft).filter(BookingDraft.quote_id == quote.id).first()
    if existing:
        return existing

    session_id = session_id or quote.visitor_session_id or quote.anonymous_session_id
    if not session_id:
        session_id = quote.id

    draft = svc.find_active_draft(db, session_id=session_id)
    if not draft:
        draft = BookingDraft(
            session_id=session_id,
            state=BookingDraftState.DRAFT.value,
            current_step="quote",
            expires_at=quote.expires_at,
        )
        db.add(draft)
        db.flush()
        svc._log_audit(
            db,
            draft,
            from_state=None,
            to_state=BookingDraftState.DRAFT.value,
            event_label="Draft Created",
            payload={"session_id": session_id},
        )

    draft.quote_id = quote.id
    draft.pickup = quote.pickup
    draft.dropoff = quote.dropoff
    draft.additional_stops = quote.additional_stops
    draft.vehicle_class = persist_vehicle_class(quote.vehicle_class)
    draft.package_type = quote.package_type
    draft.weight_kg = quote.weight_kg
    draft.dimensions = quote.dimensions
    draft.declared_value_cents = quote.declared_value_cents
    draft.special_instructions = quote.special_instructions
    draft.pricing_breakdown = quote.pricing_breakdown
    draft.amount_cents = quote.amount_cents
    draft.currency = quote.currency
    draft.distance_meters = quote.distance_meters
    draft.estimated_pickup = quote.scheduled_at
    draft.schedule_mode = quote.schedule_mode
    draft.expires_at = quote.expires_at

    if draft.state == BookingDraftState.DRAFT.value:
        svc.transition(
            db,
            draft,
            BookingDraftState.QUOTE_GENERATED,
            "Quote Generated",
            payload={"quote_id": quote.id, "amount_cents": quote.amount_cents},
            current_step="quote",
        )
    db.commit()
    db.refresh(draft)
    return draft


def merge_session_to_customer(
    svc: Any,
    db: Session,
    *,
    session_id: str,
    customer_id: str,
    quote_id: str | None = None,
) -> BookingDraft | None:
    query = db.query(BookingDraft).filter(
        BookingDraft.session_id == session_id,
        BookingDraft.state.in_(svc.ACTIVE_STATES),
    )
    drafts = query.order_by(BookingDraft.updated_at.desc()).all()
    if not drafts:
        return None

    primary = next((d for d in drafts if d.quote_id == quote_id), drafts[0])
    for draft in drafts:
        draft.customer_id = customer_id
    db.commit()

    if primary.state in svc._PRE_CUSTOMER_IDENTIFIED:
        svc.transition(
            db,
            primary,
            BookingDraftState.CUSTOMER_IDENTIFIED,
            "Customer Identified",
            actor_type="customer",
            actor_id=customer_id,
            payload={"quote_id": quote_id},
            current_step="review",
        )
        db.commit()
    db.refresh(primary)
    return primary


def on_customer_authenticated(
    svc: Any,
    db: Session,
    *,
    quote_id: str,
    customer_id: str,
    clerk_user_id: str,
) -> BookingDraft | None:
    draft = svc.get_by_quote_id(db, quote_id)
    if not draft:
        return None
    if draft.state in svc._PRE_CUSTOMER_IDENTIFIED:
        svc.transition(
            db,
            draft,
            BookingDraftState.CUSTOMER_IDENTIFIED,
            "Customer Identified",
            actor_type="customer",
            actor_id=customer_id,
            payload={"quote_id": quote_id},
            current_step="review",
        )
    if draft.state == BookingDraftState.CUSTOMER_IDENTIFIED.value:
        svc.transition(
            db,
            draft,
            BookingDraftState.AUTHENTICATED,
            "Customer Authenticated",
            actor_type="customer",
            actor_id=customer_id,
            payload={"clerk_user_id": clerk_user_id, "quote_id": quote_id},
            current_step="payment",
        )
        db.commit()
        db.refresh(draft)
    return draft


def on_payment_started(
    svc: Any,
    db: Session,
    quote: Quote,
    *,
    stripe_session_id: str | None = None,
    settings: Settings | None = None,
) -> BookingDraft | None:
    draft = svc.get_by_quote_id(db, quote.id)
    if not draft:
        return None
    if stripe_session_id:
        draft.stripe_checkout_session_id = stripe_session_id
    if settings is not None:
        draft.expires_at = svc._expires_at(settings)
    if draft.state != BookingDraftState.PAYMENT_PENDING.value:
        svc.transition(
            db,
            draft,
            BookingDraftState.PAYMENT_PENDING,
            "Payment Started",
            actor_type="customer",
            actor_id=quote.customer_id,
            payload={"quote_id": quote.id, "stripe_session_id": stripe_session_id},
            current_step="payment",
        )
    db.commit()
    db.refresh(draft)
    return draft


def on_payment_failed(
    svc: Any,
    db: Session,
    quote_id: str,
    *,
    reason: str,
) -> BookingDraft | None:
    draft = svc.get_by_quote_id(db, quote_id)
    if not draft:
        return None
    if draft.state == BookingDraftState.PAYMENT_PENDING.value:
        svc.transition(
            db,
            draft,
            BookingDraftState.PAYMENT_FAILED,
            "Payment Failed",
            payload={"reason": reason, "quote_id": quote_id},
            current_step="payment",
        )
        db.commit()
        db.refresh(draft)
    return draft


def on_payment_completed(
    svc: Any,
    db: Session,
    quote: Quote,
    *,
    order_id: str | None = None,
    booking_id: str | None = None,
) -> BookingDraft | None:
    draft = svc._raw_by_quote_id(db, quote.id)
    if not draft:
        return None
    draft.order_id = order_id
    draft.booking_id = booking_id
    if draft.state in (
        BookingDraftState.PAYMENT_COMPLETED.value,
        BookingDraftState.BOOKING_CONFIRMED.value,
    ):
        db.commit()
        db.refresh(draft)
        return draft
    if draft.state != BookingDraftState.PAYMENT_COMPLETED.value:
        svc.transition(
            db,
            draft,
            BookingDraftState.PAYMENT_COMPLETED,
            "Payment Completed",
            payload={"quote_id": quote.id, "order_id": order_id},
            current_step="confirmation",
        )
    db.commit()
    db.refresh(draft)
    return draft


def on_booking_confirmed(
    svc: Any,
    db: Session,
    quote: Quote,
    booking: Booking,
    order: Order,
) -> BookingDraft | None:
    draft = svc._raw_by_quote_id(db, quote.id)
    if not draft:
        return None
    draft.booking_id = booking.id
    draft.order_id = order.id
    if draft.state == BookingDraftState.BOOKING_CONFIRMED.value:
        db.commit()
        db.refresh(draft)
        return draft
    svc.transition(
        db,
        draft,
        BookingDraftState.BOOKING_CONFIRMED,
        "Booking Confirmed",
        payload={
            "booking_number": booking.booking_number,
            "order_id": order.id,
            "tracking_number": order.tracking_number,
        },
        current_step="confirmed",
    )
    db.commit()
    db.refresh(draft)
    return draft


def payment_status_for_draft(db: Session, draft: BookingDraft) -> str | None:
    if not draft.quote_id:
        return None
    payment = (
        db.query(Payment)
        .filter(Payment.quote_id == draft.quote_id)
        .order_by(Payment.created_at.desc())
        .first()
    )
    return payment.status if payment else None


def draft_to_dict(db: Session, draft: BookingDraft) -> dict[str, Any]:
    customer = (
        db.query(Customer).filter(Customer.id == draft.customer_id).first()
        if draft.customer_id
        else None
    )
    return {
        "draft_id": draft.id,
        "session_id": draft.session_id,
        "customer_id": draft.customer_id,
        "customer_email": customer.email if customer else None,
        "quote_id": draft.quote_id,
        "state": draft.state,
        "current_step": draft.current_step,
        "payment_status": payment_status_for_draft(db, draft),
        "pickup": draft.pickup,
        "dropoff": draft.dropoff,
        "additional_stops": draft.additional_stops,
        "vehicle_class": draft.vehicle_class,
        "package_type": draft.package_type,
        "weight_kg": draft.weight_kg,
        "dimensions": draft.dimensions,
        "declared_value_cents": draft.declared_value_cents,
        "special_instructions": draft.special_instructions,
        "pricing_breakdown": draft.pricing_breakdown,
        "taxes_cents": draft.taxes_cents,
        "discounts_cents": draft.discounts_cents,
        "promo_code": draft.promo_code,
        "amount_cents": draft.amount_cents,
        "currency": draft.currency,
        "estimated_pickup": draft.estimated_pickup,
        "estimated_delivery": draft.estimated_delivery,
        "booking_id": draft.booking_id,
        "order_id": draft.order_id,
        "expires_at": draft.expires_at,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }

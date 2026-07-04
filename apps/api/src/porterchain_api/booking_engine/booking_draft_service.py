"""Booking draft lifecycle — persistent server-side checkout state."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.repositories.booking_draft_repository import BookingDraftRepository
from porterchain_api.booking_draft_models import BookingDraft, BookingDraftAudit
from porterchain_api.config import Settings
from porterchain_api.domain.states import (
    BOOKING_DRAFT_TERMINAL,
    BookingDraftState,
    can_transition_booking_draft,
)
from porterchain_api.models import Booking, Customer, Order, Payment, Quote
from porterchain_api.schemas import CreateBookingDraftRequest, UpdateBookingDraftRequest


class BookingDraftService:
    _PRE_CUSTOMER_IDENTIFIED = frozenset({
        BookingDraftState.DRAFT.value,
        BookingDraftState.QUOTE_GENERATED.value,
    })

    def __init__(self) -> None:
        self._repo = BookingDraftRepository()

    ACTIVE_STATES = tuple(
        s.value
        for s in BookingDraftState
        if s not in BOOKING_DRAFT_TERMINAL and s != BookingDraftState.EXPIRED
    )

    def _expires_at(self, settings: Settings) -> datetime:
        return datetime.now(UTC) + timedelta(minutes=settings.booking_draft_ttl_minutes)

    def _log_audit(
        self,
        db: Session,
        draft: BookingDraft,
        *,
        from_state: str | None,
        to_state: str,
        event_label: str,
        actor_type: str = "system",
        actor_id: str | None = None,
        payload: dict | None = None,
    ) -> None:
        db.add(
            BookingDraftAudit(
                booking_draft_id=draft.id,
                from_state=from_state,
                to_state=to_state,
                event_label=event_label,
                actor_type=actor_type,
                actor_id=actor_id,
                payload=payload or {},
            )
        )
        emit_event(
            db,
            event_type=f"booking_draft.{event_label.lower().replace(' ', '_')}",
            aggregate_type="booking_draft",
            aggregate_id=draft.id,
            correlation_id=draft.session_id,
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "from_state": from_state,
                "to_state": to_state,
                "event_label": event_label,
                **(payload or {}),
            },
        )

    def transition(
        self,
        db: Session,
        draft: BookingDraft,
        to_state: BookingDraftState,
        event_label: str,
        *,
        actor_type: str = "system",
        actor_id: str | None = None,
        payload: dict | None = None,
        current_step: str | None = None,
    ) -> BookingDraft:
        from_state = BookingDraftState(draft.state)
        if not can_transition_booking_draft(from_state, to_state):
            raise ValueError(f"invalid_draft_transition:{from_state.value}->{to_state.value}")

        previous = draft.state
        draft.state = to_state.value
        if current_step:
            draft.current_step = current_step
        draft.updated_at = datetime.now(UTC)

        self._log_audit(
            db,
            draft,
            from_state=previous,
            to_state=to_state.value,
            event_label=event_label,
            actor_type=actor_type,
            actor_id=actor_id,
            payload=payload,
        )
        return draft

    def _raw_by_quote_id(self, db: Session, quote_id: str) -> BookingDraft | None:
        """Load draft without running expiry — used during verified payment finalization."""
        return self._repo.get_by_quote_id(db, quote_id)

    def expire_if_needed(self, db: Session, draft: BookingDraft) -> BookingDraft:
        if draft.state in {s.value for s in BOOKING_DRAFT_TERMINAL}:
            return draft
        if draft.state == BookingDraftState.EXPIRED.value:
            return draft
        # Do not expire while customer is on Stripe Checkout (masterrule §14).
        if (
            draft.state == BookingDraftState.PAYMENT_PENDING.value
            and draft.stripe_checkout_session_id
        ):
            return draft
        if datetime.now(UTC) <= draft.expires_at:
            return draft
        self.transition(
            db,
            draft,
            BookingDraftState.EXPIRED,
            "Draft Expired",
            payload={"expires_at": draft.expires_at.isoformat()},
        )
        db.commit()
        db.refresh(draft)
        return draft

    def get_by_id(self, db: Session, draft_id: str) -> BookingDraft | None:
        draft = self._repo.get_by_id(db, draft_id)
        if not draft:
            return None
        return self.expire_if_needed(db, draft)

    def get_by_quote_id(self, db: Session, quote_id: str) -> BookingDraft | None:
        draft = self._repo.get_by_quote_id(db, quote_id)
        if not draft:
            return None
        return self.expire_if_needed(db, draft)

    def find_active_draft(
        self,
        db: Session,
        *,
        session_id: str | None = None,
        customer_id: str | None = None,
        quote_id: str | None = None,
    ) -> BookingDraft | None:
        query = db.query(BookingDraft).filter(BookingDraft.state.in_(self.ACTIVE_STATES))
        if quote_id:
            query = query.filter(BookingDraft.quote_id == quote_id)
        elif customer_id:
            query = query.filter(BookingDraft.customer_id == customer_id)
        elif session_id:
            query = query.filter(BookingDraft.session_id == session_id)
        else:
            return None

        draft = query.order_by(BookingDraft.updated_at.desc()).first()
        if not draft:
            return None
        return self.expire_if_needed(db, draft)

    def create_or_update_draft(
        self,
        db: Session,
        settings: Settings,
        body: CreateBookingDraftRequest,
    ) -> BookingDraft:
        session_id = body.session_id
        existing = self.find_active_draft(db, session_id=session_id)
        if existing and existing.state == BookingDraftState.DRAFT.value:
            return self._apply_update(db, settings, existing, body, event_label="Draft Updated")

        draft = BookingDraft(
            session_id=session_id,
            state=BookingDraftState.DRAFT.value,
            current_step=body.current_step or "details",
            pickup=body.pickup.model_dump() if body.pickup else None,
            dropoff=body.dropoff.model_dump() if body.dropoff else None,
            additional_stops=[s.model_dump() for s in body.additional_stops] if body.additional_stops else None,
            vehicle_class=body.vehicle_class,
            package_type=body.package_type,
            weight_kg=body.weight_kg,
            dimensions=body.dimensions,
            declared_value_cents=body.declared_value_cents,
            special_instructions=body.special_instructions,
            promo_code=body.promo_code,
            estimated_pickup=body.estimated_pickup,
            estimated_delivery=body.estimated_delivery,
            schedule_mode=body.schedule_mode or "now",
            expires_at=self._expires_at(settings),
        )
        db.add(draft)
        db.flush()
        self._log_audit(
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

    def update_draft(
        self,
        db: Session,
        settings: Settings,
        draft: BookingDraft,
        body: UpdateBookingDraftRequest,
    ) -> BookingDraft:
        if draft.state in {s.value for s in BOOKING_DRAFT_TERMINAL}:
            raise ValueError("draft_not_editable")
        return self._apply_update(db, settings, draft, body, event_label="Draft Updated")

    def _apply_update(
        self,
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
            draft.vehicle_class = body.vehicle_class
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
        draft.expires_at = self._expires_at(settings)
        draft.updated_at = datetime.now(UTC)
        self._log_audit(
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

    def attach_quote(self, db: Session, quote: Quote, session_id: str | None) -> BookingDraft:
        existing = db.query(BookingDraft).filter(BookingDraft.quote_id == quote.id).first()
        if existing:
            return existing

        session_id = session_id or quote.visitor_session_id or quote.anonymous_session_id
        if not session_id:
            session_id = quote.id

        draft = self.find_active_draft(db, session_id=session_id)
        if not draft:
            draft = BookingDraft(
                session_id=session_id,
                state=BookingDraftState.DRAFT.value,
                current_step="quote",
                expires_at=quote.expires_at,
            )
            db.add(draft)
            db.flush()
            self._log_audit(
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
        draft.vehicle_class = quote.vehicle_class
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
            self.transition(
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
        self,
        db: Session,
        *,
        session_id: str,
        customer_id: str,
        quote_id: str | None = None,
    ) -> BookingDraft | None:
        """Associate anonymous drafts with the authenticated customer — no new draft."""
        query = db.query(BookingDraft).filter(
            BookingDraft.session_id == session_id,
            BookingDraft.state.in_(self.ACTIVE_STATES),
        )
        drafts = query.order_by(BookingDraft.updated_at.desc()).all()
        if not drafts:
            return None

        primary = next((d for d in drafts if d.quote_id == quote_id), drafts[0])
        for draft in drafts:
            draft.customer_id = customer_id
        db.commit()

        if primary.state in self._PRE_CUSTOMER_IDENTIFIED:
            self.transition(
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
        self,
        db: Session,
        *,
        quote_id: str,
        customer_id: str,
        clerk_user_id: str,
    ) -> BookingDraft | None:
        draft = self.get_by_quote_id(db, quote_id)
        if not draft:
            return None
        if draft.state in self._PRE_CUSTOMER_IDENTIFIED:
            self.transition(
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
            self.transition(
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
        self,
        db: Session,
        quote: Quote,
        *,
        stripe_session_id: str | None = None,
        settings: Settings | None = None,
    ) -> BookingDraft | None:
        draft = self.get_by_quote_id(db, quote.id)
        if not draft:
            return None
        if stripe_session_id:
            draft.stripe_checkout_session_id = stripe_session_id
        if settings is not None:
            draft.expires_at = self._expires_at(settings)
        if draft.state != BookingDraftState.PAYMENT_PENDING.value:
            self.transition(
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
        self,
        db: Session,
        quote_id: str,
        *,
        reason: str,
    ) -> BookingDraft | None:
        draft = self.get_by_quote_id(db, quote_id)
        if not draft:
            return None
        if draft.state == BookingDraftState.PAYMENT_PENDING.value:
            self.transition(
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
        self,
        db: Session,
        quote: Quote,
        *,
        order_id: str | None = None,
        booking_id: str | None = None,
    ) -> BookingDraft | None:
        draft = self._raw_by_quote_id(db, quote.id)
        if not draft:
            return None
        draft.order_id = order_id
        draft.booking_id = booking_id
        if draft.state != BookingDraftState.PAYMENT_COMPLETED.value:
            self.transition(
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
        self,
        db: Session,
        quote: Quote,
        booking: Booking,
        order: Order,
    ) -> BookingDraft | None:
        draft = self._raw_by_quote_id(db, quote.id)
        if not draft:
            return None
        draft.booking_id = booking.id
        draft.order_id = order.id
        self.transition(
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

    def restore_draft(self, db: Session, draft: BookingDraft) -> BookingDraft:
        if draft.state == BookingDraftState.EXPIRED.value:
            if datetime.now(UTC) > draft.expires_at:
                raise ValueError("draft_expired")
            resume_state = (
                BookingDraftState.PAYMENT_FAILED
                if draft.stripe_checkout_session_id
                else BookingDraftState.QUOTE_GENERATED
            )
            self.transition(
                db,
                draft,
                resume_state,
                "Draft Restored",
                payload={"resume_state": resume_state.value},
            )
            db.commit()
            db.refresh(draft)

        emit_event(
            db,
            event_type=E.BOOKING_DRAFT_RESTORED,
            aggregate_type="booking_draft",
            aggregate_id=draft.id,
            correlation_id=draft.session_id,
            payload={"quote_id": draft.quote_id, "state": draft.state, "current_step": draft.current_step},
        )
        db.commit()
        return draft

    def cancel_draft(
        self,
        db: Session,
        draft: BookingDraft,
        *,
        actor_type: str = "admin",
        actor_id: str | None = None,
        reason: str | None = None,
    ) -> BookingDraft:
        self.transition(
            db,
            draft,
            BookingDraftState.CANCELLED,
            "Draft Cancelled",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={"reason": reason},
        )
        db.commit()
        db.refresh(draft)
        return draft

    def extend_expiry(
        self,
        db: Session,
        settings: Settings,
        draft: BookingDraft,
        *,
        extra_minutes: int | None = None,
        actor_id: str | None = None,
    ) -> BookingDraft:
        minutes = extra_minutes or settings.booking_draft_ttl_minutes
        draft.expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
        if draft.state == BookingDraftState.EXPIRED.value:
            resume = (
                BookingDraftState.PAYMENT_FAILED
                if draft.stripe_checkout_session_id
                else BookingDraftState.QUOTE_GENERATED
            )
            self.transition(
                db,
                draft,
                resume,
                "Draft Restored",
                actor_type="admin",
                actor_id=actor_id,
                payload={"extended_minutes": minutes},
            )
        else:
            self._log_audit(
                db,
                draft,
                from_state=draft.state,
                to_state=draft.state,
                event_label="Expiry Extended",
                actor_type="admin",
                actor_id=actor_id,
                payload={"expires_at": draft.expires_at.isoformat(), "extra_minutes": minutes},
            )
        db.commit()
        db.refresh(draft)
        return draft

    def list_for_admin(
        self,
        db: Session,
        *,
        state: str | None = None,
        search: str | None = None,
        customer_id: str | None = None,
        limit: int = 100,
    ) -> list[BookingDraft]:
        query = db.query(BookingDraft).order_by(BookingDraft.updated_at.desc())
        if state:
            query = query.filter(BookingDraft.state == state)
        if customer_id:
            query = query.filter(BookingDraft.customer_id == customer_id)
        if search:
            like = f"%{search}%"
            query = query.filter(
                (BookingDraft.id.like(like))
                | (BookingDraft.session_id.like(like))
                | (BookingDraft.quote_id.like(like))
            )
        return query.limit(limit).all()

    def assert_access(
        self,
        db: Session,
        draft: BookingDraft,
        *,
        session_id: str | None = None,
        clerk_user_id: str | None = None,
    ) -> None:
        """Require visitor session or owning Clerk customer (masterrule §10, §15)."""
        if clerk_user_id and draft.customer_id:
            customer = db.query(Customer).filter(Customer.id == draft.customer_id).first()
            if customer and customer.clerk_user_id == clerk_user_id:
                return
        if session_id and session_id == draft.session_id:
            return
        raise PermissionError("draft_access_denied")

    def restore_active(
        self,
        db: Session,
        *,
        session_id: str | None = None,
        clerk_user_id: str | None = None,
    ) -> BookingDraft:
        draft = None
        if clerk_user_id:
            customer = db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()
            if customer:
                draft = self.find_active_draft(db, customer_id=customer.id)
        if not draft and session_id:
            draft = self.find_active_draft(db, session_id=session_id)
        if not draft:
            raise LookupError("draft_not_found")
        return self.restore_draft(db, draft)

    def payment_status_for_draft(self, db: Session, draft: BookingDraft) -> str | None:
        if not draft.quote_id:
            return None
        payment = (
            db.query(Payment)
            .filter(Payment.quote_id == draft.quote_id)
            .order_by(Payment.created_at.desc())
            .first()
        )
        return payment.status if payment else None

    def draft_to_dict(self, db: Session, draft: BookingDraft) -> dict[str, Any]:
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
            "payment_status": self.payment_status_for_draft(db, draft),
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

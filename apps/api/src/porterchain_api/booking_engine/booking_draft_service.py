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
from porterchain_api.booking_models import Booking, Customer, Order, Quote
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
        from porterchain_api.booking_engine.draft_compose import create_or_update_draft as _create

        return _create(self, db, settings, body)

    def update_draft(
        self,
        db: Session,
        settings: Settings,
        draft: BookingDraft,
        body: UpdateBookingDraftRequest,
    ) -> BookingDraft:
        if draft.state in {s.value for s in BOOKING_DRAFT_TERMINAL}:
            raise ValueError("draft_not_editable")
        from porterchain_api.booking_engine.draft_compose import apply_update

        return apply_update(self, db, settings, draft, body, event_label="Draft Updated")

    def _apply_update(
        self,
        db: Session,
        settings: Settings,
        draft: BookingDraft,
        body: CreateBookingDraftRequest | UpdateBookingDraftRequest,
        *,
        event_label: str,
    ) -> BookingDraft:
        from porterchain_api.booking_engine.draft_compose import apply_update

        return apply_update(self, db, settings, draft, body, event_label=event_label)

    def attach_quote(self, db: Session, quote: Quote, session_id: str | None) -> BookingDraft:
        from porterchain_api.booking_engine.draft_compose import attach_quote as _attach

        return _attach(self, db, quote, session_id)

    def merge_session_to_customer(
        self,
        db: Session,
        *,
        session_id: str,
        customer_id: str,
        quote_id: str | None = None,
    ) -> BookingDraft | None:
        from porterchain_api.booking_engine.draft_compose import merge_session_to_customer as _merge

        return _merge(self, db, session_id=session_id, customer_id=customer_id, quote_id=quote_id)

    def on_customer_authenticated(
        self,
        db: Session,
        *,
        quote_id: str,
        customer_id: str,
        clerk_user_id: str,
    ) -> BookingDraft | None:
        from porterchain_api.booking_engine.draft_compose import on_customer_authenticated as _auth

        return _auth(self, db, quote_id=quote_id, customer_id=customer_id, clerk_user_id=clerk_user_id)

    def on_payment_started(
        self,
        db: Session,
        quote: Quote,
        *,
        stripe_session_id: str | None = None,
        settings: Settings | None = None,
    ) -> BookingDraft | None:
        from porterchain_api.booking_engine.draft_compose import on_payment_started as _started

        return _started(self, db, quote, stripe_session_id=stripe_session_id, settings=settings)

    def on_payment_failed(
        self,
        db: Session,
        quote_id: str,
        *,
        reason: str,
    ) -> BookingDraft | None:
        from porterchain_api.booking_engine.draft_compose import on_payment_failed as _failed

        return _failed(self, db, quote_id, reason=reason)

    def on_payment_completed(
        self,
        db: Session,
        quote: Quote,
        *,
        order_id: str | None = None,
        booking_id: str | None = None,
    ) -> BookingDraft | None:
        from porterchain_api.booking_engine.draft_compose import on_payment_completed as _completed

        return _completed(self, db, quote, order_id=order_id, booking_id=booking_id)

    def on_booking_confirmed(
        self,
        db: Session,
        quote: Quote,
        booking: Booking,
        order: Order,
    ) -> BookingDraft | None:
        from porterchain_api.booking_engine.draft_compose import on_booking_confirmed as _confirmed

        return _confirmed(self, db, quote, booking, order)

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
        from porterchain_api.booking_engine.draft_compose import payment_status_for_draft as _status

        return _status(db, draft)

    def draft_to_dict(self, db: Session, draft: BookingDraft) -> dict[str, Any]:
        from porterchain_api.booking_engine.draft_compose import draft_to_dict as _as_dict

        return _as_dict(db, draft)

"""Booking draft expiration and payment reconciliation — worker jobs (masterrule §10)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.config import Settings
from porterchain_api.domain.states import BookingDraftState
from porterchain_api.models import Booking, Order, Payment, Quote

logger = logging.getLogger(__name__)


class BookingDraftReconciliationService:
    def __init__(self) -> None:
        self._drafts = BookingDraftService()
        self._confirmation = BookingConfirmationService()

    def expire_stale_drafts(self, db: Session) -> int:
        """Expire drafts past TTL that are not in active Stripe checkout."""
        now = datetime.now(UTC)
        terminal = {BookingDraftState.BOOKING_CONFIRMED.value, BookingDraftState.CANCELLED.value}
        rows = (
            db.query(BookingDraft)
            .filter(
                BookingDraft.state.notin_(terminal),
                BookingDraft.state != BookingDraftState.EXPIRED.value,
                BookingDraft.expires_at < now,
            )
            .limit(200)
            .all()
        )
        expired = 0
        for draft in rows:
            if (
                draft.state == BookingDraftState.PAYMENT_PENDING.value
                and draft.stripe_checkout_session_id
            ):
                continue
            try:
                self._drafts.transition(
                    db,
                    draft,
                    BookingDraftState.EXPIRED,
                    "Draft Expired (worker)",
                    payload={"expires_at": draft.expires_at.isoformat()},
                )
                db.commit()
                expired += 1
            except ValueError:
                db.rollback()
        return expired

    def reconcile_paid_orders(self, db: Session, settings: Settings) -> int:
        """Repair drafts that lag behind verified payments / created orders."""
        repaired = 0
        rows = (
            db.query(Order)
            .filter(Order.quote_id.isnot(None))
            .order_by(Order.created_at.desc())
            .limit(100)
            .all()
        )
        for order in rows:
            draft = self._drafts._raw_by_quote_id(db, order.quote_id)  # noqa: SLF001
            if not draft:
                continue
            if draft.state == BookingDraftState.BOOKING_CONFIRMED.value:
                continue
            payment = (
                db.query(Payment)
                .filter(Payment.quote_id == order.quote_id, Payment.status == "SUCCEEDED")
                .first()
            )
            if not payment:
                continue
            quote = db.query(Quote).filter(Quote.id == order.quote_id).first()
            if not quote:
                continue
            try:
                booking = db.query(Booking).filter(Booking.order_id == order.id).first()
                self._drafts.on_payment_completed(
                    db, quote, order_id=order.id, booking_id=booking.id if booking else None
                )
                if booking:
                    self._drafts.on_booking_confirmed(db, quote, booking, order)
                db.commit()
                repaired += 1
                logger.info("reconciled draft %s for order %s", draft.id, order.id)
            except Exception:
                db.rollback()
                logger.exception("draft reconcile failed order=%s", order.id)
        return repaired

    def run_cycle(self, db: Session, settings: Settings) -> dict[str, int]:
        expired = self.expire_stale_drafts(db)
        repaired = self.reconcile_paid_orders(db, settings)
        return {"expired": expired, "repaired": repaired}

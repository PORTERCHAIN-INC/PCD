"""Admin Booking Draft Management — Application Service.

Wraps BookingDraftService for admin operations, analytics, and enriched views.
Business logic lives here; routers orchestrate only (masterrule §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.booking_draft_admin_rows import (
    ACTIVE_PRE_CONFIRM,
    display_state,
    draft_row,
    is_abandoned,
    payment_for_draft,
)
from porterchain_api.booking_draft_models import BookingDraft, BookingDraftAudit
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.config import Settings
from porterchain_api.domain.states import BOOKING_DRAFT_TERMINAL, BookingDraftState
from porterchain_api.merchant_engine.quote_snapshot import sanitize_pricing_breakdown
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.booking_models import Customer, DomainEvent, Order, Payment, Quote


@dataclass
class AdminDraftFilters:
    state: str | None = None
    search: str | None = None
    customer_id: str | None = None
    merchant_id: str | None = None
    booking_type: str | None = None
    vehicle_class: str | None = None
    payment_status: str | None = None
    current_step: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    price_min_cents: int | None = None
    price_max_cents: int | None = None
    expired_only: bool = False
    abandoned_only: bool = False
    limit: int = 500


class AdminBookingDraftService:
    def __init__(self) -> None:
        self._drafts = BookingDraftService()

    def _payment_for_draft(self, db: Session, draft: BookingDraft) -> Payment | None:
        return payment_for_draft(db, draft)

    def _merchant_for_draft(self, db: Session, draft: BookingDraft) -> Any | None:
        if not draft.order_id:
            return None
        order = db.query(Order).filter(Order.id == draft.order_id).first()
        if not order or not order.merchant_id:
            return None
        return get_merchant(db, order.merchant_id)

    def _display_state(self, draft: BookingDraft) -> str:
        return display_state(draft)

    def _is_abandoned(self, draft: BookingDraft, now: datetime) -> bool:
        return is_abandoned(draft, now)

    def _row(self, db: Session, draft: BookingDraft, now: datetime) -> dict[str, Any]:
        return draft_row(db, draft, now, merchant=self._merchant_for_draft(db, draft))

    def list_drafts(self, db: Session, filters: AdminDraftFilters) -> list[dict[str, Any]]:
        now = datetime.now(UTC).replace(tzinfo=None)
        q = db.query(BookingDraft).order_by(BookingDraft.updated_at.desc())

        if filters.state:
            q = q.filter(BookingDraft.state == filters.state)
        if filters.customer_id:
            q = q.filter(BookingDraft.customer_id == filters.customer_id)
        if filters.vehicle_class:
            q = q.filter(BookingDraft.vehicle_class == filters.vehicle_class)
        if filters.current_step:
            q = q.filter(BookingDraft.current_step == filters.current_step)
        if filters.date_from:
            q = q.filter(BookingDraft.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(BookingDraft.created_at <= filters.date_to)
        if filters.price_min_cents is not None:
            q = q.filter(BookingDraft.amount_cents >= filters.price_min_cents)
        if filters.price_max_cents is not None:
            q = q.filter(BookingDraft.amount_cents <= filters.price_max_cents)
        if filters.expired_only:
            q = q.filter(BookingDraft.state == BookingDraftState.EXPIRED.value)
        if filters.search:
            like = f"%{filters.search}%"
            q = q.filter(
                or_(
                    BookingDraft.id.like(like),
                    BookingDraft.session_id.like(like),
                    BookingDraft.quote_id.like(like),
                )
            )

        rows = q.limit(filters.limit).all()
        out: list[dict[str, Any]] = []
        for draft in rows:
            row = self._row(db, draft, now)
            if filters.booking_type and row["booking_type"] != filters.booking_type:
                continue
            if filters.merchant_id and row["merchant_id"] != filters.merchant_id:
                continue
            if filters.payment_status and row["payment_status"] != filters.payment_status:
                continue
            if filters.abandoned_only and not row["is_abandoned"]:
                continue
            out.append(row)
        return out

    def get_detail(self, db: Session, settings: Settings, draft_id: str) -> dict[str, Any] | None:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft:
            return None
        now = datetime.now(UTC).replace(tzinfo=None)
        row = self._row(db, draft, now)
        payment = self._payment_for_draft(db, draft)
        quote = db.query(Quote).filter(Quote.id == draft.quote_id).first() if draft.quote_id else None
        continue_url = None
        if draft.quote_id:
            base = settings.retail_checkout_cancel_url.rsplit("?", 1)[0]
            continue_url = f"{base}?quote_id={draft.quote_id}&draft_id={draft.id}"

        events = (
            db.query(DomainEvent)
            .filter(
                DomainEvent.aggregate_type == "booking_draft",
                DomainEvent.aggregate_id == draft.id,
            )
            .order_by(DomainEvent.occurred_at.asc())
            .all()
        )

        return {
            **row,
            "pickup": draft.pickup,
            "dropoff": draft.dropoff,
            "additional_stops": draft.additional_stops,
            "package_type": draft.package_type,
            "weight_kg": draft.weight_kg,
            "dimensions": draft.dimensions,
            "declared_value_cents": draft.declared_value_cents,
            "booking_mode": (quote.parcels or {}).get("booking_mode")
            if quote and isinstance(quote.parcels, dict)
            else None,
            "parcels": (quote.parcels or {}).get("items")
            if quote and isinstance(quote.parcels, dict) and isinstance(quote.parcels.get("items"), list)
            else [],
            "special_instructions": draft.special_instructions,
            "pricing_breakdown": sanitize_pricing_breakdown(draft.pricing_breakdown),
            "taxes_cents": draft.taxes_cents,
            "discounts_cents": draft.discounts_cents,
            "promo_code": draft.promo_code,
            "distance_meters": draft.distance_meters,
            "estimated_pickup": draft.estimated_pickup,
            "estimated_delivery": draft.estimated_delivery,
            "schedule_mode": draft.schedule_mode,
            "stripe_checkout_session_id": draft.stripe_checkout_session_id
            or (payment.stripe_checkout_session_id if payment else None),
            "stripe_payment_intent_id": payment.stripe_payment_intent_id if payment else None,
            "payment_id": payment.id if payment else None,
            "quote_amount_cents": quote.amount_cents if quote else None,
            "quote_state": quote.state if quote else None,
            "continue_url": continue_url,
            "audits": [
                {
                    "event_label": a.event_label,
                    "from_state": a.from_state,
                    "to_state": a.to_state,
                    "actor_type": a.actor_type,
                    "actor_id": a.actor_id,
                    "occurred_at": a.occurred_at.isoformat(),
                    "payload": a.payload,
                }
                for a in draft.audits
            ],
            "domain_events": [
                {
                    "event_type": e.event_type,
                    "actor_type": e.actor_type,
                    "actor_id": e.actor_id,
                    "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                    "payload": e.payload,
                }
                for e in events
            ],
            "abandoned_minutes": (
                int((now - draft.updated_at.replace(tzinfo=None)).total_seconds() / 60)
                if self._is_abandoned(draft, now)
                else None
            ),
        }

    def analytics(self, db: Session) -> dict[str, Any]:
        now = datetime.now(UTC).replace(tzinfo=None)
        total = db.query(func.count(BookingDraft.id)).scalar() or 0
        confirmed = (
            db.query(func.count(BookingDraft.id))
            .filter(BookingDraft.state == BookingDraftState.BOOKING_CONFIRMED.value)
            .scalar()
            or 0
        )
        cancelled = (
            db.query(func.count(BookingDraft.id))
            .filter(BookingDraft.state == BookingDraftState.CANCELLED.value)
            .scalar()
            or 0
        )
        expired = (
            db.query(func.count(BookingDraft.id))
            .filter(BookingDraft.state == BookingDraftState.EXPIRED.value)
            .scalar()
            or 0
        )
        payment_failed = (
            db.query(func.count(BookingDraft.id))
            .filter(BookingDraft.state == BookingDraftState.PAYMENT_FAILED.value)
            .scalar()
            or 0
        )
        started = total - cancelled
        conversion_rate = round((confirmed / started) * 100, 1) if started else 0.0
        abandonment_rate = round(((expired + payment_failed) / started) * 100, 1) if started else 0.0

        payments = db.query(Payment).join(Quote, Payment.quote_id == Quote.id).all()
        pay_total = len(payments)
        pay_success = sum(1 for p in payments if p.status == "SUCCEEDED")
        payment_success_rate = round((pay_success / pay_total) * 100, 1) if pay_total else 0.0

        completed = (
            db.query(BookingDraft)
            .filter(BookingDraft.state == BookingDraftState.BOOKING_CONFIRMED.value)
            .all()
        )
        durations: list[float] = []
        for d in completed:
            if d.created_at and d.updated_at:
                c = d.created_at.replace(tzinfo=None)
                u = d.updated_at.replace(tzinfo=None)
                durations.append((u - c).total_seconds() / 60)
        avg_completion_minutes = round(sum(durations) / len(durations), 1) if durations else 0.0

        step_counts: dict[str, int] = {}
        failed_audits = (
            db.query(BookingDraftAudit)
            .filter(BookingDraftAudit.event_label.in_(["Payment Failed", "Draft Expired"]))
            .all()
        )
        for a in failed_audits:
            step = (a.payload or {}).get("current_step") or a.to_state
            step_counts[step] = step_counts.get(step, 0) + 1
        failure_step = max(step_counts, key=step_counts.get) if step_counts else None

        lost_cents = (
            db.query(func.coalesce(func.sum(BookingDraft.amount_cents), 0))
            .filter(
                BookingDraft.state.in_(
                    [
                        BookingDraftState.EXPIRED.value,
                        BookingDraftState.PAYMENT_FAILED.value,
                        BookingDraftState.CANCELLED.value,
                    ]
                ),
                BookingDraft.order_id.is_(None),
            )
            .scalar()
            or 0
        )

        restored = (
            db.query(func.count(BookingDraftAudit.id))
            .filter(BookingDraftAudit.event_label.in_(["Draft Restored", "Expiry Extended"]))
            .scalar()
            or 0
        )
        recovery_rate = round((restored / expired) * 100, 1) if expired else 0.0

        return {
            "total_drafts": total,
            "confirmed_drafts": confirmed,
            "conversion_rate_percent": conversion_rate,
            "abandonment_rate_percent": abandonment_rate,
            "payment_success_rate_percent": payment_success_rate,
            "avg_completion_minutes": avg_completion_minutes,
            "most_common_failure_step": failure_step,
            "revenue_lost_cents": int(lost_cents),
            "recovery_rate_percent": recovery_rate,
            "active_drafts": db.query(func.count(BookingDraft.id)).filter(BookingDraft.state.in_(ACTIVE_PRE_CONFIRM)).scalar() or 0,
            "abandoned_now": len(self.abandoned(db)),
        }

    def abandoned(self, db: Session, *, limit: int = 100) -> list[dict[str, Any]]:
        now = datetime.now(UTC).replace(tzinfo=None)
        rows = (
            db.query(BookingDraft)
            .filter(BookingDraft.state.in_(ACTIVE_PRE_CONFIRM + (BookingDraftState.EXPIRED.value,)))
            .order_by(BookingDraft.updated_at.asc())
            .limit(limit * 3)
            .all()
        )
        out: list[dict[str, Any]] = []
        for draft in rows:
            if not self._is_abandoned(draft, now):
                continue
            row = self._row(db, draft, now)
            row["abandoned_minutes"] = int(
                (now - draft.updated_at.replace(tzinfo=None)).total_seconds() / 60
            )
            row["last_step"] = draft.current_step
            row["reason"] = (
                "Expired"
                if draft.state == BookingDraftState.EXPIRED.value
                else f"Inactive for {row['abandoned_minutes']}m at step {draft.current_step}"
            )
            out.append(row)
            if len(out) >= limit:
                break
        return out

    def restore(self, db: Session, settings: Settings, draft_id: str, *, actor_id: str) -> BookingDraft:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft:
            raise LookupError("draft_not_found")
        self._drafts.extend_expiry(db, settings, draft, actor_id=actor_id)
        return self._drafts.restore_draft(db, draft)

    def force_expire(self, db: Session, draft_id: str, *, actor_id: str) -> BookingDraft:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft:
            raise LookupError("draft_not_found")
        if draft.state in {s.value for s in BOOKING_DRAFT_TERMINAL}:
            raise ValueError("draft_terminal")
        self._drafts.transition(
            db,
            draft,
            BookingDraftState.EXPIRED,
            "Draft Expired",
            actor_type="admin",
            actor_id=actor_id,
            payload={"forced": True},
        )
        db.commit()
        db.refresh(draft)
        return draft

    def duplicate(
        self, db: Session, settings: Settings, draft_id: str, *, actor_id: str
    ) -> BookingDraft:
        source = self._drafts.get_by_id(db, draft_id)
        if not source:
            raise LookupError("draft_not_found")
        clone = BookingDraft(
            session_id=f"{source.session_id}-dup-{draft_id[:6]}",
            customer_id=source.customer_id,
            state=BookingDraftState.QUOTE_GENERATED.value if source.quote_id else BookingDraftState.DRAFT.value,
            current_step=source.current_step,
            pickup=source.pickup,
            dropoff=source.dropoff,
            additional_stops=source.additional_stops,
            vehicle_class=source.vehicle_class,
            package_type=source.package_type,
            weight_kg=source.weight_kg,
            dimensions=source.dimensions,
            declared_value_cents=source.declared_value_cents,
            special_instructions=source.special_instructions,
            pricing_breakdown=source.pricing_breakdown,
            taxes_cents=source.taxes_cents,
            discounts_cents=source.discounts_cents,
            promo_code=source.promo_code,
            amount_cents=source.amount_cents,
            currency=source.currency,
            distance_meters=source.distance_meters,
            estimated_pickup=source.estimated_pickup,
            estimated_delivery=source.estimated_delivery,
            schedule_mode=source.schedule_mode,
            expires_at=self._drafts._expires_at(settings),
        )
        db.add(clone)
        db.flush()
        self._drafts._log_audit(
            db,
            clone,
            from_state=None,
            to_state=clone.state,
            event_label="Draft Duplicated",
            actor_type="admin",
            actor_id=actor_id,
            payload={"source_draft_id": source.id},
        )
        db.commit()
        db.refresh(clone)
        return clone

    def send_payment_link(
        self, db: Session, settings: Settings, draft_id: str
    ) -> dict[str, str | None]:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft:
            raise LookupError("draft_not_found")
        if not draft.quote_id or not draft.customer_id:
            raise ValueError("draft_missing_quote_or_customer")
        quote = db.query(Quote).filter(Quote.id == draft.quote_id).first()
        customer = db.query(Customer).filter(Customer.id == draft.customer_id).first()
        if not quote or not customer:
            raise ValueError("draft_missing_quote_or_customer")
        from porterchain_api.booking_engine.payment_service import PaymentService

        checkout_url, payment = PaymentService().start_payment(db, settings, quote, customer)
        return {
            "checkout_url": checkout_url,
            "payment_id": payment.id,
            "stripe_checkout_session_id": payment.stripe_checkout_session_id,
        }

    def extend_draft(
        self,
        db: Session,
        settings: Settings,
        draft_id: str,
        *,
        extra_minutes: int | None,
        actor_id: str,
    ) -> BookingDraft:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft:
            raise LookupError("draft_not_found")
        return self._drafts.extend_expiry(
            db, settings, draft, extra_minutes=extra_minutes, actor_id=actor_id
        )

    def cancel_draft(
        self,
        db: Session,
        draft_id: str,
        *,
        actor_id: str,
        reason: str | None,
    ) -> BookingDraft:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft:
            raise LookupError("draft_not_found")
        return self._drafts.cancel_draft(
            db, draft, actor_type="admin", actor_id=actor_id, reason=reason
        )

    def bulk_action(
        self,
        db: Session,
        settings: Settings,
        *,
        draft_ids: list[str],
        action: str,
        actor_id: str,
        extra_minutes: int | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        results: list[dict[str, str]] = []
        for draft_id in draft_ids:
            try:
                if action == "extend":
                    draft = self._drafts.get_by_id(db, draft_id)
                    if draft:
                        self._drafts.extend_expiry(
                            db, settings, draft, extra_minutes=extra_minutes, actor_id=actor_id
                        )
                        results.append({"draft_id": draft_id, "status": "ok"})
                elif action == "cancel":
                    draft = self._drafts.get_by_id(db, draft_id)
                    if draft:
                        self._drafts.cancel_draft(
                            db, draft, actor_type="admin", actor_id=actor_id, reason=reason
                        )
                        results.append({"draft_id": draft_id, "status": "ok"})
                elif action == "expire":
                    self.force_expire(db, draft_id, actor_id=actor_id)
                    results.append({"draft_id": draft_id, "status": "ok"})
                else:
                    results.append({"draft_id": draft_id, "status": "unknown_action"})
            except Exception as exc:
                results.append({"draft_id": draft_id, "status": "error", "detail": str(exc)})
        return {"action": action, "results": results}

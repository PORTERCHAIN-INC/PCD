"""Admin phone-book booking for retail customers — quote + draft + Stripe link."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.config import Settings
from porterchain_api.models import Customer, Quote
from porterchain_api.schemas_booking import AddressInput, CreateQuoteRequest


class CustomerBookingAdminService:
    """Create retail booking drafts for existing customers (Stripe only, no cash)."""

    def create_for_customer(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        customer_id: str,
        *,
        pickup: dict[str, Any],
        dropoff: dict[str, Any],
        vehicle_class: str,
        package_type: str = "looseParcel",
        weight_kg: float | None = None,
        dimensions: str | None = None,
        declared_value_cents: int | None = None,
        special_instructions: str | None = None,
        scheduled_at: Any,
        schedule_mode: str = "now",
        send_payment_link: bool = False,
    ) -> dict[str, Any]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        if (customer.privacy_status or "") == "deletion_hold":
            raise ValueError("customer_privacy_hold")

        session_id = f"admin-cust-{customer_id[:8]}-{uuid.uuid4().hex[:12]}"
        body = CreateQuoteRequest(
            anonymous_session_id=session_id,
            visitor_session_id=session_id,
            pickup=AddressInput(**pickup),
            dropoff=AddressInput(**dropoff),
            vehicle_class=vehicle_class,
            package_type=package_type or "looseParcel",
            weight_kg=weight_kg,
            dimensions=dimensions,
            declared_value_cents=declared_value_cents,
            special_instructions=special_instructions,
            scheduled_at=scheduled_at,
            schedule_mode=schedule_mode or "now",
        )
        quote = QuoteService().create_quote(db, settings, body)
        quote.customer_id = customer.id
        db.add(quote)
        db.commit()
        db.refresh(quote)

        drafts = BookingDraftService()
        draft = drafts.merge_session_to_customer(
            db,
            session_id=session_id,
            customer_id=customer.id,
            quote_id=quote.id,
        )
        if draft is None:
            draft = db.query(BookingDraft).filter(BookingDraft.quote_id == quote.id).first()
            if not draft:
                raise ValueError("draft_attach_failed")
            draft.customer_id = customer.id
            db.commit()
            db.refresh(draft)

        if draft.quote_id != quote.id:
            draft.quote_id = quote.id
            db.commit()
            db.refresh(draft)

        out: dict[str, Any] = {
            "draft_id": draft.id,
            "draft_number": f"BD-{draft.id[:8].upper()}",
            "quote_id": quote.id,
            "customer_id": customer.id,
            "amount_cents": int(quote.amount_cents or 0),
            "currency": quote.currency or "cad",
            "state": draft.state,
            "checkout_url": None,
            "payment_id": None,
            "stripe_checkout_session_id": None,
        }
        if send_payment_link:
            pay = self._start_checkout(db, settings, draft)
            out["checkout_url"] = pay.get("checkout_url")
            out["payment_id"] = pay.get("payment_id")
            out["stripe_checkout_session_id"] = pay.get("stripe_checkout_session_id")

        log_admin_audit(
            db,
            ctx,
            action="customer.booking_draft.create",
            resource_type="customer",
            resource_id=customer_id,
            payload={
                "draft_id": out["draft_id"],
                "quote_id": out["quote_id"],
                "send_payment_link": send_payment_link,
            },
        )
        db.commit()
        return out

    def send_payment_link_for_customer(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        *,
        customer_id: str,
        draft_id: str,
    ) -> dict[str, str | None]:
        draft = db.get(BookingDraft, draft_id)
        if not draft or draft.customer_id != customer_id:
            raise LookupError("draft_not_found")
        result = self._start_checkout(db, settings, draft)
        log_admin_audit(
            db,
            ctx,
            action="customer.booking_draft.send_payment_link",
            resource_type="booking_draft",
            resource_id=draft_id,
            payload={"customer_id": customer_id},
        )
        db.commit()
        return result

    def _start_checkout(
        self, db: Session, settings: Settings, draft: BookingDraft
    ) -> dict[str, str | None]:
        if not draft.quote_id or not draft.customer_id:
            raise ValueError("draft_missing_quote_or_customer")
        quote = db.get(Quote, draft.quote_id)
        customer = db.get(Customer, draft.customer_id)
        if not quote or not customer:
            raise ValueError("draft_missing_quote_or_customer")
        checkout_url, payment = PaymentService().start_payment(db, settings, quote, customer)
        return {
            "checkout_url": checkout_url,
            "payment_id": payment.id,
            "stripe_checkout_session_id": payment.stripe_checkout_session_id,
        }

"""GDPR/CCPA/PIPEDA data subject requests (§11.1.8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from porterchain_shared.events.catalog import DomainEventType
from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_models import Customer, Order
from porterchain_api.merchant_engine.privacy import (
    MerchantPrivacyService,
)

PRIVACY_ERROR_MESSAGES: dict[str, str] = {
    "merchant_not_found": "That company was not found.",
    "merchant_not_closed": "Close this company first. Erasure only runs after close.",
    "close_blocked_live_orders": "Live orders are still open. Finish or cancel them before erasure.",
    "close_blocked_outstanding_ar": "Outstanding invoices must be collected first.",
}

def privacy_error_message(code: str) -> str:
    return PRIVACY_ERROR_MESSAGES.get(code, code)


class PrivacyService:
    def __init__(self) -> None:
        self._merchants = MerchantPrivacyService()

    def export_merchant(self, db: Session, merchant: Any, *, actor_user_id: str) -> dict[str, Any]:
        return self._merchants.export_merchant(db, merchant, actor_user_id=actor_user_id)

    def privacy_status(self, db: Session, merchant: Any, *, log_limit: int = 40) -> dict[str, Any]:
        return self._merchants.privacy_status(db, merchant, log_limit=log_limit)

    def request_merchant_deletion(
        self,
        db: Session,
        merchant: Any,
        *,
        actor_user_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return self._merchants.request_merchant_deletion(
            db, merchant, actor_user_id=actor_user_id, reason=reason
        )

    def export_customer(self, db: Session, customer: Customer) -> dict[str, Any]:
        """C-20: DSAR export — profile + orders + payments + tickets + prefs."""
        from porterchain_api.booking_models import Payment
        from porterchain_api.notification_engine.user_settings import (
            UserSettingsService,
        )
        from porterchain_api.support_engine.support_service import AdminSupportService

        orders = (
            db.query(Order)
            .filter(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
            .limit(200)
            .all()
        )
        payments = (
            db.query(Payment)
            .filter(Payment.customer_id == customer.id)
            .order_by(Payment.created_at.desc())
            .limit(200)
            .all()
        )
        tickets = AdminSupportService().list_for_customer(db, customer.id, limit=100)
        prefs: dict[str, Any] = {}
        try:
            row = UserSettingsService().get(db, user_role="customer", user_id=customer.id)
            prefs = UserSettingsService().to_dict(row, timezone_fallback="America/Toronto")
        except Exception:  # noqa: BLE001
            prefs = {}

        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "subject_type": "customer",
            "customer_id": customer.id,
            "profile": {
                "email": customer.email,
                "phone": customer.phone,
                "customer_reference": customer.customer_reference,
                "stripe_customer_id": getattr(customer, "stripe_customer_id", None),
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
            },
            "orders": [
                {
                    "order_id": o.id,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "pickup": o.pickup,
                    "dropoff": o.dropoff,
                    "amount_cents": o.amount_cents,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ],
            "payments": [
                {
                    "payment_id": p.id,
                    "status": p.status,
                    "amount_cents": p.amount_cents,
                    "currency": p.currency,
                    "stripe_payment_intent_id": p.stripe_payment_intent_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in payments
            ],
            "support_tickets": [
                {
                    "ticket_id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "order_id": t.order_id,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tickets
            ],
            "notification_preferences": prefs,
        }

    def request_customer_deletion(
        self,
        db: Session,
        customer: Customer,
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        reference = f"DSR-{uuid.uuid4().hex[:12].upper()}"
        payload = {
            "reference": reference,
            "reason": reason or "customer_portal_request",
            "customer_id": customer.id,
            "email": customer.email,
        }
        # Legal hold — Admin delete must not wipe during SLA (C-19).
        customer.privacy_status = "deletion_hold"
        customer.privacy_hold_reference = reference
        customer.privacy_hold_at = datetime.now(UTC)
        # Reviewable erasure job: automatic plan, staff approve → execute (customer_fast.privacy).
        from porterchain_api.customer_fast.privacy import open_job

        job = open_job(db, customer, reference=reference, source=reason or "customer_portal_request")
        payload["job_id"] = job.id
        emit_event(
            db,
            event_type=DomainEventType.PRIVACY_DELETE_REQUESTED,
            aggregate_type="customer",
            aggregate_id=customer.id,
            actor_type="customer",
            actor_id=customer.clerk_user_id,
            payload=payload,
        )
        db.commit()
        return {
            "reference": reference,
            "status": "received",
            "sla_days": 30,
            "message": "Deletion request logged; shipment records may be retained where required by law.",
        }

    def execute_merchant_erasure(
        self,
        db: Session,
        merchant: Any,
        *,
        actor_user_id: str,
    ) -> dict[str, Any]:
        return self._merchants.execute_merchant_erasure(db, merchant, actor_user_id=actor_user_id)


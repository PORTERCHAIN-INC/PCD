"""GDPR/CCPA/PIPEDA data subject requests (§11.1.8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_models import Customer, Order
from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantUser
from porterchain_shared.events.catalog import DomainEventType


class PrivacyService:
    def export_merchant(self, db: Session, merchant: Merchant, *, actor_user_id: str) -> dict[str, Any]:
        users = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant.id)
            .order_by(MerchantUser.created_at.asc())
            .all()
        )
        orders = (
            db.query(Order)
            .filter(Order.merchant_id == merchant.id)
            .order_by(Order.created_at.desc())
            .limit(500)
            .all()
        )
        audit = (
            db.query(MerchantAuditLog)
            .filter(MerchantAuditLog.merchant_id == merchant.id)
            .order_by(MerchantAuditLog.created_at.desc())
            .limit(200)
            .all()
        )
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "subject_type": "merchant",
            "merchant_id": merchant.id,
            "requested_by": actor_user_id,
            "profile": {
                "company_name": merchant.company_name,
                "legal_name": merchant.legal_name,
                "email": merchant.email,
                "phone": merchant.phone,
                "billing_address": merchant.billing_address,
                "status": merchant.status,
                "created_at": merchant.created_at.isoformat() if merchant.created_at else None,
            },
            "team": [
                {
                    "user_id": u.id,
                    "email": u.email,
                    "role": u.role,
                    "clerk_user_id": u.clerk_user_id,
                    "is_active": u.is_active,
                }
                for u in users
            ],
            "orders_summary": [
                {
                    "order_id": o.id,
                    "order_number": o.order_number,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in orders
            ],
            "audit_logs": [
                {
                    "action": row.action,
                    "resource_type": row.resource_type,
                    "resource_id": row.resource_id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in audit
            ],
            "retention_note": "Billing and shipment records may be retained per legal obligation after erasure request.",
        }

    def request_merchant_deletion(
        self,
        db: Session,
        merchant: Merchant,
        *,
        actor_user_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        reference = f"DSR-{uuid.uuid4().hex[:12].upper()}"
        payload = {
            "reference": reference,
            "reason": reason or "merchant_portal_request",
            "requested_by": actor_user_id,
        }
        db.add(
            MerchantAuditLog(
                merchant_id=merchant.id,
                actor_user_id=actor_user_id,
                action="privacy.delete_requested",
                resource_type="merchant",
                resource_id=merchant.id,
                payload=payload,
            )
        )
        emit_event(
            db,
            event_type=DomainEventType.PRIVACY_DELETE_REQUESTED,
            aggregate_type="merchant",
            aggregate_id=merchant.id,
            actor_type="merchant_user",
            actor_id=actor_user_id,
            payload=payload,
        )
        db.commit()
        return {
            "reference": reference,
            "status": "received",
            "sla_days": 30,
            "message": "Deletion request logged; ops will confirm identity and legal holds before erasure.",
        }

    def export_customer(self, db: Session, customer: Customer) -> dict[str, Any]:
        """C-20: DSAR export — profile + orders + payments + tickets + prefs."""
        from porterchain_api.admin_models import SupportTicket
        from porterchain_api.models import Payment
        from porterchain_api.notification_engine.user_settings import UserSettingsService

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
        tickets = (
            db.query(SupportTicket)
            .filter(SupportTicket.customer_id == customer.id)
            .order_by(SupportTicket.created_at.desc())
            .limit(100)
            .all()
        )
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

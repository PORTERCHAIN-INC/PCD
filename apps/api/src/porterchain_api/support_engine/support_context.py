"""Order context, SLA, and ticket row enrichment for support."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Claim, Driver, SupportTicket, SystemConfig
from porterchain_api.booking_models import Booking, Customer, Invoice, Order, Payment
from porterchain_api.domain.support import ticket_number
from porterchain_api.merchant_engine.lookups import get_merchant
from porterchain_api.platform.admin_audit import log_admin_audit
from porterchain_api.platform.invoice_status import invoice_status as merchant_invoice_status
from porterchain_api.support_engine.support_helpers import (
    DEFAULT_SLA,
    SupportActor,
    normalize_status,
    ticket_data,
)


class SupportContextMixin:
    def _now(self) -> datetime:
        return datetime.now(UTC)

    def _sla_config(self, db: Session) -> dict[str, Any]:
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_sla").first()
        if row and row.value:
            return {**DEFAULT_SLA, **row.value}
        return dict(DEFAULT_SLA)

    def set_sla_config(self, db: Session, ctx: SupportActor, value: dict[str, Any]) -> dict[str, Any]:
        merged = {**self._sla_config(db), **value}
        row = db.query(SystemConfig).filter(SystemConfig.key == "support_sla").first()
        if not row:
            row = SystemConfig(key="support_sla", value=merged)
            db.add(row)
        else:
            row.value = merged
        log_admin_audit(db, ctx, action="support.sla.update", resource_type="system_config", resource_id="support_sla")
        db.commit()
        return merged

    def _order_context(self, db: Session, order_id: str | None) -> dict[str, Any]:
        if not order_id:
            return {}
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {}
        merchant = get_merchant(db, order.merchant_id)
        customer = (
            db.query(Customer).filter(Customer.id == order.customer_id).first()
            if order.customer_id
            else None
        )
        driver = (
            db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            if order.assigned_driver_id
            else None
        )
        booking = db.query(Booking).filter(Booking.order_id == order.id).first()
        invoice = db.query(Invoice).filter(Invoice.order_id == order.id).order_by(Invoice.created_at.desc()).first()
        payment = db.query(Payment).filter(Payment.order_id == order.id).order_by(Payment.created_at.desc()).first()
        claims = db.query(Claim).filter(Claim.order_id == order.id).all()
        invoice_status = (
            merchant_invoice_status(
                invoice,
                order,
                payment,
                terms=order.payment_terms if order else None,
                now=self._now().replace(tzinfo=None),
            )
            if invoice
            else None
        )
        return {
            "order": order,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "order_state": order.state,
            "amount_cents": order.amount_cents,
            "merchant_id": order.merchant_id,
            "merchant_name": merchant.company_name if merchant else None,
            "customer_id": order.customer_id,
            "customer_email": customer.email if customer else None,
            "customer_phone": customer.phone if customer else None,
            "driver_id": order.assigned_driver_id,
            "driver_name": driver.full_name if driver else None,
            "booking_id": booking.id if booking else None,
            "booking_number": booking.booking_number if booking else None,
            "invoice": {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "amount_cents": invoice.amount_cents,
                "status": invoice_status,
                "pdf_url": invoice.pdf_url,
            }
            if invoice
            else None,
            "payment": {
                "payment_id": payment.id,
                "status": payment.status,
                "amount_cents": payment.amount_cents,
                "stripe_payment_intent_id": payment.stripe_payment_intent_id,
                "receipt_url": payment.receipt_url,
            }
            if payment
            else None,
            "claims": [
                {"id": c.id, "claim_type": c.claim_type, "status": c.status}
                for c in claims
            ],
        }

    def _sla_status(self, db: Session, ticket: SupportTicket) -> str:
        data = ticket_data(ticket)
        if data.get("sla_paused"):
            return "paused"
        cfg = self._sla_config(db)
        created = ticket.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_h = (self._now() - created).total_seconds() / 3600
        first_at = data.get("first_response_at")
        resolution_at = data.get("resolved_at")
        if resolution_at:
            return "met"
        if age_h > cfg["resolution_hours"]:
            return "breached"
        if age_h > cfg["resolution_hours"] * 0.75:
            return "at_risk"
        if not first_at and age_h > cfg["first_response_hours"]:
            return "breached"
        if not first_at and age_h > cfg["first_response_hours"] * 0.75:
            return "at_risk"
        return "ok"

    def _agent_name(self, db: Session, user_id: str | None) -> str | None:
        if not user_id:
            return None
        user = db.query(AdminUser).filter(AdminUser.id == user_id).first()
        return user.name or user.email if user else None

    def _row(self, db: Session, ticket: SupportTicket) -> dict[str, Any]:
        ctx = self._order_context(db, ticket.order_id)
        customer = (
            db.query(Customer).filter(Customer.id == ticket.customer_id).first()
            if ticket.customer_id
            else None
        )
        merchant = get_merchant(db, ticket.merchant_id)
        driver = (
            db.query(Driver).filter(Driver.id == ticket.driver_id).first()
            if ticket.driver_id
            else None
        )
        display_status = normalize_status(ticket.status)
        return {
            "id": ticket.id,
            "ticket_number": ticket_number(ticket.id),
            "subject": ticket.subject,
            "category": ticket.category or "general_inquiry",
            "priority": ticket.priority,
            "status": ticket.status,
            "display_status": display_status,
            "customer_id": ticket.customer_id or ctx.get("customer_id"),
            "customer_email": customer.email if customer else ctx.get("customer_email"),
            "merchant_id": ticket.merchant_id or ctx.get("merchant_id"),
            "merchant_name": merchant.company_name if merchant else ctx.get("merchant_name"),
            "driver_id": ticket.driver_id or ctx.get("driver_id"),
            "driver_name": driver.full_name if driver else ctx.get("driver_name"),
            "order_id": ticket.order_id,
            "order_number": ctx.get("order_number"),
            "tracking_number": ctx.get("tracking_number"),
            "booking_id": ctx.get("booking_id"),
            "booking_number": ctx.get("booking_number"),
            "assigned_agent_id": ticket.assigned_to,
            "assigned_agent": self._agent_name(db, ticket.assigned_to),
            "sla_status": self._sla_status(db, ticket),
            "description": ticket.description,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }

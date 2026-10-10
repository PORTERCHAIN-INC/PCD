"""Send AR invoice reminders to the merchant's primary AP contact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from porterchain_shared.events.catalog import DomainEventType
from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.invoice_service import InvoiceService
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.merchant_models import Merchant, MerchantAuditLog


def _billing_contacts(merchant: Merchant) -> list[dict[str, Any]]:
    settings = (merchant.profile or {}).get("settings") if isinstance(merchant.profile, dict) else {}
    return list((settings or {}).get("billing_contacts") or [])


def primary_billing_email(merchant: Merchant) -> str | None:
    contacts = _billing_contacts(merchant)
    primary = next((c for c in contacts if c.get("is_primary") and c.get("email")), None)
    if primary:
        email = str(primary.get("email") or "").strip()
        if email:
            return email
    for contact in contacts:
        email = str(contact.get("email") or "").strip()
        if email:
            return email
    return (merchant.email or "").strip() or None


@dataclass(frozen=True)
class ApContact:
    """Who collections actually phones about an unpaid invoice (BL).

    Distinct from ``primary_billing_email``: that answers "where does the reminder
    email go", which needs an email. Chasing a payment needs a person and a
    number, and an AP contact may have a phone but no mailbox.
    """

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    is_primary: bool = False
    #: ``billing_contact`` when a named AP contact exists, else ``company``.
    source: str = "company"

    @property
    def is_named(self) -> bool:
        return bool(self.name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "is_primary": self.is_primary,
            "source": self.source,
        }


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def primary_ap_contact(merchant: Merchant | None) -> ApContact:
    """The primary AP contact, else any AP contact, else the company's own details."""
    if merchant is None:
        return ApContact()

    contacts = _billing_contacts(merchant)
    chosen = next((c for c in contacts if c.get("is_primary")), None) or next(iter(contacts), None)
    if chosen:
        return ApContact(
            name=_clean(chosen.get("name")),
            email=_clean(chosen.get("email")),
            phone=_clean(chosen.get("phone")),
            role=_clean(chosen.get("role")) or "billing",
            is_primary=bool(chosen.get("is_primary")),
            source="billing_contact",
        )

    # No AP contact on file — the company record is all collections has to go on.
    return ApContact(
        name=_clean(merchant.company_name),
        email=_clean(merchant.email),
        phone=_clean(merchant.phone),
        source="company",
    )


def remind_invoice(
    db: Session,
    invoice: Invoice,
    merchant: Merchant,
    *,
    actor_type: str,
    actor_id: str | None,
) -> dict[str, Any]:
    order = db.query(Order).filter(Order.id == invoice.order_id).first() if invoice.order_id else None
    owner = order.merchant_id if order is not None else invoice.merchant_id
    if not owner or owner != merchant.id:
        raise LookupError("invoice_not_found")
    to_email = primary_billing_email(merchant)
    if not to_email:
        raise ValueError("billing_contact_missing")
    payload = InvoiceService()._invoice_event_payload(db, order, invoice)
    payload["email"] = to_email
    payload["merchant_email"] = to_email
    payload["reminder"] = True
    # Portal Pay now deep-link (Stripe Checkout starts from the invoice page).
    from porterchain_api.config import get_settings

    portal = (get_settings().merchant_portal_url or "").rstrip("/")
    pay_url = f"{portal}/billing/invoices/{invoice.id}" if portal else None
    if pay_url:
        payload["pay_url"] = pay_url
        # Prefer Pay CTA over receipt when chasing AR.
        if not payload.get("receipt_url"):
            payload["receipt_url"] = pay_url
    emit_event(
        db,
        event_type=DomainEventType.MERCHANT_BILLED,
        aggregate_type="invoice",
        aggregate_id=invoice.id,
        correlation_id=order.id if order is not None else invoice.id,
        actor_type=actor_type,
        actor_id=actor_id,
        payload=payload,
        publish=False,
    )
    try:
        from porterchain_api.notification_engine.event_router import handle_domain_event

        handle_domain_event(
            {
                "event_type": DomainEventType.MERCHANT_BILLED,
                "aggregate_type": "invoice",
                "aggregate_id": invoice.id,
                "correlation_id": order.id if order is not None else invoice.id,
                "payload": payload,
            }
        )
    except Exception:
        pass
    invoice.last_reminded_at = datetime.now(UTC)
    db.add(
        MerchantAuditLog(
            merchant_id=merchant.id,
            actor_user_id=actor_id,
            action="invoice.reminded",
            resource_type="invoice",
            resource_id=invoice.id,
            payload={
                "email": to_email,
                "invoice_number": invoice.invoice_number,
                "pay_url": pay_url,
            },
        )
    )
    db.commit()
    db.refresh(invoice)
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "email": to_email,
        "pay_url": pay_url,
        "last_reminded_at": invoice.last_reminded_at.isoformat() if invoice.last_reminded_at else None,
    }

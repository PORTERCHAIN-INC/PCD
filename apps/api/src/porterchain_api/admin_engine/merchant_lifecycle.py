"""Admin merchant close / convert-to-customer — never hard-delete live AR or trucks."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_models import Customer
from porterchain_api.domain.crm_states import CompanyMerchantStatus
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.offboard import (
    operational_order_count,
    outstanding_cents,
)
from porterchain_api.merchant_models import Merchant, MerchantUser


def assert_can_offboard(
    db: Session,
    merchant: Merchant,
    *,
    allow_ar: bool = False,
) -> None:
    if merchant.status == MerchantStatus.CLOSED.value:
        raise ValueError("merchant_already_closed")
    live = operational_order_count(db, merchant.id)
    if live:
        raise ValueError("close_blocked_live_orders")
    if not allow_ar and outstanding_cents(db, merchant) > 0:
        raise ValueError("close_blocked_outstanding_ar")


def deactivate_access(db: Session, merchant: Merchant) -> None:
    from porterchain_api.merchant_engine.lifecycle import (
        deactivate_access as persist_deactivate,
    )

    persist_deactivate(db, merchant)


def mark_crm_churned(db: Session, merchant_id: str) -> None:
    from porterchain_api.collaboration_engine.crm_service import CrmSalesService

    CrmSalesService().set_merchant_status(db, merchant_id, CompanyMerchantStatus.CHURNED.value)


def write_off_outstanding(db: Session, ctx: AdminContext, merchant: Merchant) -> int:
    from porterchain_api.billing_engine.credit_notes import record_convert_write_off

    amount = outstanding_cents(db, merchant)
    if amount <= 0:
        return 0
    record_convert_write_off(
        db, merchant_id=merchant.id, amount_cents=amount, actor_id=ctx.user.id
    )
    return amount


def apply_closed(
    db: Session,
    ctx: AdminContext,
    merchant: Merchant,
    *,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> Merchant:
    from porterchain_api.merchant_engine.lifecycle import apply_closed as persist_closed

    persist_closed(db, merchant, reason=reason, actor_id=ctx.user.id, extra=extra)
    mark_crm_churned(db, merchant.id)
    return merchant


def ensure_retail_customer(
    db: Session,
    *,
    email: str,
    phone: str | None,
    full_name: str | None = None,
) -> Customer:
    from porterchain_api.booking_engine.customer_service import CustomerService

    return CustomerService().ensure_from_email(
        db, email=email, phone=phone, full_name=full_name
    )


def owner_email(db: Session, merchant: Merchant) -> str:
    owner = (
        db.query(MerchantUser)
        .filter(
            MerchantUser.merchant_id == merchant.id,
            MerchantUser.role == MerchantRole.OWNER.value,
        )
        .order_by(MerchantUser.created_at.asc())
        .first()
    )
    return (owner.email if owner else None) or merchant.email or ""


def require_billing_cycle(billing_cycle: str) -> str:
    from porterchain_api.billing_engine.merchant_service import BILLING_CYCLES

    cycle = billing_cycle.upper().strip()
    if cycle not in BILLING_CYCLES:
        raise ValueError("invalid_billing_cycle")
    return cycle


_APPROVE_FROM = frozenset({MerchantStatus.PENDING.value, MerchantStatus.ONBOARDING.value})


def approve_merchant(svc: Any, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
    from datetime import UTC, datetime

    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.collaboration_engine.crm_service import CrmSalesService
    from porterchain_api.domain.crm_states import CompanyMerchantStatus
    from porterchain_api.merchant_engine.lifecycle import set_status

    merchant = svc._get_or_raise(db, merchant_id)
    if merchant.status not in _APPROVE_FROM:
        raise ValueError("approve_requires_pending_or_onboarding")
    set_status(merchant, MerchantStatus.ACTIVE.value, activated_at=datetime.now(UTC))
    CrmSalesService().set_merchant_status(
        db, merchant_id, CompanyMerchantStatus.ACTIVE_MERCHANT.value
    )
    svc._audit(db, ctx, "merchant.approved", "merchant", merchant_id, {})
    emit_event(
        db,
        event_type=E.MERCHANT_APPROVED,
        aggregate_type="merchant",
        aggregate_id=merchant_id,
        actor_type="admin",
        actor_id=ctx.user.id,
        payload={
            "merchant_id": merchant_id,
            "company_name": merchant.company_name,
            "merchant_email": merchant.email,
        },
    )
    return merchant


def suspend_merchant(svc: Any, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.merchant_engine.lifecycle import set_status

    merchant = svc._get_or_raise(db, merchant_id)
    if merchant.status == MerchantStatus.CLOSED.value:
        raise ValueError("cannot_suspend_closed")
    if merchant.status == MerchantStatus.SUSPENDED.value:
        raise ValueError("already_suspended")
    if merchant.status != MerchantStatus.ACTIVE.value:
        raise ValueError("suspend_requires_active")
    set_status(merchant, MerchantStatus.SUSPENDED.value)
    svc._audit(db, ctx, "merchant.suspended", "merchant", merchant_id, {})
    emit_event(
        db,
        event_type=E.MERCHANT_SUSPENDED,
        aggregate_type="merchant",
        aggregate_id=merchant_id,
        actor_type="admin",
        actor_id=ctx.user.id,
        payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
    )
    return merchant


def unsuspend_merchant(svc: Any, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
    from datetime import UTC, datetime

    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.collaboration_engine.crm_service import CrmSalesService
    from porterchain_api.domain.crm_states import CompanyMerchantStatus
    from porterchain_api.merchant_engine.lifecycle import set_status

    merchant = svc._get_or_raise(db, merchant_id)
    if merchant.status != MerchantStatus.SUSPENDED.value:
        raise ValueError("unsuspend_requires_suspended")
    set_status(merchant, MerchantStatus.ACTIVE.value, activated_at=datetime.now(UTC))
    CrmSalesService().set_merchant_status(
        db, merchant_id, CompanyMerchantStatus.ACTIVE_MERCHANT.value
    )
    svc._audit(db, ctx, "merchant.unsuspended", "merchant", merchant_id, {})
    emit_event(
        db,
        event_type=E.MERCHANT_UNSUSPENDED,
        aggregate_type="merchant",
        aggregate_id=merchant_id,
        actor_type="admin",
        actor_id=ctx.user.id,
        payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
    )
    return merchant


def reopen_merchant(svc: Any, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
    """CLOSED → PENDING. Does not auto-activate seats; operator must Approve again."""
    from datetime import UTC, datetime

    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.collaboration_engine.crm_service import CrmSalesService
    from porterchain_api.domain.crm_states import CompanyMerchantStatus
    from porterchain_api.merchant_engine.lifecycle import merge_profile, set_status

    merchant = svc._get_or_raise(db, merchant_id)
    if merchant.status != MerchantStatus.CLOSED.value:
        raise ValueError("reopen_requires_closed")
    prior = dict((merchant.profile or {}).get("closed") or {})
    set_status(merchant, MerchantStatus.PENDING.value)
    merge_profile(
        merchant,
        {
            "reopened": {
                "at": datetime.now(UTC).isoformat(),
                "actor_id": ctx.user.id,
                "prior_close_reason": prior.get("reason"),
            }
        },
    )
    CrmSalesService().set_merchant_status(db, merchant_id, CompanyMerchantStatus.PROSPECT.value)
    svc._audit(
        db,
        ctx,
        "merchant.reopened",
        "merchant",
        merchant_id,
        {"prior_close_reason": prior.get("reason")},
    )
    emit_event(
        db,
        event_type=E.MERCHANT_REOPENED,
        aggregate_type="merchant",
        aggregate_id=merchant_id,
        actor_type="admin",
        actor_id=ctx.user.id,
        payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
    )
    return merchant


def close_merchant(svc: Any, db: Session, ctx: AdminContext, merchant_id: str, *, reason: str) -> Merchant:
    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event

    reason_text = (reason or "").strip()
    if not reason_text:
        raise ValueError("reason_required")
    merchant = svc._get_or_raise(db, merchant_id)
    assert_can_offboard(db, merchant, allow_ar=False)
    apply_closed(db, ctx, merchant, reason=reason_text)
    svc._audit(
        db,
        ctx,
        "merchant.closed",
        "merchant",
        merchant_id,
        {"reason": reason_text, "company_name": merchant.company_name},
    )
    emit_event(
        db,
        event_type=E.MERCHANT_CLOSED,
        aggregate_type="merchant",
        aggregate_id=merchant_id,
        actor_type="admin",
        actor_id=ctx.user.id,
        payload={
            "merchant_id": merchant_id,
            "company_name": merchant.company_name,
            "reason": reason_text,
            "reason_line": f" Reason: {reason_text}." if reason_text else "",
            "merchant_email": merchant.email,
            "email": merchant.email,
        },
    )
    return merchant


def convert_to_customer(
    svc: Any,
    db: Session,
    ctx: AdminContext,
    merchant_id: str,
    *,
    owner_email_value: str | None = None,
    write_off_ar: bool = False,
) -> dict[str, Any]:
    from porterchain_api.admin_engine import events as E
    from porterchain_api.booking_engine._core import emit_event

    merchant = svc._get_or_raise(db, merchant_id)
    existing = (merchant.profile or {}).get("converted_customer_id")
    if merchant.status == MerchantStatus.CLOSED.value and existing:
        return {
            "customer_id": existing,
            "merchant_id": merchant.id,
            "status": merchant.status,
            "merchant": merchant,
            "customer": None,
            "skip_commit": True,
        }
    assert_can_offboard(db, merchant, allow_ar=write_off_ar)
    written_off = 0
    if write_off_ar:
        written_off = write_off_outstanding(db, ctx, merchant)
    elif outstanding_cents(db, merchant) > 0:
        raise ValueError("close_blocked_outstanding_ar")
    email = (owner_email_value or "").strip() or owner_email(db, merchant)
    customer = ensure_retail_customer(db, email=email, phone=merchant.phone)
    apply_closed(
        db,
        ctx,
        merchant,
        reason="converted_to_customer",
        extra={"customer_id": customer.id, "ar_written_off_cents": written_off},
    )
    profile = dict(merchant.profile or {})
    profile["converted_customer_id"] = customer.id
    merchant.profile = profile
    svc._audit(
        db,
        ctx,
        "merchant.converted_to_customer",
        "merchant",
        merchant_id,
        {
            "customer_id": customer.id,
            "owner_email": email,
            "ar_written_off_cents": written_off,
        },
    )
    emit_event(
        db,
        event_type=E.MERCHANT_CLOSED,
        aggregate_type="merchant",
        aggregate_id=merchant_id,
        actor_type="admin",
        actor_id=ctx.user.id,
        payload={
            "merchant_id": merchant_id,
            "customer_id": customer.id,
            "company_name": merchant.company_name,
            "converted": True,
            "ar_written_off_cents": written_off,
            "reason_line": " Account converted to customer.",
            "merchant_email": merchant.email,
            "email": merchant.email,
        },
    )
    return {
        "customer_id": customer.id,
        "merchant_id": merchant.id,
        "status": merchant.status,
        "ar_written_off_cents": written_off,
        "merchant": merchant,
        "customer": customer,
        "skip_commit": False,
    }


def complete_onboarding(
    svc: Any,
    db: Session,
    ctx: AdminContext,
    settings: Any,
    merchant_id: str,
    *,
    email: str | None = None,
) -> tuple[Merchant, str | None]:
    from datetime import UTC, datetime

    from porterchain_api.admin_engine import events as E
    from porterchain_api.admin_engine.clerk_directory_service import _clerk_linked
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.merchant_engine.lifecycle import set_status
    from porterchain_api.merchant_engine.lookups import seats_for_merchant
    from porterchain_api.merchant_engine.team_service import activate_seats

    merchant = svc._get_or_raise(db, merchant_id)
    target = (email or merchant.email or "").lower().strip()
    if not target:
        raise ValueError("merchant_owner_email_required")

    users = seats_for_merchant(db, merchant_id)
    owner = next((u for u in users if u.role == MerchantRole.OWNER.value), None)
    needs_seat = not owner or not _clerk_linked(owner.clerk_user_id)
    if needs_seat:
        svc.invite_owner(db, ctx, settings, merchant_id, email=owner.email if owner else target)

    users = seats_for_merchant(db, merchant_id)
    owner = next((u for u in users if u.role == MerchantRole.OWNER.value), None)
    owner_linked = bool(owner and _clerk_linked(owner.clerk_user_id))
    if not owner_linked:
        if merchant.status != MerchantStatus.ACTIVE.value:
            set_status(merchant, MerchantStatus.ONBOARDING.value)
        activate_seats(users)
        svc._audit(
            db,
            ctx,
            "merchant.onboarding_seat_reserved",
            "merchant",
            merchant_id,
            {"email": target, "owner_linked": False},
        )
        return merchant, "owner_not_clerk_linked"

    activate_seats(users)

    if merchant.status != MerchantStatus.ACTIVE.value:
        set_status(merchant, MerchantStatus.ACTIVE.value, activated_at=datetime.now(UTC))
        svc._audit(db, ctx, "merchant.approved", "merchant", merchant_id, {"via": "complete_onboarding"})
        emit_event(
            db,
            event_type=E.MERCHANT_APPROVED,
            aggregate_type="merchant",
            aggregate_id=merchant_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
        )

    svc._audit(
        db,
        ctx,
        "merchant.onboarding_completed",
        "merchant",
        merchant_id,
        {"email": target},
    )
    return merchant, None


def ops_invoices(db: Session, merchant: Merchant):
    from datetime import date as date_cls

    from porterchain_api.billing_engine.merchant_service import (
        invoice_status,
        invoice_total_cents,
    )
    from porterchain_api.booking_models import Invoice, Order, Payment
    from porterchain_api.schemas_crm import InvoiceOut

    rows = (
        db.query(Invoice, Order)  # outer: cycle invoices have no order
        .outerjoin(Order, Invoice.order_id == Order.id)
        .filter(or_(Order.merchant_id == merchant.id, Invoice.merchant_id == merchant.id))
        .order_by(Invoice.created_at.desc())
        .limit(200)
        .all()
    )
    out: list[InvoiceOut] = []
    for inv, order in rows:
        payment = (
            db.query(Payment).filter(Payment.order_id == order.id).order_by(Payment.created_at.desc()).first()
            if order is not None
            else None
        )
        oterms = order.payment_terms if order is not None else None
        status = invoice_status(inv, order, payment, terms=merchant.payment_terms or oterms)
        due = inv.due_at.date() if inv.due_at else None
        paid_at = payment.created_at if payment and payment.status == "SUCCEEDED" else None
        total = invoice_total_cents(inv)
        pretax = int(inv.amount_cents or 0) - int(inv.tax_cents or 0)
        out.append(
            InvoiceOut(
                id=inv.id,
                invoice_number=inv.invoice_number,
                company_id=None,
                deal_id=None,
                contract_id=None,
                status=status,
                amount_cents=pretax if inv.tax_cents else inv.amount_cents,
                tax_cents=inv.tax_cents,
                total_cents=total,
                currency=inv.currency,
                net_terms=merchant.payment_terms or oterms or "NET_30",
                line_items=[
                    {
                        "label": (order.order_number or order.tracking_number) if order else "Billing cycle",
                        "quantity": 1,
                        "unit_price_cents": pretax if inv.tax_cents else inv.amount_cents,
                        "amount_cents": pretax if inv.tax_cents else inv.amount_cents,
                    }
                ],
                notes=None,
                issue_date=inv.created_at.date() if inv.created_at else date_cls.today(),
                due_date=due,
                paid_at=paid_at,
                created_at=inv.created_at,
                updated_at=inv.created_at,
            )
        )
    return out

"""Merchant billing façade — credit balance, invoice totals, e-Transfer settings.

Lets admin/merchant engines read billing facts without importing billing_engine or
admin_engine directly (§3.2.9).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def finance_tax_settings(db: Session) -> tuple[str, str, bool]:
    """(tax_mode, default_province, collect_qst) from finance settings."""
    from porterchain_api.admin_engine.platform_settings import collect_qst, default_tax_province, tax_mode

    return tax_mode(db), default_tax_province(db), collect_qst(db)


def order_tax_split(db: Session, order: Any) -> Any:
    """Pre-tax / tax / gross for a merchant delivery (destination province, tax mode)."""
    from porterchain_api.billing_engine.tax import order_tax_split as _f

    return _f(db, order)


def charged_tax_split(db: Session, order: Any, charged_cents: int) -> Any:
    """Tax contained in an amount already charged (Stripe)."""
    from porterchain_api.billing_engine.tax import charged_tax_split as _f

    return _f(db, order, charged_cents)


def merchant_credit_cents(db: Session, merchant_id: str) -> int:
    from porterchain_api.billing_engine.merchant_credit import merchant_credit_cents as _f

    return _f(db, merchant_id)


def merchant_credit_total_cents(db: Session) -> int:
    from porterchain_api.billing_engine.merchant_credit import merchant_credit_total_cents as _f

    return _f(db)


def apply_available_credit(db: Session, invoice: Any, *, actor: str | None) -> int:
    """Use a merchant's unapplied overpayment credit against ``invoice``."""
    from datetime import UTC, datetime

    from porterchain_api.billing_engine.merchant_credit import CREDIT_APPLIED, merchant_credit_cents
    from porterchain_api.billing_engine.merchant_service import invoice_total_cents
    from porterchain_api.billing_engine.models import BillingLedgerEntry

    if not invoice.merchant_id:
        return 0
    available = merchant_credit_cents(db, invoice.merchant_id)
    outstanding = max(0, invoice_total_cents(invoice) - int(invoice.amount_paid_cents or 0))
    use = min(available, outstanding)
    if use <= 0:
        return 0
    invoice.amount_paid_cents = int(invoice.amount_paid_cents or 0) + use
    db.add(
        BillingLedgerEntry(
            kind=CREDIT_APPLIED,
            invoice_id=invoice.id,
            merchant_id=invoice.merchant_id,
            amount_cents=use,
            status="applied",
            metadata_json={"invoice_number": invoice.invoice_number, "actor": actor},
        )
    )
    if int(invoice.amount_paid_cents) >= invoice_total_cents(invoice):
        invoice.paid_at = datetime.now(UTC)
    db.flush()
    return use


def etransfer_recipient_email(db: Session) -> str:
    from porterchain_api.admin_engine.platform_settings import etransfer_recipient_email as _f

    return _f(db)


def record_offline_payment(db: Session, ctx: Any, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
    """Record an Interac/cheque/wire payment (partial and over supported)."""
    from porterchain_api.admin_engine.merchant_ar_service import MerchantArService

    return MerchantArService().record_payment(db, ctx, invoice_id, **kwargs)


def merchant_display_name(db: Session, merchant_id: str | None) -> str | None:
    if not merchant_id:
        return None
    from porterchain_api.merchant_engine.lookups import get_merchant

    m = get_merchant(db, merchant_id)
    return (m.company_name or m.legal_name) if m else None

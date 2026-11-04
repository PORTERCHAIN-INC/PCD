"""AP pack copy — glossary, remittance, English billing errors."""

from __future__ import annotations

from typing import Any

from porterchain_api.merchant_engine.invoice_reminder import primary_billing_email
from porterchain_api.merchant_models import Merchant

PAYEE_LEGAL_NAME = "Porterchain Inc."

BILLING_GLOSSARY: list[dict[str, str]] = [
    {
        "term": "Outstanding",
        "meaning": "What you owe now: open invoices plus uninvoiced orders, minus credit notes.",
    },
    {
        "term": "Invoiced outstanding",
        "meaning": "Open invoices that are not paid yet.",
    },
    {
        "term": "Uninvoiced orders",
        "meaning": "Deliveries that are billed on your cycle but do not have an invoice number yet.",
    },
    {
        "term": "Credits applied",
        "meaning": "Credit notes that reduce what you owe. They are already subtracted from Outstanding.",
    },
    {
        "term": "Headroom",
        "meaning": "Credit limit minus outstanding. When headroom is $0, new bookings are refused.",
    },
    {
        "term": "Net terms",
        "meaning": "Days after the invoice date when payment is due (for example Net 14 or Net 30).",
    },
    {
        "term": "Tax",
        "meaning": "Sales tax shown on an invoice only when it was charged on that invoice. Invoices with no tax line carry no sales tax.",
    },
    {
        "term": "Contract pricing",
        "meaning": "Your negotiated rate card (FSA or distance) and any monthly commitment. Checkout and portal quotes use the same engine.",
    },
    {
        "term": "Channel",
        "meaning": "Where the delivery was booked: Shopify, portal, or API. Reports break spend down by channel.",
    },
]

_ERRORS = {
    "invoice_not_found": "That invoice was not found.",
    "pdf_not_available": "We could not prepare a PDF for this invoice. Try again or contact support.",
    "billing_contact_missing": "Add a billing email in Settings so we can send reminders.",
    "nothing_outstanding": "Nothing is due on this account right now.",
    "invoice_not_payable": "This invoice cannot be paid (already paid or void).",
}


def billing_error_message(code: str) -> str:
    raw = (code or "").strip()
    return _ERRORS.get(raw, raw or _ERRORS["invoice_not_found"])


def remittance_pack(
    merchant: Merchant,
    *,
    outstanding_cents: int,
    open_invoice_numbers: list[str],
    net_terms_days: int,
    credits_applied_cents: int,
    open_references: list[str] | None = None,
    etransfer_email: str | None = None,
) -> dict[str, Any]:
    numbers = [n for n in open_invoice_numbers if n]
    refs = [r for r in (open_references or []) if r]
    memo = ", ".join((refs or numbers)[:8]) if (refs or numbers) else "invoice numbers from Billing"
    return {
        "method": "interac",
        "etransfer_email": etransfer_email,
        "open_references": refs[:20],
        "payee": PAYEE_LEGAL_NAME,
        "advice_email": primary_billing_email(merchant),
        "memo": memo,
        "open_invoice_numbers": numbers[:20],
        "outstanding_cents": outstanding_cents,
        "credits_applied_cents": credits_applied_cents,
        "net_terms_days": net_terms_days,
        "instructions": (
            f"Pay by Interac e-Transfer to {etransfer_email or 'the billing email on your invoice'}. "
            f"Put {memo} in the e-Transfer message so we can match it. "
            "Partial payments are applied; any overpayment becomes credit on your next invoice."
        ),
    }


def _etransfer_email(db) -> str:
    from porterchain_api.platform.merchant_billing import etransfer_recipient_email

    return etransfer_recipient_email(db)


def _credit_balance(db, merchant_id: str) -> int:
    """Overpayment credit carried to the next invoice."""
    from porterchain_api.platform.merchant_billing import merchant_credit_cents

    return merchant_credit_cents(db, merchant_id)


def overview_payload(svc, db, ctx, *, billing_cycles: tuple[str, ...]) -> dict[str, Any]:
    merchant = ctx.merchant
    invoices = svc._merchant_invoices(db, ctx)
    enriched = svc.list_invoices_enriched(db, ctx)
    payments = svc.list_payments(db, ctx)
    credit_notes = svc.list_credit_notes(db, ctx)
    tax = svc.tax_summary(db, ctx)
    contract = svc.contract_pricing(db, ctx)
    ar = svc._ar(db, ctx)
    outstanding_invoices = ar.invoiced_cents
    uninvoiced = ar.uninvoiced_cents
    credit_notes_cents = ar.credits_cents
    outstanding_balance = ar.outstanding_cents
    summary = svc.statement_summary(db, ctx)
    limit = merchant.credit_limit_cents
    available = None
    if limit is not None and limit > 0:
        available = max(0, int(limit) - int(outstanding_balance))
    open_numbers = [
        str(r.get("invoice_number") or "")
        for r in enriched
        if r.get("outstanding_cents", 0) > 0 and r.get("status") not in ("paid", "void", "cancelled", "credited")
    ]
    from porterchain_api.admin_engine.merchant_ar_cycles import is_weekly_billed_merchant
    from porterchain_api.billing_engine.weekly_billing import TERMS_LABEL

    weekly = is_weekly_billed_merchant(merchant)
    from porterchain_api.config import get_settings
    from porterchain_api.merchant_engine.shopify_billing import is_shopify_billed

    # Review 139170: Shopify-installed stores pay through their Shopify bill, not Interac.
    shopify_billed = is_shopify_billed(db, get_settings(), merchant.id)
    hide_remittance = shopify_billed and int(outstanding_invoices or 0) <= 0
    return {
        "shopify_billed": shopify_billed,
        **summary,
        **({"billing_cycle": "WEEKLY", "billing_terms_label": TERMS_LABEL} if weekly else {}),
        "credit_limit_cents": merchant.credit_limit_cents,
        "available_credit_cents": available,
        "headroom_cents": available,
        "credits_applied_cents": credit_notes_cents,
        "credit_balance_cents": _credit_balance(db, merchant.id),
        "glossary": BILLING_GLOSSARY,
        "remittance": None
        if hide_remittance
        else remittance_pack(
            merchant,
            outstanding_cents=outstanding_balance,
            open_invoice_numbers=open_numbers,
            net_terms_days=int(summary["net_terms_days"]),
            credits_applied_cents=credit_notes_cents,
            open_references=[
                str(r.get("payment_reference") or "")
                for r in enriched
                if r.get("outstanding_cents", 0) > 0 and r.get("status") not in ("paid", "void", "cancelled", "credited")
            ],
            etransfer_email=_etransfer_email(db),
        )
        | {"gst_hst_number": _gst_hst(db)},
        "outstanding_balance_cents": outstanding_balance,
        "outstanding_invoices_cents": outstanding_invoices,
        "uninvoiced_orders_cents": uninvoiced,
        "credit_notes_cents": credit_notes_cents,
        "overdue_cents": ar.overdue_cents,
        "open_invoice_count": ar.open_invoice_count,
        "overdue_invoice_count": ar.overdue_invoice_count,
        "billing_cycles_available": list(billing_cycles),
        "invoices_due": sum(
            1 for r in enriched if r["status"] in ("sent", "overdue", "pending", "partial") and r["outstanding_cents"] > 0
        ),
        "overdue_invoices": sum(1 for r in enriched if r["status"] == "overdue"),
        "invoice_count": len(invoices),
        "payment_count": len(payments),
        "credit_notes_count": len(credit_notes),
        "tax_summary": tax,
        "contract_pricing": contract,
        "supplier_gst_hst_number": _gst_hst(db),
    }


def _gst_hst(db) -> str:
    """Our GST/HST registration (single source; '' until set in Settings > Finance)."""
    from porterchain_api.platform.tax_registration import supplier_gst_hst_number

    return supplier_gst_hst_number(db)

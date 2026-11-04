"""Merchant cycle AR helpers — period/time conversion and email field builders.

Split from ``merchant_ar_service`` (ENG-G2 ≤500 LOC); re-exported there unchanged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.platform.engine_ports.billing_engine__merchant_service import billing_period_bounds, invoice_net_total_cents
from porterchain_api.platform.engine_ports.billing_engine__models import InvoiceLine
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.domain.states import OrderState

ELIGIBLE_STATES = frozenset(
    {
        OrderState.DELIVERED.value,
        OrderState.POD_COMPLETED.value,
        # Allow recovering state-only "INVOICED" orders that never got an Invoice row.
        OrderState.INVOICED.value,
    }
)


def previous_billing_period_bounds(
    cycle: str,
    reference: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return the fully closed period immediately before the current cycle window."""
    cur_start, cur_end = billing_period_bounds(cycle, reference)
    duration = cur_end - cur_start
    return cur_start - duration, cur_start


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _naive(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _toronto_wall_to_utc(dt: datetime) -> datetime:
    from zoneinfo import ZoneInfo

    wall = dt.replace(tzinfo=None)
    return wall.replace(tzinfo=ZoneInfo("America/Toronto")).astimezone(UTC).replace(tzinfo=None)


def _end_of_day(dt: datetime) -> datetime:
    """L137: a period end picked late in the day (23:30 picker default, 23:59) means through that
    whole day, so the billing week ends at Toronto midnight."""
    from datetime import timedelta

    if dt.hour == 23 and dt.minute >= 30:
        return (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return dt


_METHOD_LABELS = {"card": ("card", "carte"), "interac": ("Interac e-Transfer", "virement Interac"),
                  "cheque": ("cheque", "chèque"), "wire": ("wire transfer", "virement bancaire"), "other": ("other", "autre")}


def _payment_email_fields(invoice: Invoice, merchant: Any, received: int, method: str) -> dict[str, Any]:
    from porterchain_api.config import get_settings

    cur = (invoice.currency or "cad").upper()
    balance = max(0, invoice_net_total_cents(invoice) - int(invoice.amount_paid_cents or 0))
    en, fr = _METHOD_LABELS.get(method, (method, method))
    portal = (get_settings().merchant_portal_url or "").rstrip("/")
    return {
        "invoice_number": invoice.invoice_number,
        "company_name": (getattr(merchant, "company_name", None) or getattr(merchant, "legal_name", None) or "") if merchant else "",
        "amount_display": f"${received / 100:,.2f} {cur}",
        "balance_display": f"${balance / 100:,.2f} {cur}",
        "method_label": en,
        "method_label_fr": fr,
        "invoice_url": f"{portal}/billing/invoices/{invoice.id}" if portal else "",
    }


def interac_instructions(db: Session, invoice: Any) -> str:
    """How a merchant pays (Ravi 2026-11-03: Interac e-Transfer only, no card)."""
    from porterchain_api.admin_engine.platform_settings import etransfer_recipient_email

    ref = getattr(invoice, "payment_reference", None) or invoice.invoice_number
    return (
        f"Pay by Interac e-Transfer to {etransfer_recipient_email(db)}. "
        f"Put {ref} (invoice {invoice.invoice_number}) in the e-Transfer message.\n"
        f"Payez par virement Interac à {etransfer_recipient_email(db)}, avec {ref} dans le message."
    )


def _display_cycle(merchant: Any) -> str | None:
    from porterchain_api.admin_engine.merchant_ar_cycles import is_weekly_billed_merchant

    return "WEEKLY" if is_weekly_billed_merchant(merchant) else merchant.billing_cycle


def _cycle_email_fields(invoice: Any, line_specs: list, extras: list, start: datetime, end: datetime) -> dict[str, Any]:
    """L126: billing week (Toronto dates), one line per delivery/fee, due date, Pay now + PDF links."""
    from datetime import timedelta

    from porterchain_api.platform.engine_ports.billing_engine__weekly_billing import TORONTO
    from porterchain_api.config import get_settings

    def _loc(dt: datetime) -> datetime:
        return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(TORONTO)

    cur = (invoice.currency or "cad").upper()
    lines = [
        f"- {o.order_number}: ${(sp.gross_cents or 0) / 100:.2f} {cur}" for o, sp in line_specs
    ]
    for ex in extras:
        label = getattr(ex, "description", None) or getattr(ex, "label", None) or "Fee"
        lines.append(f"- {label}: ${(getattr(ex, 'gross_cents', 0) or 0) / 100:.2f} {cur}")
    a = _loc(start).date()
    b = (_loc(end) - timedelta(microseconds=1)).date()
    due = _loc(invoice.due_at).date() if invoice.due_at else None
    portal = (get_settings().merchant_portal_url or "").rstrip("/")
    base = f"{portal}/billing/invoices/{invoice.id}" if portal else ""
    return {
        "period_label": f"{a:%a %b %d, %Y} to {b:%a %b %d, %Y} (Toronto)",
        "due_label": f"{due:%a %b %d, %Y} (Toronto)" if due else "",
        "lines_text": "\n".join(lines),
        "order_number": f"{len(line_specs)} deliveries" if len(line_specs) != 1 else line_specs[0][0].order_number,
        "pay_url": base,
        "receipt_url": f"{base}?pdf=1" if base else "",
        "merchant_deep_link": base,
    }


def eligible_orders(db: Session, merchant_id: str, period_end: datetime) -> list[Order]:
    # Shopify-installed stores are billed through Shopify usage charges (review 139170),
    # never on an Interac invoice.
    from porterchain_api.config import get_settings
    from porterchain_api.platform.engine_ports.merchant_engine__shopify_billing import is_shopify_billed

    if is_shopify_billed(db, get_settings(), merchant_id):
        return []
    invoiced_ids = {
        row[0]
        for row in db.query(Invoice.order_id).filter(Invoice.order_id.isnot(None)).all()
    }
    invoiced_ids |= {
        row[0]
        for row in db.query(InvoiceLine.order_id).filter(InvoiceLine.order_id.isnot(None)).all()
    }
    end = _aware(period_end)  # period_start is informational: older uninvoiced work carries forward
    rows = (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant_id,
            Order.state.in_(list(ELIGIBLE_STATES)),
        )
        .order_by(Order.updated_at.asc())
        .all()
    )
    out: list[Order] = []
    for order in rows:
        if order.id in invoiced_ids:
            continue
        # Activity rule: updated_at within [start, end).
        stamp = order.updated_at or order.created_at
        if stamp is None:
            continue
        stamp_a = _aware(stamp)
        # Anything delivered before the period closes and never invoiced is billed now
        # (carried forward), so a late POD never falls through the cracks.
        if stamp_a < end:
            out.append(order)
    return out

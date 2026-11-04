"""Invoice adjustments: void, credit specific lines, or a partial credit.

Every adjustment is a numbered GST/HST credit note (ETA s.232(3), SOR/91-44 s.3).
The rules and their sources are in docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md.

- The invoice is never edited. ``invoices.credited_cents`` grows, and
  ``invoice_status`` / ``outstanding_cents`` net it out, so AR, reminders and the
  Interac matcher see the new balance.
- The tax reversed is always the tax the invoice actually charged (never re-rated):
  exact for whole lines, prorated ROUND_HALF_UP for partial credits, and the exact
  remainder on the final credit, so the credited tax never exceeds the charged tax.
- Credit above what is still owed (already paid) goes to the merchant's credit
  balance (Interac merchants) or back to the card (Stripe retail).
- Above the approval threshold a note waits as ``pending_approval`` with no number
  and no effect, until a different admin approves it.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry, CreditNote, InvoiceLine
from porterchain_api.booking_models import Customer, Invoice, Order, Payment

logger = logging.getLogger(__name__)

LEDGER_KIND = "invoice_credit_note"
LEGACY_KIND = "credit_note"
KINDS = ("void", "lines", "partial")
DEFAULT_APPROVAL_THRESHOLD_CENTS = 50_000

# Customer-facing wording per reason code. Internal notes are never shown (PIPEDA 4.5).
REASON_CODES: dict[str, str] = {
    "service_failure": "We did not meet our service standard on this delivery, so we have credited the charge.",
    "test_delivery": "This charge was for a test delivery and should not have been billed.",
    "goodwill": "A goodwill credit, with our thanks for your business.",
    "duplicate_billing": "This charge was billed more than once; we have removed the duplicate.",
    "pricing_error": "The price on the original invoice was incorrect; this credit corrects it.",
    "other": "An adjustment to your invoice.",
}
REASON_ALIASES = {"our_fault": "service_failure"}
ERROR_CODES = ("duplicate_billing", "pricing_error")  # tax charged in error: ETA s.232(1), 2 years


def normalise_reason(code: str | None) -> str:
    c = (code or "").strip().lower()
    c = REASON_ALIASES.get(c, c)
    if c not in REASON_CODES:
        raise ValueError("credit_reason_invalid")
    return c


def approval_threshold_cents(db: Session) -> int:
    from porterchain_api.platform.engine_ports.merchant_engine__config_read import config_dict

    cfg = config_dict(db, "settings_finance")
    raw = cfg.get("credit_note_approval_threshold_cents")
    try:
        val = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_APPROVAL_THRESHOLD_CENTS
    return max(0, val)


def _round(x: Decimal) -> int:
    return int(x.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# --------------------------------------------------------------------- numbering


def allocate_credit_note_number(db: Session, *, now: datetime | None = None) -> str:
    """Gap-free ``CN-YYYY-NNNNNN`` on the row-locked invoice counter (scope ``CN:YYYY``)."""
    import re

    from porterchain_api.billing_engine.models import InvoiceNumberSequence

    year = (now or datetime.now(UTC)).year
    scope = f"CN:{year}"
    row = db.execute(
        select(InvoiceNumberSequence).where(InvoiceNumberSequence.scope == scope).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        pattern = re.compile(rf"^CN-{year}-(\d{{6,}})$")
        start = 0
        for (num,) in db.query(CreditNote.credit_note_number).filter(
            CreditNote.credit_note_number.like(f"CN-{year}-%")
        ):
            m = pattern.match(num or "")
            if m:
                start = max(start, int(m.group(1)))
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        db.execute(
            pg_insert(InvoiceNumberSequence)
            .values(scope=scope, last_value=start)
            .on_conflict_do_nothing(index_elements=["scope"])
        )
        row = db.execute(
            select(InvoiceNumberSequence).where(InvoiceNumberSequence.scope == scope).with_for_update()
        ).scalar_one()
    row.last_value = int(row.last_value or 0) + 1
    db.flush()
    return f"CN-{year}-{row.last_value:06d}"


# --------------------------------------------------------------------- invoice maths


def _total(invoice: Invoice) -> int:
    from porterchain_api.billing_engine.merchant_service import invoice_total_cents

    return invoice_total_cents(invoice)


def _lines(db: Session, invoice: Invoice) -> list[InvoiceLine]:
    return (
        db.query(InvoiceLine)
        .filter(InvoiceLine.invoice_id == invoice.id)
        .order_by(InvoiceLine.created_at.asc(), InvoiceLine.id.asc())
        .all()
    )


def _lines_are_pretax(invoice: Invoice, lines: list[InvoiceLine]) -> bool:
    """Cycle invoices store pre-tax line amounts; per-order invoices store the gross."""
    pre = sum(int(ln.amount_cents or 0) for ln in lines)
    tax = sum(int(ln.tax_cents or 0) for ln in lines)
    return bool(lines) and pre + tax == int(invoice.amount_cents or 0) and tax > 0


def line_breakdown(db: Session, invoice: Invoice) -> list[dict[str, Any]]:
    """Each line as gross / tax / pre-tax, plus whether a credit note already removed it."""
    lines = _lines(db, invoice)
    pretax = _lines_are_pretax(invoice, lines)
    credited: set[str] = set()
    for note in _notes(db, invoice.id, statuses=("issued", "pending_approval")):
        for ln in note.lines_json or []:
            if ln.get("line_id"):
                credited.add(str(ln["line_id"]))
    out = []
    for ln in lines:
        amt, tax = int(ln.amount_cents or 0), int(ln.tax_cents or 0)
        gross = amt + tax if pretax else amt
        out.append(
            {
                "line_id": ln.id,
                "description": ln.description or "Delivery",
                "gross_cents": gross,
                "tax_cents": tax,
                "subtotal_cents": gross - tax,
                "credited": ln.id in credited,
            }
        )
    return out


def _notes(db: Session, invoice_id: str, *, statuses: tuple[str, ...] = ("issued",)) -> list[CreditNote]:
    return (
        db.query(CreditNote)
        .filter(CreditNote.invoice_id == invoice_id, CreditNote.status.in_(statuses), CreditNote.kind.isnot(None))
        .order_by(CreditNote.created_at.asc())
        .all()
    )


def _credited_tax(db: Session, invoice_id: str) -> int:
    return sum(int(n.tax_cents or 0) for n in _notes(db, invoice_id))


def _pending_cents(db: Session, invoice_id: str) -> int:
    return sum(int(n.amount_cents or 0) for n in _notes(db, invoice_id, statuses=("pending_approval",)))


def creditable_cents(db: Session, invoice: Invoice) -> int:
    credited = int(getattr(invoice, "credited_cents", 0) or 0)
    return max(0, _total(invoice) - credited - _pending_cents(db, invoice.id))


def _money_in(db: Session, invoice: Invoice) -> int:
    paid = int(invoice.amount_paid_cents or 0)
    if invoice.order_id:
        pay = (
            db.query(Payment)
            .filter(Payment.order_id == invoice.order_id, Payment.status.in_(("SUCCEEDED", "REFUNDED")))
            .order_by(Payment.created_at.desc())
            .first()
        )
        # Offline (Interac) receipts on order invoices are recorded on the invoice itself.
        if pay is not None and pay.stripe_payment_intent_id and not paid:
            paid = int(pay.amount_cents or 0)
    return paid


def _money_back(db: Session, invoice: Invoice) -> int:
    """Refunds / credit-balance already returned against this invoice."""
    back = sum(int(n.settlement_cents or 0) for n in _notes(db, invoice.id))
    back += sum(
        int(r.amount_cents or 0)
        for r in db.query(BillingLedgerEntry).filter(
            BillingLedgerEntry.invoice_id == invoice.id,
            BillingLedgerEntry.kind == "refund",
            BillingLedgerEntry.status == "recorded",
            or_(
                BillingLedgerEntry.idempotency_key.is_(None),
                ~BillingLedgerEntry.idempotency_key.like("cn-refund:%"),
            ),
        )
    )
    return back


def _is_stripe_retail(db: Session, invoice: Invoice) -> bool:
    if not invoice.order_id:
        return False
    order = db.get(Order, invoice.order_id)
    if order is None:
        return False
    pay = db.query(Payment).filter(Payment.order_id == order.id, Payment.stripe_payment_intent_id.isnot(None)).first()
    return bool(order.stripe_payment_intent_id or pay)


# --------------------------------------------------------------------- building a note


def _compute(
    db: Session,
    invoice: Invoice,
    *,
    kind: str,
    line_ids: list[str] | None,
    amount_cents: int | None,
) -> tuple[int, int, list[dict[str, Any]]]:
    """Return (gross, tax, lines) for the requested credit."""
    total = _total(invoice)
    room = creditable_cents(db, invoice)
    if room <= 0:
        raise ValueError("invoice_fully_credited")
    tax_total = int(invoice.tax_cents or 0)
    tax_left = max(0, tax_total - _credited_tax(db, invoice.id))

    if kind == "void":
        if _pending_cents(db, invoice.id):
            raise ValueError("credit_note_pending_approval")
        return room, tax_left, [{"description": "Full credit of the invoice (void)", "gross_cents": room, "tax_cents": tax_left}]

    if kind == "lines":
        wanted = [str(x) for x in (line_ids or []) if str(x).strip()]
        if not wanted:
            raise ValueError("credit_lines_required")
        rows = {r["line_id"]: r for r in line_breakdown(db, invoice)}
        picked = []
        for lid in dict.fromkeys(wanted):
            r = rows.get(lid)
            if r is None:
                raise LookupError("invoice_line_not_found")
            if r["credited"]:
                raise ValueError("invoice_line_already_credited")
            picked.append(r)
        gross = sum(r["gross_cents"] for r in picked)
        tax = min(sum(r["tax_cents"] for r in picked), tax_left)
        if gross > room:
            raise ValueError("credit_exceeds_invoice")
        if gross == room:
            tax = tax_left  # final credit: reverse the exact remaining tax
        return gross, tax, [
            {"line_id": r["line_id"], "description": r["description"], "gross_cents": r["gross_cents"], "tax_cents": r["tax_cents"]}
            for r in picked
        ]

    if kind == "partial":
        gross = int(amount_cents or 0)
        if gross <= 0:
            raise ValueError("credit_amount_invalid")
        if gross > room:
            raise ValueError("credit_exceeds_invoice")
        if gross == room:
            tax = tax_left
        else:
            tax = _round(Decimal(gross) * Decimal(tax_total) / Decimal(total)) if total else 0
            tax = min(tax, tax_left)
        return gross, tax, [{"description": "Partial credit", "gross_cents": gross, "tax_cents": tax}]

    raise ValueError("credit_kind_invalid")


def _recipient_name(db: Session, invoice: Invoice) -> str:
    if invoice.customer_id:
        c = db.get(Customer, invoice.customer_id)
        if c is not None:
            return (c.full_name or "").strip() or "Customer"
    if invoice.merchant_id:
        from porterchain_api.platform.engine_ports.merchant_engine__lookups import get_merchant

        m = get_merchant(db, invoice.merchant_id)
        if m is not None:
            return (m.legal_name or m.company_name or "").strip() or "Merchant"
    return "Customer"


def request_credit(
    db: Session,
    *,
    invoice_id: str,
    kind: str,
    reason_code: str,
    actor_id: str,
    internal_note: str | None = None,
    customer_message: str | None = None,
    line_ids: list[str] | None = None,
    amount_cents: int | None = None,
) -> CreditNote:
    """Create a credit note; issue it now, or park it for a second approver above the threshold."""
    kind = (kind or "").strip().lower()
    if kind not in KINDS:
        raise ValueError("credit_kind_invalid")
    code = normalise_reason(reason_code)
    note_text = (internal_note or "").strip()
    if code == "other" and not note_text:
        raise ValueError("credit_note_required_for_other")
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).with_for_update().first()
    if invoice is None:
        raise LookupError("invoice_not_found")
    gross, tax, lines = _compute(db, invoice, kind=kind, line_ids=line_ids, amount_cents=amount_cents)
    public = (customer_message or "").strip()[:500] or REASON_CODES[code]
    issued = _aware(invoice.issued_at) or _aware(invoice.created_at)
    note = CreditNote(
        merchant_id=invoice.merchant_id,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        amount_cents=gross,
        subtotal_cents=gross - tax,
        tax_cents=tax,
        tax_province=invoice.tax_province,
        currency=invoice.currency or "cad",
        kind=kind,
        reason_code=code,
        reason=code,
        internal_note=note_text or None,
        customer_reason=public,
        lines_json=lines,
        original_invoice_number=invoice.invoice_number,
        original_invoice_date=issued,
        recipient_name=_recipient_name(db, invoice),
        issued_by=actor_id,
        status="pending_approval",
    )
    db.add(note)
    db.flush()
    if gross <= approval_threshold_cents(db):
        _issue(db, note, invoice, approver_id=None)
    return note


def approve_credit(db: Session, *, credit_note_id: str, actor_id: str) -> CreditNote:
    note = db.query(CreditNote).filter(CreditNote.id == credit_note_id).with_for_update().first()
    if note is None:
        raise LookupError("credit_note_not_found")
    if note.status != "pending_approval":
        raise ValueError("credit_note_not_pending")
    if note.issued_by == actor_id:
        raise PermissionError("credit_note_second_approver_required")
    invoice = db.query(Invoice).filter(Invoice.id == note.invoice_id).with_for_update().first()
    if invoice is None:
        raise LookupError("invoice_not_found")
    # The invoice may have moved on since the request: re-check what is still creditable.
    room = max(0, _total(invoice) - int(invoice.credited_cents or 0))
    if int(note.amount_cents) > room:
        raise ValueError("credit_exceeds_invoice")
    _issue(db, note, invoice, approver_id=actor_id)
    return note


def reject_credit(db: Session, *, credit_note_id: str, actor_id: str, note_text: str | None = None) -> CreditNote:
    note = db.query(CreditNote).filter(CreditNote.id == credit_note_id).with_for_update().first()
    if note is None:
        raise LookupError("credit_note_not_found")
    if note.status != "pending_approval":
        raise ValueError("credit_note_not_pending")
    note.status = "rejected"
    note.approved_by = actor_id
    if note_text:
        note.internal_note = f"{note.internal_note or ''}\n[rejected] {note_text.strip()}".strip()
    db.flush()
    return note


def _issue(db: Session, note: CreditNote, invoice: Invoice, *, approver_id: str | None) -> None:
    from porterchain_api.billing_engine.invoice_document import persist_invoice_status
    from porterchain_api.billing_engine.merchant_service import invoice_net_total_cents

    now = datetime.now(UTC)
    note.credit_note_number = allocate_credit_note_number(db, now=now)
    note.status = "issued"
    note.issued_at = now
    note.approved_by = approver_id
    invoice.credited_cents = int(invoice.credited_cents or 0) + int(note.amount_cents)
    if note.kind == "void" or invoice.credited_cents >= _total(invoice):
        invoice.voided_at = invoice.voided_at or (now if note.kind == "void" else None)
    db.add(
        BillingLedgerEntry(
            kind=LEDGER_KIND,
            invoice_id=invoice.id,
            order_id=invoice.order_id,
            merchant_id=invoice.merchant_id,
            amount_cents=int(note.amount_cents),
            currency=invoice.currency or "cad",
            status="recorded",
            idempotency_key=f"cn:{note.id}",
            metadata_json={
                "credit_note_id": note.id,
                "credit_note_number": note.credit_note_number,
                "kind": note.kind,
                "reason_code": note.reason_code,
                "tax_cents": int(note.tax_cents or 0),
                "invoice_number": invoice.invoice_number,
            },
        )
    )
    db.flush()
    # Money already received above the new net total goes back.
    excess = max(0, _money_in(db, invoice) - _money_back(db, invoice) - invoice_net_total_cents(invoice))
    excess = min(excess, int(note.amount_cents))
    if excess > 0:
        if _is_stripe_retail(db, invoice):
            note.settlement = "stripe_refund_pending"
        elif invoice.merchant_id:
            from porterchain_api.billing_engine.merchant_credit import add_merchant_credit

            add_merchant_credit(
                db,
                merchant_id=invoice.merchant_id,
                amount_cents=excess,
                source={
                    "source": "credit_note",
                    "credit_note_id": note.id,
                    "credit_note_number": note.credit_note_number,
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                },
            )
            note.settlement = "credit_balance"
        else:
            note.settlement = "manual_refund_required"
        note.settlement_cents = excess
    order = db.get(Order, invoice.order_id) if invoice.order_id else None
    pay = (
        db.query(Payment).filter(Payment.order_id == order.id).order_by(Payment.created_at.desc()).first()
        if order is not None
        else None
    )
    persist_invoice_status(invoice, order, pay, terms=(order.payment_terms if order else None))
    db.flush()


def settle_stripe_refund(db: Session, settings: Any, note: CreditNote, *, actor_id: str) -> None:
    """Refund the card for a note marked ``stripe_refund_pending`` (idempotent per note)."""
    from porterchain_api.services.stripe_service import create_refund

    if note.settlement not in ("stripe_refund_pending", "stripe_refund_failed") or not note.settlement_cents:
        return
    invoice = db.get(Invoice, note.invoice_id)
    order = db.get(Order, invoice.order_id) if invoice and invoice.order_id else None
    if order is None:
        return
    pay = db.query(Payment).filter(Payment.order_id == order.id).order_by(Payment.created_at.desc()).first()
    if not order.stripe_payment_intent_id and pay is not None and pay.stripe_payment_intent_id:
        order.stripe_payment_intent_id = pay.stripe_payment_intent_id
    key = f"cn-refund:{note.id}"
    claim = db.query(BillingLedgerEntry).filter(BillingLedgerEntry.idempotency_key == key).first()
    if claim is None:
        claim = BillingLedgerEntry(
            kind="refund",
            payment_id=pay.id if pay else None,
            invoice_id=invoice.id,
            order_id=order.id,
            merchant_id=invoice.merchant_id,
            amount_cents=int(note.settlement_cents),
            currency=invoice.currency or "cad",
            status="pending",
            idempotency_key=key,
            metadata_json={"created_by": actor_id, "credit_note_id": note.id},
        )
        db.add(claim)
        db.commit()
    if claim.status == "recorded":
        note.settlement = "stripe_refund"
        db.commit()
        return
    try:
        refund_id = create_refund(settings, order, int(note.settlement_cents), idempotency_key=key)
    except Exception:
        logger.warning("credit note refund failed (credit_note=%s)", note.credit_note_number, exc_info=True)
        refund_id = None
    if not refund_id:
        claim.status = "failed"
        note.settlement = "stripe_refund_failed"
        db.commit()
        return
    claim.status = "recorded"
    claim.metadata_json = {**(claim.metadata_json or {}), "stripe_refund_id": refund_id}
    note.settlement = "stripe_refund"
    note.settlement_ref = refund_id
    if pay is not None and int(note.settlement_cents) >= int(pay.amount_cents or 0):
        pay.status = "REFUNDED"
    db.commit()


# --------------------------------------------------------------------- views


def tax_reason_warning(note_or_code: Any, invoice: Invoice) -> str | None:
    code = getattr(note_or_code, "reason_code", note_or_code)
    issued = _aware(invoice.issued_at) or _aware(invoice.created_at)
    if code in ERROR_CODES and issued and datetime.now(UTC) - issued > timedelta(days=730):
        return "older_than_2_years_tax_charged_in_error"
    return None


def serialize(note: CreditNote, *, internal: bool) -> dict[str, Any]:
    out = {
        "credit_note_id": note.id,
        "credit_note_number": note.credit_note_number,
        "invoice_id": note.invoice_id,
        "original_invoice_number": note.original_invoice_number,
        "original_invoice_date": note.original_invoice_date.isoformat() if note.original_invoice_date else None,
        "kind": note.kind,
        "reason_code": note.reason_code,
        "customer_reason": note.customer_reason,
        "amount_cents": int(note.amount_cents or 0),
        "subtotal_cents": int(note.subtotal_cents or 0),
        "tax_cents": int(note.tax_cents or 0),
        "tax_province": note.tax_province,
        "currency": note.currency or "cad",
        "lines": [
            {k: v for k, v in ln.items() if k in ("line_id", "description", "gross_cents", "tax_cents")}
            for ln in (note.lines_json or [])
        ],
        "status": note.status,
        "settlement": note.settlement,
        "settlement_cents": int(note.settlement_cents or 0),
        "issued_at": note.issued_at.isoformat() if note.issued_at else None,
        "created_at": note.created_at.isoformat() if note.created_at else None,
    }
    if internal:
        out.update(
            internal_note=note.internal_note,
            issued_by=note.issued_by,
            approved_by=note.approved_by,
            settlement_ref=note.settlement_ref,
        )
    return out


def notes_for_invoice(db: Session, invoice_id: str, *, internal: bool) -> list[dict[str, Any]]:
    statuses = ("issued", "pending_approval", "rejected") if internal else ("issued",)
    return [serialize(n, internal=internal) for n in _notes(db, invoice_id, statuses=statuses)]


def adjustment_summary(db: Session, invoice: Invoice) -> dict[str, Any]:
    return {
        "invoice_id": invoice.id,
        "total_cents": _total(invoice),
        "credited_cents": int(invoice.credited_cents or 0),
        "pending_cents": _pending_cents(db, invoice.id),
        "creditable_cents": creditable_cents(db, invoice),
        "tax_cents": int(invoice.tax_cents or 0),
        "tax_credited_cents": _credited_tax(db, invoice.id),
        "approval_threshold_cents": approval_threshold_cents(db),
        "reason_codes": [{"code": k, "customer_reason": v} for k, v in REASON_CODES.items()],
        "lines": line_breakdown(db, invoice),
        "credit_notes": notes_for_invoice(db, invoice.id, internal=True),
    }

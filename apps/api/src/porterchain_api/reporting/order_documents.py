"""Order print-preview / pickup-list PDFs — commercial dock sheets, not carrier labels.

These are dock documents. Do not title them “shipping label”.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence

from porterchain_api.domain.catalog_labels import order_state_label
from porterchain_api.merchant_engine.toronto import format_datetime_toronto
from porterchain_api.booking_models import Order
from porterchain_api.reporting.compliance_dossier import render_compliance_pdf

_PREVIEW_NOTE = "Print preview for your dock — not a carrier shipping label."


def _addr_line(addr: dict[str, Any] | None) -> str:
    if not isinstance(addr, dict):
        return "—"
    parts = [
        addr.get("name") or addr.get("contact_name"),
        addr.get("formatted") or addr.get("street") or addr.get("address") or addr.get("line1"),
        addr.get("city"),
        addr.get("postal_code") or addr.get("postal") or addr.get("zip"),
    ]
    return ", ".join(str(p) for p in parts if p) or "—"


def _ref_lines(order: Order) -> list[str]:
    lines: list[str] = []
    if getattr(order, "purchase_order_number", None):
        lines.append(f"PO: {order.purchase_order_number}")
    if getattr(order, "internal_reference", None):
        lines.append(f"Your reference: {order.internal_reference}")
    if getattr(order, "cost_centre", None):
        lines.append(f"Cost centre: {order.cost_centre}")
    return lines


def _order_sheet_lines(order: Order) -> list[str]:
    amount = f"${(order.amount_cents or 0) / 100:.2f} {(order.currency or 'cad').upper()}"
    return [
        f"Tracking: {order.tracking_number}",
        f"Order: {order.order_number}",
        f"Status: {order_state_label(order.state)}",
        f"Scheduled: {format_datetime_toronto(order.scheduled_at)}",
        f"Amount: {amount}",
        *_ref_lines(order),
    ]


def build_print_preview_pdf(order: Order) -> bytes:
    """One order per sheet — tracking, stops, references."""
    exported = datetime.now(UTC)
    sections: list[tuple[str, list[str]]] = [
        ("Print preview", [*_order_sheet_lines(order), _PREVIEW_NOTE]),
        ("Pickup", [_addr_line(order.pickup if isinstance(order.pickup, dict) else None)]),
        ("Delivery", [_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)]),
    ]
    if order.special_instructions:
        sections.append(("Instructions", [order.special_instructions[:240]]))
    footer = f"{order.tracking_number} · print preview {format_datetime_toronto(exported)}"
    return render_compliance_pdf(sections, title="Print preview", footer=footer)


def build_label_pdf(order: Order) -> bytes:
    """Retired dishonest alias — use LabelService / labels.pdf."""
    raise RuntimeError("use LabelService — GET /orders/{id}/labels.pdf")


def _money(cents: int | None, currency: str) -> str:
    cur = (currency or "cad").upper()
    return f"${(cents or 0) / 100:.2f} {cur}"


def _issuer_from_db(db: Any) -> tuple[str, str, str]:
    """Platform name, legal name, support email. Defaults if settings are unavailable."""
    name = "PorterChain"
    legal = "Porterchain Logistics Inc."
    email = "support@porterchain.com"
    try:
        from porterchain_api.admin_engine.platform_settings import (
            general_settings,
            platform_company_name,
            platform_support_email,
        )

        raw_name = platform_company_name(db)
        if isinstance(raw_name, str) and raw_name.strip():
            name = raw_name.strip()
        general = general_settings(db)
        if isinstance(general, dict):
            raw_legal = general.get("legal_name")
            if isinstance(raw_legal, str) and raw_legal.strip():
                legal = raw_legal.strip()
        raw_email = platform_support_email(db)
        if isinstance(raw_email, str) and raw_email.strip():
            email = raw_email.strip()
    except Exception:
        pass
    return name, legal, email


def render_branded_invoice_pdf(
    *,
    invoice_number: str,
    amount_cents: int,
    currency: str = "cad",
    tax_cents: int = 0,
    fees_cents: int = 0,
    outstanding_cents: int | None = None,
    receipt_number: str | None = None,
    status: str | None = None,
    payment_terms: str | None = None,
    due_date: str | None = None,
    issued_at: str | None = None,
    order_number: str | None = None,
    tracking_number: str | None = None,
    order_status: str | None = None,
    merchant_name: str | None = None,
    merchant_email: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    pickup: str | None = None,
    delivery: str | None = None,
    lines: Sequence[dict[str, Any]] | None = None,
    issuer_name: str = "PorterChain",
    issuer_legal_name: str = "Porterchain Logistics Inc.",
    support_email: str = "support@porterchain.com",
    compliance: dict[str, Any] | None = None,
) -> bytes:
    """Multi-page PorterChain invoice. Amount labels stay plain text so cents checks can read them."""
    import io

    from pathlib import Path

    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus.flowables import Flowable

    navy = HexColor("#0a1628")
    accent = HexColor("#2563eb")
    muted = HexColor("#64748b")
    line_color = HexColor("#e2e8f0")
    surface = HexColor("#f8fafc")
    page_w, page_h = letter
    cur = (currency or "cad").upper()
    amount = _money(amount_cents, currency)
    tax = _money(tax_cents, currency)
    fees = _money(fees_cents, currency)
    due_amount = _money(
        outstanding_cents if outstanding_cents is not None else amount_cents,
        currency,
    )
    has_customer = bool((customer_name or "").strip() or (customer_email or "").strip())
    if has_customer:
        bill_lines = [
            f"Bill to: {customer_name or customer_email or '—'}",
            f"Customer: {customer_email or '—'}",
        ]
        if merchant_name:
            bill_lines.append(f"Account: {merchant_name}")
    else:
        bill_lines = [
            f"Bill to: {merchant_name or '—'}",
            f"Customer: {merchant_email or '—'}",
        ]

    class LiteralBlock(Flowable):
        def __init__(self, rows: list[str], size: float = 10, leading: float = 14, color=navy):
            super().__init__()
            self.rows = rows
            self.size = size
            self.leading = leading
            self.color = color
            self._width = 460
            self.height = leading * max(len(rows), 1)

        def wrap(self, avail_width, avail_height):
            self._width = avail_width
            return avail_width, self.height

        def draw(self):
            self.canv.setFillColor(self.color)
            self.canv.setFont("Helvetica", self.size)
            y = self.height - self.size
            for row in self.rows:
                self.canv.drawString(0, y, row)
                y -= self.leading

    mark = ImageReader(
        str(Path(__file__).resolve().parent / "brand" / "porterchain-mark-white.png")
    )
    mark_h = 36
    mark_w = 36 * (298 / 267)

    def paint_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(navy)
        canvas.rect(0, page_h - 64, page_w, 64, fill=1, stroke=0)
        canvas.setFillColor(accent)
        canvas.rect(0, page_h - 68, page_w, 4, fill=1, stroke=0)
        canvas.drawImage(
            mark,
            40,
            page_h - 50,
            width=mark_w,
            height=mark_h,
            mask="auto",
            preserveAspectRatio=True,
            anchor="sw",
        )
        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(40 + mark_w + 8, page_h - 32, "porterchain")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40 + mark_w + 8, page_h - 46, issuer_legal_name[:72])
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(page_w - 48, page_h - 32, "INVOICE")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(page_w - 48, page_h - 48, invoice_number)
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(48, 28, f"{support_email} · {invoice_number}")
        canvas.drawRightString(page_w - 48, 28, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=letter,
        title=f"Porterchain Invoice {invoice_number}",
        author=issuer_name or "PorterChain",
    )
    doc.pageCompression = 0
    frame = Frame(48, 46, page_w - 96, page_h - 68 - 46, id="body", showBoundary=0)
    doc.addPageTemplates([PageTemplate(id="invoice", frames=[frame], onPage=paint_page)])

    label = ParagraphStyle(
        "invLabel",
        fontName="Helvetica",
        fontSize=8,
        textColor=muted,
        leading=11,
        spaceAfter=2,
    )
    body = ParagraphStyle(
        "invBody",
        fontName="Helvetica",
        fontSize=10,
        textColor=navy,
        leading=13,
    )

    comp = dict(compliance or {})
    story: list[Any] = [Spacer(1, 8)]
    if comp.get("supplier_tax_number"):
        # CRA: supplier name + GST/HST registration number on every invoice of $100+.
        story.append(
            LiteralBlock(
                [
                    f"{issuer_legal_name}",
                    *( [str(comp["issuer_address"])] if comp.get("issuer_address") else [] ),
                    f"GST/HST Reg. No.: {comp['supplier_tax_number']}",
                ],
                size=9,
                leading=13,
            )
        )
        story.append(Spacer(1, 6))
    is_cycle = bool(comp.get("billing_period"))
    if is_cycle:
        # One invoice for many deliveries: no single order/route; dates as YYYY-MM-DD.
        meta = [
            f"Status: {status or '—'}",
            f"Issued: {(issued_at or '—')[:10]}",
            f"Due: {(due_date or '—')[:10]}",
            f"Terms: {payment_terms or '—'}",
        ]
    else:
        meta = [
            f"Receipt: {receipt_number or '—'}",
            f"Status: {status or order_status or '—'}",
            f"Issued: {issued_at or '—'}",
            f"Due: {due_date or '—'}",
            f"Terms: {payment_terms or '—'}",
            f"Order: {order_number or '—'}",
            f"Tracking: {tracking_number or '—'}",
        ]
    if comp.get("billing_period"):
        meta.append(f"Billing period: {comp['billing_period']}")
    if comp.get("payment_reference"):
        meta.append(f"Payment reference: {comp['payment_reference']}")
    story.append(LiteralBlock(meta, size=9, leading=13))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Bill to", label))
    story.append(LiteralBlock(bill_lines, size=10, leading=14))
    story.append(Spacer(1, 8))
    if not is_cycle:
        story.append(Paragraph("Route", label))
        story.append(
            LiteralBlock(
                [
                    f"Pickup: {pickup or '—'}",
                    f"Delivery: {delivery or '—'}",
                ],
                size=9,
                leading=12,
            )
        )
    story.append(Spacer(1, 12))

    header = [
        Paragraph("Description", label),
        Paragraph("Order", label),
        Paragraph("Amount", label),
    ]
    table_rows: list[list[Any]] = [header]
    line_literals: list[str] = []
    for ln in list(lines or [])[:80]:
        desc = str(ln.get("description") or "Delivery")
        cents = int(ln.get("amount_cents") or 0)
        channel = ln.get("channel") or "—"
        model = ln.get("pricing_model") or "—"
        order_no = str(ln.get("order_number") or order_number or "—")
        line_literals.append(f"{desc} · {channel}/{model} · ${cents / 100:.2f} {cur}")
        table_rows.append(
            [
                Paragraph(desc.replace("&", "&amp;").replace("<", "&lt;"), body),
                Paragraph(order_no, body),
                Paragraph(_money(cents, currency), body),
            ]
        )
    if len(table_rows) == 1:
        table_rows.append(
            [
                Paragraph("Delivery", body),
                Paragraph(order_number or "—", body),
                Paragraph(amount, body),
            ]
        )
    table = Table(table_rows, colWidths=[3.2 * inch, 2.0 * inch, 1.4 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), surface),
                ("TEXTCOLOR", (0, 0), (-1, 0), muted),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, line_color),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    if line_literals:
        story.append(Spacer(1, 6))
        story.append(LiteralBlock(line_literals, size=8, leading=11, color=muted))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Totals", label))
    story.append(
        LiteralBlock(
            [
                f"Amount: {amount}",
                f"Tax: {tax}" + (f" ({comp['tax_label']})" if comp.get("tax_label") else ""),
                f"Fees: {fees}",
                *([f"Paid: {_money(int(comp['amount_paid_cents']), currency)}"] if comp.get("amount_paid_cents") else []),
                f"Outstanding: {due_amount}",
            ],
            size=11,
            leading=16,
        )
    )
    owing = outstanding_cents if outstanding_cents is not None else amount_cents
    if comp.get("payment_reference") and comp.get("etransfer_email") and int(owing or 0) > 0:
        story.append(Spacer(1, 14))
        story.append(Paragraph("How to pay — Interac e-Transfer", label))
        rows = [
            f"Send to: {comp['etransfer_email']}",
            f"Amount: {due_amount}",
            f"Message: {comp['payment_reference']}  (required — this is how we match your payment)",
        ]
        if comp.get("autodeposit"):
            rows.append("Autodeposit is on: no security question needed.")
        rows.append("Partial payments are applied; overpayments become credit on your next invoice.")
        story.append(LiteralBlock(rows, size=10, leading=14))
    doc.build(story)
    return buf.getvalue()


def build_invoice_pdf(
    order: Order,
    *,
    invoice_number: str,
    amount_cents: int,
    currency: str = "cad",
    receipt_number: str | None = None,
    merchant_name: str | None = None,
    merchant_email: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    tax_cents: int = 0,
    fees_cents: int = 0,
    outstanding_cents: int | None = None,
    lines: Sequence[dict[str, Any]] | None = None,
    status: str | None = None,
    payment_terms: str | None = None,
    due_date: str | None = None,
    issued_at: str | None = None,
    issuer_name: str | None = None,
    issuer_legal_name: str | None = None,
    support_email: str | None = None,
    compliance: dict[str, Any] | None = None,
) -> bytes:
    """Commercial invoice. Amounts must match GET invoice detail."""
    return render_branded_invoice_pdf(
        invoice_number=invoice_number,
        amount_cents=amount_cents,
        currency=currency,
        tax_cents=tax_cents,
        fees_cents=fees_cents,
        outstanding_cents=outstanding_cents,
        receipt_number=receipt_number,
        status=status,
        payment_terms=payment_terms,
        due_date=due_date,
        issued_at=issued_at,
        order_number=getattr(order, "order_number", None),
        tracking_number=getattr(order, "tracking_number", None),
        order_status=order_state_label(getattr(order, "state", None)) if getattr(order, "state", None) else None,
        merchant_name=merchant_name,
        merchant_email=merchant_email,
        customer_name=customer_name,
        customer_email=customer_email,
        pickup=_addr_line(order.pickup if isinstance(getattr(order, "pickup", None), dict) else None),
        delivery=_addr_line(order.dropoff if isinstance(getattr(order, "dropoff", None), dict) else None),
        lines=lines,
        issuer_name=issuer_name or "PorterChain",
        issuer_legal_name=issuer_legal_name or "Porterchain Logistics Inc.",
        support_email=support_email or "support@porterchain.com",
        compliance=compliance,
    )


def _province_tax_label(db: Any, province: str | None) -> str | None:
    if not province:
        return None
    from porterchain_api.admin_engine.platform_settings import collect_qst
    from porterchain_pricing.tax.provinces import PROVINCES

    prov = PROVINCES.get(province)
    return f"{prov.label(collect_qst=collect_qst(db))} ({province})" if prov else None


def invoice_compliance(db: Any, invoice: Any) -> dict[str, Any]:
    """CRA + Interac fields for an invoice PDF (supplier GST/HST #, tax label, e-Transfer)."""
    from porterchain_api.admin_engine.platform_settings import (
        etransfer_autodeposit,
        etransfer_recipient_email,
        finance_settings,
        supplier_gst_hst_number,
        tax_label,
    )

    is_b2b = bool(getattr(invoice, "merchant_id", None)) and not getattr(invoice, "customer_id", None)
    start = getattr(invoice, "billing_period_start", None)
    end = getattr(invoice, "billing_period_end", None)
    period = None
    if start and end and getattr(invoice, "billing_kind", "order") == "cycle":
        from datetime import timedelta

        period = f"{start.date().isoformat()} to {(end - timedelta(seconds=1)).date().isoformat()}"
    return {
        "supplier_tax_number": supplier_gst_hst_number(db),
        "issuer_address": str(finance_settings(db).get("business_address") or "").strip() or None,
        "tax_label": _province_tax_label(db, getattr(invoice, "tax_province", None)) or tax_label(db),
        "payment_reference": getattr(invoice, "payment_reference", None) if is_b2b else None,
        "etransfer_email": etransfer_recipient_email(db) if is_b2b else None,
        "autodeposit": etransfer_autodeposit(db),
        "amount_paid_cents": int(getattr(invoice, "amount_paid_cents", 0) or 0),
        "billing_period": period,
    }


def pdf_for_invoice_record(db: Any, invoice: Any, *, lines: Sequence[dict[str, Any]] | None = None) -> tuple[bytes, str]:
    """Branded PDF for a stored invoice, including tax, fees, outstanding, and lines."""
    from porterchain_api.billing_engine.merchant_service import (
        invoice_status,
        outstanding_cents,
    )
    from porterchain_api.billing_engine.models import InvoiceLine
    from porterchain_api.booking_models import Customer, Order, Payment
    from porterchain_api.merchant_engine.lookups import get_merchant
    from porterchain_api.merchant_engine.reporting_metrics import channel_for_order_source

    order = db.get(Order, invoice.order_id) if getattr(invoice, "order_id", None) else None
    if order is None:
        order = type(
            "OrderShell",
            (),
            {
                "order_number": invoice.invoice_number,
                "tracking_number": "—",
                "state": "INVOICED",
                "pickup": {},
                "dropoff": {},
                "order_source": None,
                "payment_terms": None,
                "customer_id": getattr(invoice, "customer_id", None),
                "merchant_id": getattr(invoice, "merchant_id", None),
            },
        )()

    customer = None
    customer_id = getattr(invoice, "customer_id", None) or getattr(order, "customer_id", None)
    if customer_id:
        customer = db.get(Customer, customer_id)
    merchant = None
    merchant_id = getattr(invoice, "merchant_id", None) or getattr(order, "merchant_id", None)
    if merchant_id:
        merchant = get_merchant(db, merchant_id)

    payment = None
    if getattr(invoice, "order_id", None):
        payment = (
            db.query(Payment)
            .filter(Payment.order_id == invoice.order_id)
            .order_by(Payment.created_at.desc())
            .first()
        )
    terms = getattr(order, "payment_terms", None) or (
        getattr(merchant, "payment_terms", None) if merchant else None
    )
    status = invoice_status(invoice, order if getattr(order, "id", None) else None, payment, terms=terms)
    due = outstanding_cents(invoice, status)

    line_rows: list[dict[str, Any]] = [dict(ln) for ln in lines] if lines else []
    if not line_rows:
        stored = (
            db.query(InvoiceLine)
            .filter(InvoiceLine.invoice_id == invoice.id)
            .all()
        )
        for ln in stored:
            linked = db.get(Order, ln.order_id) if ln.order_id else order
            source = getattr(linked, "order_source", None)
            line_rows.append(
                {
                    "description": ln.description or "Delivery",
                    "amount_cents": int(ln.amount_cents or 0),
                    "order_number": getattr(linked, "order_number", None),
                    "channel": channel_for_order_source(source) if source else None,
                    "pricing_model": getattr(merchant, "pricing_model", None) if merchant else None,
                }
            )
    if not line_rows:
        line_rows.append(
            {
                "description": "Delivery",
                "amount_cents": int(invoice.amount_cents or 0),
                "order_number": getattr(order, "order_number", None),
                "channel": None,
                "pricing_model": getattr(merchant, "pricing_model", None) if merchant else None,
            }
        )

    issuer_name, legal, support = _issuer_from_db(db)
    issued = getattr(invoice, "issued_at", None) or getattr(invoice, "created_at", None)
    due_at = getattr(invoice, "due_at", None)
    pdf = build_invoice_pdf(
        order,
        invoice_number=invoice.invoice_number,
        amount_cents=int(invoice.amount_cents or 0),
        currency=invoice.currency or "cad",
        tax_cents=int(invoice.tax_cents or 0),
        fees_cents=int(invoice.fees_cents or 0),
        outstanding_cents=due,
        receipt_number=invoice.receipt_number,
        merchant_name=getattr(merchant, "company_name", None) if merchant else None,
        merchant_email=getattr(merchant, "email", None) if merchant else None,
        customer_name=getattr(customer, "full_name", None) if customer else None,
        customer_email=getattr(customer, "email", None) if customer else None,
        lines=line_rows,
        status=status,
        payment_terms=terms,
        due_date=due_at.isoformat() if due_at else None,
        issued_at=issued.isoformat() if issued else None,
        issuer_name=issuer_name,
        issuer_legal_name=legal,
        support_email=support,
        compliance=invoice_compliance(db, invoice),
    )
    return pdf, f"invoice-{invoice.invoice_number}.pdf"


def pdf_bytes_for_invoice_id(db: Any, invoice_id: str) -> tuple[bytes, str] | None:
    """Admin download: branded PDF for one invoice id, or None when missing."""
    from porterchain_api.booking_models import Invoice

    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        return None
    return pdf_for_invoice_record(db, invoice)


def pdf_for_merchant_invoice(
    db: Any,
    invoice_id: str,
    detail: dict[str, Any],
    *,
    merchant_name: str | None,
    merchant_email: str | None,
) -> tuple[bytes, str]:
    """Merchant download from an already-authorized invoice detail payload."""
    from types import SimpleNamespace

    from porterchain_api.booking_models import Customer, Invoice, Order

    order = None
    if detail.get("lines"):
        oid = detail["lines"][0].get("order_id")
        if oid:
            order = db.get(Order, oid)
    if order is None and detail.get("invoice_id"):
        inv_row = db.get(Invoice, invoice_id)
        if inv_row and inv_row.order_id:
            order = db.get(Order, inv_row.order_id)
    if order is None:
        order = SimpleNamespace(
            order_number=detail.get("invoice_number") or "—",
            tracking_number="—",
            state="INVOICED",
            amount_cents=int(detail["amount_cents"]),
            currency=detail.get("currency") or "cad",
            pickup={},
            dropoff={},
            special_instructions=None,
        )

    line_rows = [
        {
            "description": ln.get("description") or "Delivery",
            "amount_cents": int(ln.get("amount_cents") or 0),
            "order_number": ln.get("order_number"),
            "channel": ln.get("channel"),
            "pricing_model": ln.get("pricing_model"),
        }
        for ln in detail.get("lines") or []
    ]
    inv = db.get(Invoice, invoice_id)
    customer_name = None
    customer_email = None
    if inv and inv.customer_id:
        customer = db.get(Customer, inv.customer_id)
        if customer:
            customer_name = customer.full_name
            customer_email = customer.email
    elif order is not None and getattr(order, "customer_id", None):
        customer = db.get(Customer, order.customer_id)
        if customer:
            customer_name = customer.full_name
            customer_email = customer.email
    issuer_name, legal, support = _issuer_from_db(db)
    issued = None
    stamp = getattr(inv, "issued_at", None) or getattr(inv, "created_at", None) if inv else None
    if stamp is not None:
        issued = stamp.isoformat() if hasattr(stamp, "isoformat") else str(stamp)
    due_label = detail.get("due_date")
    if due_label is not None and hasattr(due_label, "isoformat"):
        due_label = due_label.isoformat()
    pdf = build_invoice_pdf(
        order,
        invoice_number=detail["invoice_number"],
        amount_cents=int(detail["amount_cents"]),
        currency=detail.get("currency") or "cad",
        tax_cents=int(detail.get("tax_cents") or 0),
        fees_cents=int(detail.get("fees_cents") or 0),
        outstanding_cents=int(detail.get("outstanding_cents") or 0),
        receipt_number=inv.receipt_number if inv else None,
        merchant_name=merchant_name,
        merchant_email=merchant_email,
        customer_name=customer_name,
        customer_email=customer_email,
        lines=line_rows,
        status=detail.get("status"),
        payment_terms=detail.get("payment_terms"),
        due_date=str(due_label) if due_label else None,
        issued_at=issued,
        issuer_name=issuer_name,
        issuer_legal_name=legal,
        support_email=support,
        compliance=invoice_compliance(db, inv) if inv is not None else None,
    )
    return pdf, f"invoice-{detail['invoice_number']}.pdf"


def build_pickup_list_pdf(
    orders: Sequence[Order],
    *,
    merchant_name: str | None = None,
    driver_name: str | None = None,
) -> bytes:
    """Dock list for one or more orders."""
    exported = datetime.now(UTC)
    header = [
        f"Company: {merchant_name or '—'}",
        f"Orders: {len(orders)}",
        f"Printed: {format_datetime_toronto(exported)}",
        _PREVIEW_NOTE,
    ]
    if driver_name:
        header.insert(2, f"Driver: {driver_name}")
    sections: list[tuple[str, list[str]]] = [("Pickup list", header)]
    for index, order in enumerate(orders, start=1):
        lines = [
            *_order_sheet_lines(order),
            f"Pickup: {_addr_line(order.pickup if isinstance(order.pickup, dict) else None)}",
            f"Delivery: {_addr_line(order.dropoff if isinstance(order.dropoff, dict) else None)}",
        ]
        compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
        stops = compliance.get("stops") or compliance.get("additional_stops") or []
        if isinstance(stops, list) and stops:
            for i, stop in enumerate(stops[:8], start=1):
                if isinstance(stop, dict):
                    lines.append(f"Stop {i}: {_addr_line(stop)}")
                else:
                    lines.append(f"Stop {i}: {stop}")
        sections.append((f"{index}. {order.tracking_number}", lines))
    footer = f"Pickup list · {len(orders)} order(s) · {format_datetime_toronto(exported)}"
    return render_compliance_pdf(sections, title="Pickup list", footer=footer)


def build_manifest_pdf(order: Order, *, driver_name: str | None = None) -> bytes:
    """Admin alias — same pickup list for one order."""
    return build_pickup_list_pdf([order], driver_name=driver_name)

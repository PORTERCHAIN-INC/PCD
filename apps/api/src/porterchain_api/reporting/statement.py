"""Merchant account statement PDF: balance, how to pay (Interac + PC codes), open
invoices, payments received in the last 90 days. Deep navy + one accent, bold numbers."""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Invoice, Order, Payment

NAVY = "#0B1B3F"
ACCENT = "#1F6FEB"
MUTED = "#4B5563"


def _money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def statement_data(db: Session, merchant: Any, *, now: datetime | None = None) -> dict[str, Any]:
    from porterchain_api.billing_engine.merchant_service import invoice_status, invoice_total_cents, outstanding_cents
    from porterchain_api.platform.merchant_billing import etransfer_recipient_email

    now = now or datetime.now(UTC)
    invs = (
        db.query(Invoice)
        .outerjoin(Order, Invoice.order_id == Order.id)
        .filter(Invoice.customer_id.is_(None))
        .filter(or_(Invoice.merchant_id == merchant.id, Order.merchant_id == merchant.id))
        .order_by(Invoice.created_at.asc())
        .all()
    )
    open_rows, paid_ids = [], []
    for inv in invs:
        order = db.get(Order, inv.order_id) if inv.order_id else None
        payment = (
            db.query(Payment).filter(Payment.order_id == inv.order_id).order_by(Payment.created_at.desc()).first()
            if inv.order_id
            else None
        )
        st = invoice_status(inv, order, payment, terms=merchant.payment_terms)
        out = outstanding_cents(inv, st)
        paid_ids.append(inv.id)
        if out > 0:
            open_rows.append(
                {
                    "invoice_number": inv.invoice_number,
                    "issued": (inv.issued_at or inv.created_at).date().isoformat() if (inv.issued_at or inv.created_at) else "",
                    "due": inv.due_at.date().isoformat() if inv.due_at else "",
                    "reference": inv.payment_reference or "",
                    "total_cents": invoice_total_cents(inv),
                    "paid_cents": int(inv.amount_paid_cents or 0),
                    "outstanding_cents": out,
                    "status": st,
                }
            )
    since = now - timedelta(days=90)
    payments = (
        db.query(Payment)
        .filter(Payment.invoice_id.in_(paid_ids), Payment.status == "SUCCEEDED", Payment.created_at >= since)
        .order_by(Payment.created_at.desc())
        .all()
        if paid_ids
        else []
    )
    from porterchain_api.platform.merchant_billing import merchant_credit_cents

    # Delivery activity for the statement body (every parcel on recent cycle invoices).
    from porterchain_api.billing_engine.models import InvoiceLine

    delivery_rows: list[dict[str, Any]] = []
    recent_inv_ids = [inv.id for inv in invs if (inv.issued_at or inv.created_at or now) >= now - timedelta(days=90)]
    if recent_inv_ids:
        line_rows = (
            db.query(InvoiceLine)
            .filter(InvoiceLine.invoice_id.in_(recent_inv_ids), InvoiceLine.order_id.isnot(None))
            .order_by(InvoiceLine.created_at.asc())
            .all()
        )
        seen_orders: set[str] = set()
        for ln in line_rows:
            if not ln.order_id or ln.order_id in seen_orders:
                continue
            seen_orders.add(ln.order_id)
            order = db.get(Order, ln.order_id)
            if not order:
                continue
            drop = order.dropoff if isinstance(order.dropoff, dict) else {}
            meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
            day = meta.get("route_day") or drop.get("route_day")
            seq = meta.get("route_seq") or drop.get("route_seq") or 0
            try:
                seq_n = int(seq)
            except (TypeError, ValueError):
                seq_n = 0
            try:
                day_n = int(day) if day not in (None, "") else 0
            except (TypeError, ValueError):
                day_n = 0
            delivery_rows.append(
                {
                    "day": str(day) if day else "",
                    "day_n": day_n,
                    "seq_n": seq_n,
                    "order_number": order.order_number or "",
                    "address": (drop.get("formatted") or drop.get("line1") or "")[:72],
                    "name": (drop.get("contact_name") or drop.get("name") or "")[:36],
                    "phone": (drop.get("phone") or "")[:18],
                    "status": order.state or "",
                    "amount_cents": int(order.amount_cents or 0) or (int(ln.amount_cents or 0) + int(ln.tax_cents or 0)),
                }
            )
        delivery_rows.sort(key=lambda r: (r.get("day_n") or 0, r.get("seq_n") or 0, r.get("order_number") or ""))

    return {
        "merchant_name": merchant.company_name or merchant.legal_name or "Merchant",
        "generated": now.date().isoformat(),
        "balance_cents": sum(r["outstanding_cents"] for r in open_rows),
        "overdue_cents": sum(r["outstanding_cents"] for r in open_rows if r["status"] == "overdue"),
        "credit_cents": merchant_credit_cents(db, merchant.id),
        "open": open_rows,
        "payments": [
            {
                "date": p.created_at.date().isoformat() if p.created_at else "",
                "method": p.payment_method or "card",
                "reference": p.payment_reference or "",
                "amount_cents": int(p.amount_cents or 0),
            }
            for p in payments
        ],
        "deliveries": delivery_rows,
        "etransfer_email": etransfer_recipient_email(db),
    }


def statement_pdf(data: dict[str, Any], *, issuer: str = "Porterchain Inc.", tax_number: str = "") -> bytes:
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    navy, accent, muted = HexColor(NAVY), HexColor(ACCENT), HexColor(MUTED)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch, title="Account statement")
    h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=20, textColor=navy, leading=24)
    small = ParagraphStyle("s", fontName="Helvetica", fontSize=9, textColor=muted, leading=12)
    big = ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=30, textColor=navy, leading=34)
    label = ParagraphStyle("l", fontName="Helvetica-Bold", fontSize=9, textColor=accent, leading=12)
    body = ParagraphStyle("p", fontName="Helvetica", fontSize=10, textColor=navy, leading=14)
    story: list[Any] = [
        Paragraph("PorterChain · Account statement", h),
        Paragraph(f"{data['merchant_name']} · {data['generated']}"
                  + (f" · GST/HST {tax_number}" if tax_number else "") + f" · {issuer}", small),
        Spacer(1, 18),
        Paragraph("BALANCE DUE", label),
        Paragraph(_money(data["balance_cents"]), big),
    ]
    if data["overdue_cents"]:
        story.append(Paragraph(f"{_money(data['overdue_cents'])} is past due.", body))
    if data["credit_cents"]:
        story.append(Paragraph(f"Credit on account: {_money(data['credit_cents'])} (applied to your next invoice).", body))
    refs = ", ".join(r["reference"] for r in data["open"] if r["reference"]) or "your invoice number"
    pay = Table(
        [[Paragraph("HOW TO PAY — INTERAC e-TRANSFER", ParagraphStyle("w", parent=label, textColor=white))],
         [Paragraph(f"Send to <b>{data['etransfer_email']}</b>", ParagraphStyle("w2", parent=body, textColor=white))],
         [Paragraph(f"Put the code in the message: <b>{refs}</b>", ParagraphStyle("w3", parent=body, textColor=white))],
         [Paragraph("One e-Transfer per invoice is fastest to match.", ParagraphStyle("w4", parent=small, textColor=white))]],
        colWidths=[7.1 * inch],
    )
    pay.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), navy), ("LEFTPADDING", (0, 0), (-1, -1), 12),
                             ("TOPPADDING", (0, 0), (0, 0), 10), ("BOTTOMPADDING", (0, -1), (-1, -1), 10)]))
    story += [Spacer(1, 14), pay, Spacer(1, 18), Paragraph("OPEN INVOICES", label), Spacer(1, 4)]
    rows = [["Invoice", "Issued", "Due", "Code", "Total", "Paid", "Owing"]]
    for r in data["open"]:
        rows.append([r["invoice_number"], r["issued"], r["due"], r["reference"], _money(r["total_cents"]),
                     _money(r["paid_cents"]), _money(r["outstanding_cents"])])
    if len(rows) == 1:
        rows.append(["Nothing owing — thank you.", "", "", "", "", "", ""])
    t = Table(rows, colWidths=[1.45 * inch, 0.85 * inch, 0.85 * inch, 0.85 * inch, 1.0 * inch, 0.95 * inch, 1.15 * inch],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("TEXTCOLOR", (0, 0), (-1, 0), muted),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9), ("TEXTCOLOR", (0, 1), (-1, -1), navy),
        ("FONT", (-1, 1), (-1, -1), "Helvetica-Bold", 9), ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, HexColor("#E5E7EB")), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [t, Spacer(1, 16), Paragraph("PAYMENTS RECEIVED (LAST 90 DAYS)", label), Spacer(1, 4)]
    prow = [["Date", "Method", "Reference", "Amount"]] + [
        [p["date"], p["method"], p["reference"], _money(p["amount_cents"])] for p in data["payments"]
    ]
    if len(prow) == 1:
        prow.append(["—", "", "", ""])
    pt = Table(prow, colWidths=[1.3 * inch, 1.3 * inch, 3.0 * inch, 1.5 * inch])
    pt.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("TEXTCOLOR", (0, 0), (-1, 0), muted),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9), ("TEXTCOLOR", (0, 1), (-1, -1), navy),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, HexColor("#E5E7EB")),
    ]))
    story.append(pt)
    deliveries = data.get("deliveries") or []
    if deliveries:
        story += [Spacer(1, 16), Paragraph("DELIVERIES / RETURNS DETAIL", label), Spacer(1, 4)]
        drow = [["Day", "Order", "Address", "Name", "Phone", "Status", "Amount"]]
        for d in deliveries:
            drow.append(
                [
                    str(d.get("day") or ""),
                    d.get("order_number") or "",
                    (d.get("address") or "")[:42],
                    (d.get("name") or "")[:22],
                    d.get("phone") or "",
                    d.get("status") or "",
                    _money(int(d.get("amount_cents") or 0)),
                ]
            )
        dt = Table(
            drow,
            colWidths=[0.4 * inch, 1.35 * inch, 2.15 * inch, 1.05 * inch, 0.95 * inch, 0.7 * inch, 0.7 * inch],
            repeatRows=1,
        )
        dt.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7),
                    ("TEXTCOLOR", (0, 0), (-1, 0), muted),
                    ("FONT", (0, 1), (-1, -1), "Helvetica", 7),
                    ("TEXTCOLOR", (0, 1), (-1, -1), navy),
                    ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, HexColor("#E5E7EB")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(dt)
        delivered = sum(1 for d in deliveries if (d.get("status") or "").upper() in {"DELIVERED", "INVOICED", "CLOSED"})
        returns = sum(1 for d in deliveries if "RETURN" in (d.get("status") or "").upper())
        story.append(
            Spacer(1, 8),
        )
        story.append(
            Paragraph(
                f"Totals: {len(deliveries)} parcels · {delivered} deliveries · {returns} returns.",
                body,
            )
        )
    doc.build(story)
    return buf.getvalue()

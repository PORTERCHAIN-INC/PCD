"""GST/HST credit-note PDF with the SOR/91-44 s.3 prescribed information.

Prints: "CREDIT NOTE", the number, the supplier's legal name and GST/HST number, the
recipient, the issue date, the original invoice number and date, each credited
line, the pre-tax amount, the tax reversed (rate and province) and the total.
The internal staff note is never printed (PIPEDA 4.5).
"""

from __future__ import annotations

import io
from typing import Any

from porterchain_api.reporting.order_documents import _issuer_from_db, _money, _province_tax_label


def _date(dt: Any) -> str:
    if not dt:
        return "-"
    from datetime import UTC
    from zoneinfo import ZoneInfo

    aware = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    return aware.astimezone(ZoneInfo("America/Toronto")).date().isoformat()


def credit_note_pdf(db: Any, note: Any) -> tuple[bytes, str]:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape

    from porterchain_api.admin_engine.platform_settings import finance_settings
    from porterchain_api.platform.tax_registration import registration_at

    if note.status != "issued" or not note.credit_note_number:
        raise ValueError("credit_note_not_issued")
    name, legal, support = _issuer_from_db(db)
    # Tax shown only if the original invoice charged tax; the number is the one in force
    # when that invoice was issued (a non-registrant's note shows no GST/HST at all).
    taxed = int(note.tax_cents or 0) > 0
    reg = registration_at(db, note.original_invoice_date or note.issued_at)
    bn = reg.gst_hst_number if taxed else ""
    if taxed and reg.legal_name:
        legal = reg.legal_name
    address = str(finance_settings(db).get("business_address") or "").strip()
    cur = note.currency or "cad"
    label = _province_tax_label(db, note.tax_province) or "GST/HST"
    navy = HexColor("#0a1628")
    muted = HexColor("#64748b")
    h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=20, textColor=navy, leading=24)
    b = ParagraphStyle("b", fontName="Helvetica", fontSize=10, textColor=navy, leading=14)
    small = ParagraphStyle("s", fontName="Helvetica", fontSize=8, textColor=muted, leading=11)

    recipient_addr = ""
    if note.merchant_id and not note.customer_id:
        from porterchain_api.merchant_engine.lookups import get_merchant

        m = get_merchant(db, note.merchant_id)
        addr = getattr(m, "billing_address", None) if m else None
        if isinstance(addr, dict):
            recipient_addr = ", ".join(
                str(addr.get(k)) for k in ("line1", "line2", "city", "province", "postal_code") if addr.get(k)
            )

    def p(text: str, style=b) -> Paragraph:
        return Paragraph(escape(text).replace("\n", "<br/>"), style)

    story: list[Any] = [
        p("CREDIT NOTE", h),
        Spacer(1, 4),
        p(f"Credit note number: {note.credit_note_number}"),
        p(f"Date issued: {_date(note.issued_at)}"),
        Spacer(1, 10),
    ]
    supplier = [f"Supplier: {legal}" + (f" ({name})" if name and name != legal else "")]
    if address:
        supplier.append(address)
    if bn:
        supplier.append(f"GST/HST registration no.: {bn}")
    supplier.append(f"Contact: {support}")
    recipient = [f"Recipient: {note.recipient_name or '-'}"]
    if recipient_addr:
        recipient.append(recipient_addr)
    head = Table([[p("\n".join(supplier)), p("\n".join(recipient))]], colWidths=[3.4 * inch, 3.4 * inch])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [
        head,
        Spacer(1, 10),
        p(
            f"This credit note adjusts invoice {note.original_invoice_number or '-'} "
            f"dated {_date(note.original_invoice_date)}."
        ),
        p(f"Reason: {note.customer_reason or '-'}"),
        Spacer(1, 10),
    ]
    if taxed:
        rows = [["Description", "Before tax", "Tax", "Total"]]
        for ln in note.lines_json or []:
            g, tx = int(ln.get("gross_cents") or 0), int(ln.get("tax_cents") or 0)
            rows.append([p(str(ln.get("description") or "-")), _money(g - tx, cur), _money(tx, cur), _money(g, cur)])
        rows += [
            ["Credit before tax", "", "", _money(note.subtotal_cents, cur)],
            [f"Tax reversed: {label}", "", "", _money(note.tax_cents, cur)],
            ["Total credit", "", "", _money(note.amount_cents, cur)],
        ]
        widths = [3.4 * inch, 1.1 * inch, 1.1 * inch, 1.2 * inch]
        summary_rows = 3
    else:
        rows = [["Description", "Amount"]]
        for ln in note.lines_json or []:
            rows.append([p(str(ln.get("description") or "-")), _money(int(ln.get("gross_cents") or 0), cur)])
        rows += [["Total credit", _money(note.amount_cents, cur)]]
        widths = [5.6 * inch, 1.2 * inch]
        summary_rows = 1
    t = Table(rows, colWidths=widths)
    n = len(rows)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, n - 1), (-1, n - 1), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, navy),
                ("LINEABOVE", (0, n - summary_rows), (-1, n - summary_rows), 0.6, navy),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story += [
        t,
        Spacer(1, 14),
        p(
            "Keep this credit note with your records. If you claimed an input tax credit for the "
            "original invoice, reduce it by the tax reversed shown above (Excise Tax Act s. 232)."
            if taxed
            else "Keep this credit note with your records.",
            small,
        ),
    ]
    if note.settlement == "credit_balance":
        story.append(p(f"{_money(note.settlement_cents, cur)} has been added to your account credit balance and will be applied to your next invoice.", small))
    elif note.settlement in ("stripe_refund", "stripe_refund_pending"):
        story.append(p(f"{_money(note.settlement_cents, cur)} is being refunded to your original payment card.", small))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, title=f"Credit note {note.credit_note_number}", author=legal, pageCompression=0,
        leftMargin=0.8 * inch, rightMargin=0.8 * inch, topMargin=0.8 * inch, bottomMargin=0.8 * inch,
    )
    doc.build(story)
    return buf.getvalue(), f"{note.credit_note_number}.pdf"

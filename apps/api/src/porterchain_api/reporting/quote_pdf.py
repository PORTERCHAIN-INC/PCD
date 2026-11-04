"""Quote PDF: same brand header/table style as the invoice PDF (order_documents).

Supplier legal name and GST/HST number come from the tax registration record in
force on the quote date. Pre-tax lines are listed; HST is printed once (doc 72).
Amounts are always server-computed: callers pass a stored Quote or a fresh preview.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from porterchain_api.reporting.order_documents import _issuer_from_db, _money

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "QUOTE", "doc": "Porterchain Quote", "quote_no": "Quote no.", "date": "Date",
        "valid": "Valid until", "currency": "Currency", "for": "Quote for", "route": "Route",
        "pickup": "Pickup", "dropoff": "Drop-off", "shipment": "Shipment", "vehicle": "Vehicle",
        "parcels": "Parcels", "desc": "Description", "amount": "Amount", "subtotal": "Subtotal (pre-tax)",
        "tax": "HST", "total": "Total", "reg": "GST/HST Reg. No.", "page": "Page",
        "note": "This is a quote, not an invoice. Prices in Canadian dollars (CAD). "
                "Final price may change if shipment details differ.",
        "weight": "weight", "dims": "dimensions", "package": "package",
    },
    "fr": {
        "title": "SOUMISSION", "doc": "Soumission Porterchain", "quote_no": "No de soumission",
        "date": "Date", "valid": "Valide jusqu'au", "currency": "Devise", "for": "Soumission pour",
        "route": "Trajet", "pickup": "Ramassage", "dropoff": "Livraison", "shipment": "Envoi",
        "vehicle": "Véhicule", "parcels": "Colis", "desc": "Description", "amount": "Montant",
        "subtotal": "Sous-total (avant taxes)", "tax": "TVH", "total": "Total",
        "reg": "No d'inscription TPS/TVH", "page": "Page",
        "note": "Ceci est une soumission, pas une facture. Prix en dollars canadiens (CAD). "
                "Le prix final peut changer si les détails de l'envoi diffèrent.",
        "weight": "poids", "dims": "dimensions", "package": "emballage",
    },
}


def norm_lang(lang: str | None) -> str:
    return "fr" if str(lang or "").lower().startswith("fr") else "en"


def _fr_money(cents: int | None, currency: str) -> str:
    return f"{(cents or 0) / 100:.2f}".replace(".", ",") + f" $ {(currency or 'cad').upper()}"


def split_lines(items: Sequence[dict[str, Any]] | None) -> tuple[list[dict[str, Any]], int | None]:
    """Pre-tax lines and the HST amount (None when no hst line)."""
    pre: list[dict[str, Any]] = []
    hst: int | None = None
    for it in items or []:
        if not isinstance(it, dict) or it.get("amount_cents") is None:
            continue
        if str(it.get("code") or "").lower() == "hst":
            hst = (hst or 0) + int(it.get("amount_cents") or 0)
        else:
            pre.append(it)
    return pre, hst


def preview_quote_number(seed: str, at: datetime) -> str:
    h = hashlib.sha256(f"{seed}|{at.isoformat()}".encode()).hexdigest()[:6].upper()
    return f"QP-{at.strftime('%Y%m%d')}-{h}"


def render_quote_pdf(
    db: Any,
    *,
    quote_number: str,
    issued_at: datetime,
    valid_until: datetime | None,
    party_lines: Sequence[str],
    pickup: str | None,
    dropoff: str | None,
    shipment_lines: Sequence[str],
    items: Sequence[dict[str, Any]] | None,
    total_cents: int,
    tax_cents: int | None = None,
    currency: str = "cad",
    lang: str | None = "en",
) -> bytes:
    import io
    from pathlib import Path

    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Spacer, Table, TableStyle

    from porterchain_api.merchant_engine.quote_snapshot import quote_line_label
    from porterchain_api.platform.tax_registration import registration_at

    L = LABELS[norm_lang(lang)]
    fr = norm_lang(lang) == "fr"
    money = (lambda c: _fr_money(c, currency)) if fr else (lambda c: _money(c, currency))
    _, legal_default, support_email = _issuer_from_db(db)
    reg = registration_at(db, issued_at)
    legal = reg.legal_name or legal_default

    pre, hst = split_lines(items)
    if hst is None and tax_cents:
        hst = int(tax_cents)
    hst = int(hst or 0)
    subtotal = int(total_cents) - hst

    navy, accent, muted = HexColor("#0a1628"), HexColor("#2563eb"), HexColor("#64748b")
    line_color, surface = HexColor("#e2e8f0"), HexColor("#f8fafc")
    page_w, page_h = letter
    mark = ImageReader(str(Path(__file__).resolve().parent / "brand" / "porterchain-mark-white.png"))
    mark_w = 36 * (298 / 267)

    def paint(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(navy)
        canvas.rect(0, page_h - 64, page_w, 64, fill=1, stroke=0)
        canvas.setFillColor(accent)
        canvas.rect(0, page_h - 68, page_w, 4, fill=1, stroke=0)
        canvas.drawImage(mark, 40, page_h - 50, width=mark_w, height=36, mask="auto",
                         preserveAspectRatio=True, anchor="sw")
        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(40 + mark_w + 8, page_h - 32, "porterchain")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40 + mark_w + 8, page_h - 46, legal[:72])
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(page_w - 48, page_h - 32, L["title"])
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(page_w - 48, page_h - 48, quote_number)
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(48, 28, f"{support_email} · {quote_number}")
        canvas.drawRightString(page_w - 48, 28, f"{L['page']} {doc.page}")
        canvas.restoreState()

    from reportlab.platypus.flowables import Flowable

    class Block(Flowable):
        def __init__(self, rows, size=10, leading=14, color=navy, bold_first=False):
            super().__init__()
            self.rows, self.size, self.leading, self.color, self.bold_first = list(rows), size, leading, color, bold_first
            self.height = leading * max(len(self.rows), 1)

        def wrap(self, aw, ah):
            return aw, self.height

        def draw(self):
            self.canv.setFillColor(self.color)
            y = self.height - self.size
            for i, row in enumerate(self.rows):
                self.canv.setFont("Helvetica-Bold" if (self.bold_first and i == 0) else "Helvetica", self.size)
                self.canv.drawString(0, y, str(row)[:110])
                y -= self.leading

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=letter, title=f"{L['doc']} {quote_number}", author=legal)
    doc.pageCompression = 0  # text stays greppable for tests/compliance checks
    doc.addPageTemplates([PageTemplate(id="quote", frames=[Frame(48, 46, page_w - 96, page_h - 114)], onPage=paint)])

    supplier = [legal]
    if reg.gst_hst_number:
        supplier.append(f"{L['reg']}: {reg.gst_hst_number}")
    fmt = (lambda d: d.astimezone(timezone.utc).date().isoformat() if d else "—")
    story: list[Any] = [Spacer(1, 8), Block(supplier, size=9, leading=13, bold_first=True), Spacer(1, 6),
        Block([f"{L['quote_no']}: {quote_number}", f"{L['date']}: {fmt(issued_at)}",
               f"{L['valid']}: {fmt(valid_until)}", f"{L['currency']}: {(currency or 'cad').upper()}"], size=9, leading=13),
        Spacer(1, 10), Block([L["for"]], size=8, leading=11, color=muted), Block(party_lines or ["—"]), Spacer(1, 8),
        Block([L["route"]], size=8, leading=11, color=muted),
        Block([f"{L['pickup']}: {pickup or '—'}", f"{L['dropoff']}: {dropoff or '—'}"], size=9, leading=12)]
    if shipment_lines:
        story += [Spacer(1, 8), Block([L["shipment"]], size=8, leading=11, color=muted), Block(shipment_lines, size=9, leading=12)]
    story.append(Spacer(1, 12))

    rows: list[list[str]] = [[L["desc"], L["amount"]]]
    for it in pre[:80]:
        code = it.get("code")
        rows.append([quote_line_label(str(code) if code is not None else None, it.get("label")) or "—",
                     money(int(it.get("amount_cents") or 0))])
    if len(rows) == 1:
        rows.append(["Delivery" if not fr else "Livraison", money(subtotal)])
    rows += [[L["subtotal"], money(subtotal)], [L["tax"], money(hst)], [L["total"], money(int(total_cents))]]
    n = len(rows)
    t = Table(rows, colWidths=[4.9 * inch, 1.7 * inch], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), surface), ("TEXTCOLOR", (0, 0), (-1, 0), muted),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), navy), ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, line_color), ("LINEABOVE", (0, n - 3), (-1, n - 3), 0.8, navy),
        ("FONTNAME", (0, n - 1), (-1, n - 1), "Helvetica-Bold"), ("BACKGROUND", (0, n - 1), (-1, n - 1), surface),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [t, Spacer(1, 14), Block(__import__("textwrap").wrap(L["note"], 100),
                                       size=8, leading=11, color=muted)]
    doc.build(story)
    return buf.getvalue()


def _num(v: Any) -> str:
    try:
        return f"{float(v):.1f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(v)


def _shipment_lines(L: dict[str, str], *, vehicle_class: str | None, package_type: str | None,
                    weight_kg: Any, dimensions: str | None, parcels: Any) -> list[str]:
    out: list[str] = []
    plist = parcels.get("items") if isinstance(parcels, dict) else parcels
    if isinstance(plist, list) and plist:
        for i, p in enumerate(plist[:20], 1):
            if not isinstance(p, dict):
                continue
            bits = [str(p.get("preset_label") or p.get("name") or p.get("size") or p.get("size_class") or "").strip()]
            if p.get("quantity") and int(p.get("quantity") or 1) > 1:
                bits.append(f"x{int(p['quantity'])}")
            if p.get("weight_kg") is not None:
                bits.append(f"{L['weight']} {_num(p['weight_kg'])} kg")
            cm = [p.get(k) for k in ("length_cm", "width_cm", "height_cm")]
            dims = p.get("dimensions") or (" x ".join(_num(v) for v in cm) + " cm" if all(cm) else None)
            if dims:
                bits.append(f"{L['dims']} {dims}")
            out.append(f"{L['parcels']} {i}: " + ", ".join(b for b in bits if b))
    whole = str(package_type or "").lower() in ("whole_vehicle", "vehicle")
    if vehicle_class and whole:
        out.append(f"{L['vehicle']}: {str(vehicle_class).replace('_', ' ')}")
    extra = []
    if package_type and not whole:
        extra.append(f"{L['package']} {package_type}")
    if weight_kg not in (None, ""):
        extra.append(f"{L['weight']} {weight_kg} kg")
    if dimensions:
        extra.append(f"{L['dims']} {dimensions}")
    if extra and not any(r.startswith(L["parcels"]) for r in out):
        out.append(f"{L['parcels']}: " + ", ".join(extra))
    return out


def pdf_for_stored_quote(db: Any, quote: Any, *, lang: str | None = "en") -> tuple[bytes, str]:
    """PDF for a persisted website/customer Quote row."""
    from porterchain_api.merchant_engine.quote_snapshot import flatten_quote_breakdown

    L = LABELS[norm_lang(lang)]
    flat = flatten_quote_breakdown(quote.pricing_breakdown)
    number = f"Q-{str(quote.id).replace('-', '')[:8].upper()}"
    cust = getattr(quote, "customer", None)
    party = [x for x in [getattr(cust, "name", None) or getattr(cust, "full_name", None),
                         getattr(cust, "email", None) or quote.email, quote.phone] if x] or ["—"]
    pdf = render_quote_pdf(
        db, quote_number=number, issued_at=quote.created_at or datetime.now(timezone.utc),
        valid_until=quote.expires_at, party_lines=party,
        pickup=(quote.pickup or {}).get("formatted"), dropoff=(quote.dropoff or {}).get("formatted"),
        shipment_lines=_shipment_lines(L, vehicle_class=quote.vehicle_class, package_type=quote.package_type,
                                       weight_kg=quote.weight_kg, dimensions=quote.dimensions, parcels=quote.parcels),
        items=flat.get("items"), total_cents=int(quote.amount_cents), tax_cents=flat.get("tax_cents"),
        currency=quote.currency or "cad", lang=lang,
    )
    return pdf, f"porterchain-quote-{number}.pdf"


def pdf_for_preview(
    db: Any, *, merchant: Any, pickup: str | None, dropoff: str | None, breakdown: dict[str, Any] | None,
    total_cents: int, currency: str = "cad", vehicle_class: str | None = None, package_type: str | None = None,
    weight_kg: Any = None, dimensions: str | None = None, parcels: Any = None, ttl_minutes: int = 72 * 60,
    lang: str | None = "en",
) -> tuple[bytes, str]:
    """PDF for a just-computed merchant preview (admin or merchant portal). Nothing stored."""
    from porterchain_api.merchant_engine.quote_snapshot import flatten_quote_breakdown

    L = LABELS[norm_lang(lang)]
    now = datetime.now(timezone.utc)
    number = preview_quote_number(f"{getattr(merchant, 'id', '')}|{pickup}|{dropoff}|{total_cents}", now)
    flat = flatten_quote_breakdown(breakdown)
    party = [x for x in [getattr(merchant, "legal_name", None) or getattr(merchant, "company_name", None),
                         getattr(merchant, "email", None) or getattr(merchant, "contact_email", None)] if x] or ["—"]
    pdf = render_quote_pdf(
        db, quote_number=number, issued_at=now, valid_until=now + timedelta(minutes=max(1, int(ttl_minutes))),
        party_lines=party, pickup=pickup, dropoff=dropoff,
        shipment_lines=_shipment_lines(L, vehicle_class=vehicle_class, package_type=package_type,
                                       weight_kg=weight_kg, dimensions=dimensions, parcels=parcels),
        items=flat.get("items"), total_cents=int(total_cents), tax_cents=flat.get("tax_cents"),
        currency=currency, lang=lang,
    )
    return pdf, f"porterchain-quote-{number}.pdf"

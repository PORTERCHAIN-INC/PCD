"""4×6 thermal PDF renderer (ReportLab) — one page per package."""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

LABEL_WIDTH = 4 * inch
LABEL_HEIGHT = 6 * inch


def _qr_image(payload: str, box_size: int = 6) -> ImageReader:
    import qrcode

    img = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=box_size, border=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def render_thermal_labels(pages: list[dict[str, Any]]) -> bytes:
    """
    Each page dict keys:
      route_hint, stop_sequence, from_line, to_line, order_number, tracking_base,
      cod_line, qr_payload, tracking_suffix, parcel_index, total_parcels
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    for page in pages:
        _draw_page(c, page)
        c.showPage()
    c.save()
    return buf.getvalue()


def _draw_page(c: canvas.Canvas, page: dict[str, Any]) -> None:
    margin = 0.2 * inch
    y = LABEL_HEIGHT - margin

    if page.get("is_sandbox"):
        c.saveState()
        c.setFillColorRGB(0.85, 0.1, 0.1)
        c.setFont("Helvetica-Bold", 48)
        c.translate(LABEL_WIDTH / 2, LABEL_HEIGHT / 2)
        c.rotate(35)
        c.drawCentredString(0, 12, "TEST")
        c.drawCentredString(0, -28, "TEST")
        c.restoreState()
        c.setFillColorRGB(0.75, 0.05, 0.05)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(LABEL_WIDTH / 2, LABEL_HEIGHT - margin - 2, "SANDBOX — NOT FOR DISPATCH")
        c.setFillColorRGB(0, 0, 0)

    c.setFont("Helvetica-Bold", 11)
    route = page.get("route_hint") or "—"
    stop = page.get("stop_sequence")
    stop_s = f"STOP #{stop}" if stop not in (None, "") else "STOP #—"
    c.drawString(margin, y - 12, "PorterChain")
    c.setFont("Helvetica", 9)
    c.drawRightString(LABEL_WIDTH - margin, y - 12, f"ROUTE {route}  ·  {stop_s}")
    y -= 28

    c.setStrokeColorRGB(0.15, 0.15, 0.15)
    c.line(margin, y, LABEL_WIDTH - margin, y)
    y -= 14

    c.setFont("Helvetica-Bold", 8)
    c.drawString(margin, y, "FROM")
    c.drawString(LABEL_WIDTH / 2, y, "TO")
    y -= 12
    c.setFont("Helvetica", 8)
    from_line = str(page.get("from_line") or "—")[:90]
    to_line = str(page.get("to_line") or "—")[:90]
    c.drawString(margin, y, from_line[:42])
    c.drawString(LABEL_WIDTH / 2, y, to_line[:42])
    y -= 11
    if len(from_line) > 42 or len(to_line) > 42:
        c.drawString(margin, y, from_line[42:84])
        c.drawString(LABEL_WIDTH / 2, y, to_line[42:84])
        y -= 11

    y -= 4
    c.line(margin, y, LABEL_WIDTH - margin, y)
    y -= 14

    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Order {page.get('order_number') or '—'}")
    y -= 12
    c.drawString(margin, y, f"Tracking {page.get('tracking_base') or '—'}")
    y -= 12
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, f"COD {page.get('cod_line') or '—'}")
    y -= 18

    qr_payload = str(page.get("qr_payload") or "")
    qr_size = 1.6 * inch
    if qr_payload:
        c.drawImage(
            _qr_image(qr_payload),
            (LABEL_WIDTH - qr_size) / 2,
            y - qr_size,
            width=qr_size,
            height=qr_size,
            mask="auto",
        )
    y = y - qr_size - 10

    c.setFont("Helvetica-Bold", 12)
    suffix = str(page.get("tracking_suffix") or "")
    c.drawCentredString(LABEL_WIDTH / 2, y, suffix)
    y -= 18

    c.setFont("Helvetica-Bold", 11)
    idx = page.get("parcel_index") or 1
    total = page.get("total_parcels") or 1
    c.drawCentredString(LABEL_WIDTH / 2, margin + 4, f"BOX {idx} of {total}")

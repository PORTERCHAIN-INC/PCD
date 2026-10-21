"""4×6 thermal PDF renderer (ReportLab) — one page per package.

Layout is computed first (``layout_page``) as a list of non-overlapping boxes,
then drawn. Every text run is measured with real font metrics and wrapped or
shrunk to fit its column, so nothing can run past the label edge or onto
another line. Tests assert on the layout boxes directly.

The bottom ``FOOTER_RESERVE`` of the label is intentionally left blank: some
merchant print stacks (e.g. warehouse print agents) stamp their own job / carton
reference there, and anything we draw in that strip gets overprinted.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import getAscent, getDescent, stringWidth
from reportlab.pdfgen import canvas

LABEL_WIDTH = 4 * inch
LABEL_HEIGHT = 6 * inch
MARGIN = 0.2 * inch
FOOTER_RESERVE = 0.45 * inch
QR_SIZE = 1.45 * inch
BAR_HEIGHT = 0.45 * inch
HRI_GAP = 5.0  # gap between bottom of bars and top of human-readable glyphs

EMPTY = {"", "—", "-", "none", "null"}


@dataclass(frozen=True)
class Box:
    kind: str  # "text" | "qr" | "barcode" | "rule"
    x0: float
    y0: float
    x1: float
    y1: float
    text: str = ""
    font: str = ""
    size: float = 0.0
    align: str = "left"  # left | right | center
    payload: str = ""
    bar_width: float = 0.0

    def overlaps(self, other: Box) -> bool:
        return (
            self.x0 < other.x1
            and other.x0 < self.x1
            and self.y0 < other.y1
            and other.y0 < self.y1
        )


def _present(value: Any) -> str:
    s = str(value if value is not None else "").strip()
    return "" if s.lower() in EMPTY else s


def _qr_image(payload: str, box_size: int = 6) -> ImageReader:
    import qrcode

    img = qrcode.make(
        payload,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=1,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _text_box(
    text: str,
    font: str,
    size: float,
    x: float,
    top: float,
    width: float,
    align: str = "left",
) -> Box:
    """One line of text whose glyph box (ascent..descent) starts at ``top``."""
    asc = getAscent(font, size)
    desc = -getDescent(font, size)
    w = stringWidth(text, font, size)
    if align == "right":
        x0 = x + width - w
    elif align == "center":
        x0 = x + (width - w) / 2
    else:
        x0 = x
    return Box(
        "text",
        x0,
        top - asc - desc,
        x0 + w,
        top,
        text=text,
        font=font,
        size=size,
        align=align,
    )


def _fit_lines(
    text: str, font: str, sizes: tuple[float, ...], width: float, max_lines: int
) -> tuple[list[str], float]:
    """Wrap ``text`` to ``width``; shrink through ``sizes`` until it fits ``max_lines``.

    At the smallest size, any remaining overflow is cut with an ellipsis on the
    last line (still measured, so it can never cross the column edge).
    """
    for size in sizes:
        lines = _wrap(text, font, size, width)
        if len(lines) <= max_lines:
            return lines, size
    size = sizes[-1]
    lines = _wrap(text, font, size, width)[:max_lines]
    last = lines[-1]
    while last and stringWidth(last + "…", font, size) > width:
        last = last[:-1]
    lines[-1] = last.rstrip(" ,") + "…"
    return lines, size


def _wrap(text: str, font: str, size: float, width: float) -> list[str]:
    out: list[str] = []
    for line in simpleSplit(text, font, size, width):
        # simpleSplit keeps an unbreakable token whole; hard-break it.
        while stringWidth(line, font, size) > width:
            cut = len(line)
            while cut > 1 and stringWidth(line[:cut], font, size) > width:
                cut -= 1
            out.append(line[:cut])
            line = line[cut:]
        out.append(line)
    return out or [""]


def _address_text(raw: str) -> str:
    """Drop repeated comma parts (formatted address + city + postal often duplicate)."""
    parts: list[str] = []
    seen = ""
    for part in (p.strip() for p in raw.split(",")):
        if not part:
            continue
        if part.lower() in seen.lower():
            continue
        parts.append(part)
        seen += " " + part
    return ", ".join(parts)


def _code128(value: str, usable: float):
    from reportlab.graphics.barcode.code128 import Code128

    bar = Code128(value, barHeight=BAR_HEIGHT, barWidth=0.9, humanReadable=False)
    if bar.width > usable:  # width already includes the 10-module quiet zones
        bar = Code128(
            value,
            barHeight=BAR_HEIGHT,
            barWidth=max(0.55, 0.9 * (usable / bar.width)),
            humanReadable=False,
        )
    return bar


def layout_page(page: dict[str, Any]) -> list[Box]:
    left = MARGIN
    right = LABEL_WIDTH - MARGIN
    width = right - left
    floor = MARGIN + FOOTER_RESERVE
    boxes: list[Box] = []
    y = LABEL_HEIGHT - MARGIN

    if page.get("is_sandbox"):
        b = _text_box(
            "SANDBOX — NOT FOR DISPATCH", "Helvetica-Bold", 10, left, y, width, "center"
        )
        boxes.append(b)
        y = b.y0 - 4

    # Header: brand left, route/stop right only when they carry information.
    route = _present(page.get("route_hint"))
    stop = _present(page.get("stop_sequence"))
    tags = []
    if route:
        tags.append(f"ROUTE {route}")
    if stop and (route or stop not in {"1", "0"}):
        tags.append(f"STOP #{stop}")
    brand = _text_box("PorterChain", "Helvetica-Bold", 12, left, y, width)
    boxes.append(brand)
    if tags:
        tag_w = right - (brand.x1 + 10)
        tag_lines, tag_size = _fit_lines(
            "  ·  ".join(tags), "Helvetica-Bold", (10, 9, 8, 7), tag_w, 1
        )
        boxes.append(
            _text_box(
                tag_lines[0],
                "Helvetica-Bold",
                tag_size,
                brand.x1 + 10,
                y,
                tag_w,
                "right",
            )
        )
    y = brand.y0 - 6
    boxes.append(Box("rule", left, y, right, y))
    y -= 6

    # FROM (small, max 2 lines) then TO (prominent, max 4 lines) — full width each.
    from_text = _present(page.get("from_line")) or "—"
    b = _text_box("FROM", "Helvetica-Bold", 7, left, y, width)
    boxes.append(b)
    y = b.y0 - 2
    lines, size = _fit_lines(from_text, "Helvetica", (8, 7), width, 2)
    for line in lines:
        b = _text_box(line, "Helvetica", size, left, y, width)
        boxes.append(b)
        y = b.y0 - 1
    y -= 5

    to_text = _address_text(_present(page.get("to_line")) or "—")
    b = _text_box("TO", "Helvetica-Bold", 8, left, y, width)
    boxes.append(b)
    y = b.y0 - 2
    lines, size = _fit_lines(to_text, "Helvetica-Bold", (12, 11, 10, 9, 8), width, 4)
    for line in lines:
        b = _text_box(line, "Helvetica-Bold", size, left, y, width)
        boxes.append(b)
        y = b.y0 - 1
    # Delivery options (leave at door, unit, buzzer…): right under the address, max 2 lines.
    delivery = _present(page.get("delivery_line"))
    if delivery:
        y -= 2
        lines, size = _fit_lines(delivery, "Helvetica-Bold", (8, 7), width, 2)
        for line in lines:
            b = _text_box(line, "Helvetica-Bold", size, left, y, width)
            boxes.append(b)
            y = b.y0 - 1
    y -= 5
    boxes.append(Box("rule", left, y, right, y))
    y -= 6

    for label, key, font in (
        ("Order", "order_number", "Helvetica"),
        ("Tracking", "tracking_base", "Helvetica"),
        ("COD", "cod_line", "Helvetica-Bold"),
    ):
        val = _present(page.get(key))
        if not val:
            continue
        lines, size = _fit_lines(f"{label} {val}", font, (9, 8, 7), width, 1)
        b = _text_box(lines[0], font, size, left, y, width)
        boxes.append(b)
        y = b.y0 - 3
    y -= 6

    qr_payload = str(page.get("qr_payload") or "")
    if qr_payload:
        x0 = (LABEL_WIDTH - QR_SIZE) / 2
        boxes.append(Box("qr", x0, y - QR_SIZE, x0 + QR_SIZE, y, payload=qr_payload))
        y -= QR_SIZE + 8

    suffix = str(page.get("tracking_suffix") or "")
    if suffix:
        bar = _code128(suffix, width)
        x0 = (LABEL_WIDTH - bar.width) / 2
        boxes.append(
            Box(
                "barcode",
                x0,
                y - bar.height,
                x0 + bar.width,
                y,
                payload=suffix,
                bar_width=bar.barWidth,
            )
        )
        y -= bar.height + HRI_GAP
        lines, size = _fit_lines(suffix, "Helvetica-Bold", (11, 10, 9, 8), width, 1)
        b = _text_box(lines[0], "Helvetica-Bold", size, left, y, width, "center")
        boxes.append(b)
        y = b.y0 - 8

    # One clear box count; item detail only when it adds information.
    idx = page.get("parcel_index") or 1
    total = page.get("total_parcels") or 1
    b = _text_box(
        f"BOX {idx} of {total}", "Helvetica-Bold", 14, left, y, width, "center"
    )
    boxes.append(b)
    y = b.y0 - 2
    item_line = _present(page.get("item_line"))
    if item_line and not item_line.lower().endswith(f"box {idx} of {total}"):
        lines, size = _fit_lines(item_line, "Helvetica", (9, 8), width, 1)
        b = _text_box(lines[0], "Helvetica", size, left, y, width, "center")
        boxes.append(b)
        y = b.y0

    if y < floor:  # pragma: no cover - guarded by tests with worst-case input
        raise ValueError("label_layout_overflow")
    return boxes


def render_thermal_labels(pages: list[dict[str, Any]]) -> bytes:
    """
    Each page dict keys:
      route_hint, stop_sequence, from_line, to_line, order_number, tracking_base,
      cod_line, qr_payload, tracking_suffix, parcel_index, total_parcels,
      item_line ("Item 2 · box 1 of 3" for multi-box items; never contents),
      delivery_line (optional: "Leave at door · Unit 4 · Buzz 1234" — delivery options)
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    for page in pages:
        _draw_page(c, page)
        c.showPage()
    c.save()
    return buf.getvalue()


def _draw_page(c: canvas.Canvas, page: dict[str, Any]) -> None:
    if page.get("is_sandbox"):
        c.saveState()
        c.setFillColorRGB(0.85, 0.1, 0.1)
        c.setFont("Helvetica-Bold", 48)
        c.translate(LABEL_WIDTH / 2, LABEL_HEIGHT / 2)
        c.rotate(35)
        c.drawCentredString(0, 12, "TEST")
        c.drawCentredString(0, -28, "TEST")
        c.restoreState()

    for box in layout_page(page):
        if box.kind == "rule":
            c.setStrokeColorRGB(0.15, 0.15, 0.15)
            c.line(box.x0, box.y0, box.x1, box.y1)
        elif box.kind == "qr":
            c.drawImage(
                _qr_image(box.payload),
                box.x0,
                box.y0,
                width=box.x1 - box.x0,
                height=box.y1 - box.y0,
                mask="auto",
            )
        elif box.kind == "barcode":
            _code128(box.payload, LABEL_WIDTH - 2 * MARGIN).drawOn(c, box.x0, box.y0)
        else:
            sandbox_banner = box.text.startswith("SANDBOX")
            c.setFillColorRGB(
                0.75, 0.05, 0.05
            ) if sandbox_banner else c.setFillColorRGB(0, 0, 0)
            c.setFont(box.font, box.size)
            baseline = box.y1 - getAscent(box.font, box.size)
            c.drawString(box.x0, baseline, box.text)
    c.setFillColorRGB(0, 0, 0)

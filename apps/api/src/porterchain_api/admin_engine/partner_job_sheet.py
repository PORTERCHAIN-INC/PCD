"""Partner job sheet (PDF) + email draft for a 3PL / LTL / FTL / warehouse leg.

The email is a draft only: it is stored on the leg and shown to the admin, who sends
it from their own mail client. Nothing here sends mail.
"""

from __future__ import annotations

import io
from typing import Any

MODE_LABEL = {"ltl": "LTL linehaul", "ftl": "FTL linehaul", "3pl": "3PL final mile", "warehouse": "Warehouse hold",
              "local": "Local van"}


def sheet_facts(order: Any, leg: Any, partner: Any | None) -> dict[str, Any]:
    pkgs = list(getattr(order, "packages", None) or [])
    kg = round(sum(float(p.weight_kg or 0) for p in pkgs), 1)

    def addr(side: Any) -> str:
        if not isinstance(side, dict):
            return "—"
        stops = side.get("stops")
        if isinstance(stops, list) and stops:
            return " / ".join(str(s.get("formatted") or "—") for s in stops if isinstance(s, dict))
        return str(side.get("formatted") or "—")

    return {
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "mode": MODE_LABEL.get(leg.mode, leg.mode.upper()),
        "partner": partner.name if partner is not None else "Unassigned partner",
        "from": leg.from_label or addr(order.pickup),
        "to": leg.to_label or addr(order.dropoff),
        "origin_address": addr(order.pickup),
        "destination_address": addr(order.dropoff),
        "boxes": len(pkgs) or 1,
        "kg": kg,
        "ready": order.scheduled_at.strftime("%a %b %d, %Y %H:%M") if order.scheduled_at else "—",
        "est_cost": f"${leg.est_cost_cents / 100:,.2f}" if leg.est_cost_cents else "per your rate card",
        "instructions": (order.special_instructions or "").strip() or "None",
        "leg": f"Leg {leg.seq + 1}",
    }


def render_pdf(f: dict[str, Any]) -> bytes:
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    navy = HexColor("#0B1B3F")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    w, h = LETTER
    c.setFillColor(navy)
    c.rect(0, h - 96, w, 96, stroke=0, fill=1)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(48, h - 52, "Porterchain · Partner job sheet")
    c.setFont("Helvetica", 11)
    c.drawString(48, h - 74, f"{f['mode']} · {f['leg']} · {f['partner']}")
    y = h - 140
    c.setFillColor(navy)
    rows = [
        ("Order", f["order_number"]), ("Tracking", f["tracking_number"]), ("From", f["from"]), ("To", f["to"]),
        ("Origin address", f["origin_address"]), ("Destination address", f["destination_address"]),
        ("Pieces", str(f["boxes"])), ("Weight", f"{f['kg']} kg"), ("Ready", f["ready"]),
        ("Agreed rate", f["est_cost"]), ("Instructions", f["instructions"]),
    ]
    for label, value in rows:
        c.setFont("Helvetica", 9)
        c.drawString(48, y, label.upper())
        c.setFont("Helvetica-Bold", 12)
        c.drawString(190, y, str(value)[:90])
        y -= 28
    c.setFont("Helvetica", 9)
    c.drawString(48, 60, "Reply to confirm acceptance and pickup time. Quote the order number on all paperwork.")
    c.showPage()
    c.save()
    return buf.getvalue()


def email_draft(f: dict[str, Any], to: str | None) -> dict[str, Any]:
    subject = f"Job request {f['order_number']} · {f['mode']} · {f['from']} → {f['to']}"
    body = "\n".join([
        "Hi team,",
        "",
        f"Please confirm you can take the {f['mode']} leg below.",
        "",
        f"Order: {f['order_number']} (tracking {f['tracking_number']})",
        f"From: {f['from']}",
        f"To: {f['to']}",
        f"Pieces: {f['boxes']} · Weight: {f['kg']} kg",
        f"Ready: {f['ready']}",
        f"Rate: {f['est_cost']}",
        f"Instructions: {f['instructions']}",
        "",
        "The job sheet PDF is attached. Reply to accept and give a pickup time.",
        "",
        "Thanks,",
        "Porterchain Dispatch",
    ])
    return {"to": to, "subject": subject, "body": body, "attachment": f"job-sheet-{f['order_number']}.pdf",
            "status": "draft — not sent"}

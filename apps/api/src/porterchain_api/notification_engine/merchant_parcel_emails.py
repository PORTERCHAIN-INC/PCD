"""Merchant (business) copies of the pickup and delivered emails.

The merchant is told who picked the parcel up (driver's name only, never phone or
email), where it is going, and gets one button to the order in the merchant portal,
where the label, timeline and proof of delivery live.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.notification_engine.email_layout import build_transactional_html

MERCHANT_PARCEL_TEMPLATES = frozenset({"parcel_picked_up", "delivered"})


def is_merchant_parcel_email(template: str, context: dict[str, Any]) -> bool:
    return (
        template in MERCHANT_PARCEL_TEMPLATES
        and context.get("audience") == "business"
        and context.get("recipient_role") == "merchant"
        and not context.get("copy_subject")
        and not context.get("copy_intro")
    )


def _g(ctx: dict[str, Any], key: str) -> str:
    value = ctx.get(key)
    return "" if value is None else str(value).strip()


def render_merchant_parcel_email(template: str, ctx: dict[str, Any]) -> tuple[str, str, str]:
    order = _g(ctx, "order_number")
    tracking = _g(ctx, "tracking_number")
    driver = _g(ctx, "driver_name")
    pickup = _g(ctx, "pickup_address")
    dropoff = _g(ctx, "dropoff_address")
    order_url = _g(ctx, "merchant_order_url")
    track_url = _g(ctx, "public_track_url")
    ref = tracking or order

    if template == "parcel_picked_up":
        eyebrow = "Picked up"
        subject = f"Picked up · {ref}" if ref else "Parcel picked up"
        headline = "Your parcel has been picked up"
        lead = (
            f"{driver} picked up order {order} and it is on its way."
            if driver
            else f"Order {order} was picked up and is on its way."
        )
        cta_label = "View order" if order_url else ("Track this shipment" if track_url else "")
        note = "We'll email you again when it is delivered."
    else:
        eyebrow = "Delivered"
        subject = f"Delivered · {ref}" if ref else "Delivered"
        headline = "Your shipment was delivered"
        lead = (
            f"{driver} delivered order {order}."
            if driver
            else f"Order {order} was delivered."
        )
        cta_label = "View proof of delivery" if order_url else ("Track this shipment" if track_url else "")
        note = "Photo and signature proof are saved on the order in your merchant portal."

    cta_url = order_url or track_url
    rows = [
        ("Order", order),
        ("Tracking", tracking),
        ("Driver", driver),
        ("From", pickup),
        ("To", dropoff),
    ]
    lines = [headline, "", lead, ""]
    lines += [f"{label}: {value}" for label, value in rows if value]
    if order_url:
        lines += ["", f"{cta_label}: {order_url}"]
    if track_url:
        lines += [f"Public tracking: {track_url}"]
    lines += ["", note]
    text = "\n".join(lines).strip()
    html = build_transactional_html(
        eyebrow=eyebrow,
        headline=headline,
        lead=lead,
        rows=rows,
        cta_label=cta_label,
        cta_url=cta_url,
        note=note,
        preheader=f"{headline} · {ref}" if ref else headline,
    )
    return subject, text, html

"""Instant quote for a lead — the real PricingService, at postal-area (FSA) level.

Retail leads → ``calculate_retail``; leads linked to a merchant account →
``calculate_merchant`` (their contract / FSA rates). Nothing is stored here.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from porterchain_api.lead_desk.fit_score import lead_fsa

DEFAULT_VEHICLE = "cargo_van"
_VEHICLE_LABELS = {
    "sedan_suv": "car / SUV",
    "cargo_van": "cargo van",
    "box_16": "16 ft box truck",
}


class QuoteUnavailable(ValueError):
    """The lead lacks what pricing needs (reason is the message)."""


def _inputs(lead: Any) -> dict[str, Any]:
    cf = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    pickup = lead_fsa(lead)
    drop_raw = (
        str(cf.get("dropoff_fsa") or "").strip().upper().replace(" ", "")[:3] or None
    )
    try:
        parcels = max(1, int(cf.get("parcel_count") or 1))
    except (TypeError, ValueError):
        parcels = 1
    vehicle = (
        (lead.preferred_vehicle or cf.get("vehicle_class") or DEFAULT_VEHICLE)
        .strip()
        .lower()
    )
    merchant_id = cf.get("merchant_id") or None
    return {
        "pickup_fsa": pickup,
        "dropoff_fsa": drop_raw or pickup,
        "parcel_count": parcels,
        "vehicle_class": vehicle,
        "merchant_id": merchant_id,
    }


def booking_url(
    website_url: str, lead: Any, vehicle: str, *, locale: str = "en"
) -> str:
    q = {
        "vehicle": vehicle,
        "utm_source": "crm",
        "utm_medium": "lead_quote",
        "utm_campaign": "instant_quote",
        "pc_lead": lead.id,
    }
    return f"{(website_url or 'https://porterchain.com').rstrip('/')}/{locale}/book?{urlencode(q)}"


def lead_quote(db: Session, lead: Any, *, website_url: str) -> dict[str, Any]:
    from porterchain_api.marketing_site.fsa_geo import fsa_centroid
    from porterchain_api.pricing_engine import get_pricing_service
    from porterchain_api.pricing_engine.quote_bridge import _request_from_quote_body
    from porterchain_api.schemas_booking import AddressInput, CreateQuoteRequest

    inp = _inputs(lead)
    if not inp["pickup_fsa"]:
        raise QuoteUnavailable("no_postal_code")
    a = fsa_centroid(inp["pickup_fsa"])
    b = fsa_centroid(inp["dropoff_fsa"])
    if not a or not b:
        raise QuoteUnavailable("outside_service_area")

    def addr(c: tuple[str, float, float]) -> AddressInput:
        return AddressInput(
            formatted=f"{c[0]}, Ontario, Canada", postal=c[0], lat=c[1], lng=c[2]
        )

    body = CreateQuoteRequest(
        pickup=addr(a),
        dropoff=addr(b),
        vehicle_class=inp["vehicle_class"],
        booking_mode="vehicle",
        scheduled_at=datetime.now(UTC) + timedelta(hours=2),
        schedule_mode="later",
    )
    merchant = bool(inp["merchant_id"])
    request = _request_from_quote_body(
        body,
        channel="merchant" if merchant else "retail",
        merchant_id=inp["merchant_id"],
        parcel_count=inp["parcel_count"],
    )
    service = get_pricing_service(db)
    breakdown = (
        service.calculate_merchant(request)
        if merchant
        else service.calculate_retail(request)
    )
    total = int(breakdown.final_cents)
    vehicle = request.vehicle_class
    km = breakdown.metadata.get("distance_meters")
    lines = [
        {"label": i.label, "amount_cents": int(i.amount_cents)} for i in breakdown.items
    ]
    return {
        "amount_cents": total,
        "amount_display": f"${total / 100:,.2f}",
        "currency": "CAD",
        "pricing": "merchant" if merchant else "retail",
        "vehicle_class": vehicle,
        "vehicle_label": _VEHICLE_LABELS.get(vehicle, vehicle.replace("_", " ")),
        "pickup_fsa": a[0],
        "dropoff_fsa": b[0],
        "parcel_count": inp["parcel_count"],
        "distance_km": round(km / 1000, 1) if km else None,
        "lines": lines,
        "tax_cents": max(0, total - sum(line["amount_cents"] for line in lines)),
        "basis": "fsa_centroid",
        "booking_url": booking_url(website_url, lead, vehicle),
        "note": "Postal-area estimate; exact addresses confirm the final price at booking.",
    }

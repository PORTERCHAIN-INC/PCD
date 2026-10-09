"""Instant price for the website calculator — the real retail quote preview.

Postal-code level only: both ends are the FSA centroids from the pricing
registry, so no address (PII) is needed. Nothing is stored.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.config import Settings
from porterchain_api.marketing_site.fsa_geo import fsa_centroid
from porterchain_api.marketing_site.schemas import CALCULATOR_VEHICLES
from porterchain_api.schemas_booking import AddressInput, CreateQuoteRequest

DISCLAIMER = (
    "Estimate between postal-area centres for a whole-vehicle booking, including HST. "
    "Your final price is confirmed with exact addresses before you pay."
)

_quotes = QuoteService()


def _address(code: str, lat: float, lng: float) -> AddressInput:
    return AddressInput(formatted=f"{code}, Ontario, Canada", postal=code, lat=lat, lng=lng)


def estimate_price(
    db: Session, settings: Settings, *, pickup: str, dropoff: str, vehicle_class: str
) -> dict[str, Any]:
    vehicle = (vehicle_class or "").strip().lower()
    if vehicle not in CALCULATOR_VEHICLES:
        raise ValueError("vehicle_class_not_available")
    a = fsa_centroid(pickup)
    if not a:
        raise ValueError("pickup_outside_service_area")
    b = fsa_centroid(dropoff)
    if not b:
        raise ValueError("dropoff_outside_service_area")
    body = CreateQuoteRequest(
        pickup=_address(*a),
        dropoff=_address(*b),
        vehicle_class=vehicle,
        booking_mode="vehicle",
        scheduled_at=datetime.now(UTC) + timedelta(hours=1),
    )
    preview = _quotes.preview_quote(db, settings, body)
    lines = [
        {"code": str(i.get("code")), "label": str(i.get("label")), "amount_cents": int(i.get("amount_cents") or 0)}
        for i in preview.get("pricing_breakdown") or []
    ]
    total = int(preview["amount_cents"])
    subtotal = sum(line["amount_cents"] for line in lines)
    tax = max(0, total - subtotal) if lines else 0
    return {
        "amount_cents": total,
        "amount_display": preview.get("amount_display") or f"${total / 100:.2f} CAD",
        "subtotal_cents": subtotal if lines else total,
        "tax_cents": tax,
        "currency": "CAD",
        "distance_km": preview.get("distance_km"),
        "included_km": preview.get("included_km"),
        "vehicle_class": preview.get("vehicle_class") or vehicle,
        "pickup_fsa": a[0],
        "dropoff_fsa": b[0],
        "lines": lines,
        "basis": "fsa_centroid",
        "disclaimer": DISCLAIMER,
    }

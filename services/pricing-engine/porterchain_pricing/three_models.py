"""Ravi 2026-10-31: the only three pricing models (all prices before HST).

1. Parcel (default, merchants and customers): each parcel $6 if it fits 20 x 14 x 14 in
   (largest side <= 20, other two <= 14), otherwise $9 (van parcel), plus one handling
   surcharge from the size/weight table below. The higher of weight and footprint decides;
   tiers do not stack. Over Tier 2 = custom quote.
2. Vehicle hourly (merchants only): rate by vehicle x max(3, hours); hours run from arrival at
   pickup to the last drop (quoted from the route estimate, 15-min steps). +$30 per stop
   (pickup or drop) where load/unload help is requested.
3. Merchant custom price set by admin: handled by the caller (it overrides 1 and 2).
"""

from __future__ import annotations

import math
from typing import Any

from porterchain_pricing.types import PriceBreakdown, PriceLineItem, PricingRequest

SMALL_CENTS = 600
VAN_CENTS = 900
SMALL_MAX_IN = (20.0, 14.0, 14.0)
_IN_CM = 2.54
_LB_KG = 2.20462

# (tier, label, max_lb, max_long_in, max_short_in, surcharge_cents) -- footprint = two longest sides.
HANDLING_TIERS: tuple[tuple[int, str, float, float, float, int], ...] = (
    (0, "Standard", 100, 70, 45, 0),
    (1, "Handling tier 1", 125, 80, 45, 3000),
    (2, "Handling tier 2", 150, 90, 50, 6000),
)

HOURLY_MIN_HOURS = 3.0
HELP_PER_STOP_CENTS = 3000
# Sedan/SUV/pickup $40/h; cargo or small van $60/h; biggest van (16 ft+, box, large cube) $70/h.
HOURLY_RATES: dict[str, int] = {
    "sedan_suv": 4000, "sedan": 4000, "suv": 4000, "car": 4000, "pickup": 4000, "pickup_truck": 4000,
    "cargo_van": 6000, "van": 6000, "small_van": 6000, "minivan": 6000, "sprinter_van": 6000,
    "box_truck": 7000, "box_16": 7000, "box_20": 7000, "cube_van": 7000, "truck_16ft": 7000,
}
HOURLY_LABELS = {4000: "Sedan / SUV / pickup", 6000: "Cargo van", 7000: "16 ft+ box / cube van"}


class CustomQuote(ValueError):
    pass


def _dims_in(dimensions: Any) -> list[float]:
    from porterchain_pricing.components.size_weight import parse_dimensions_cm

    return sorted((d / _IN_CM for d in parse_dimensions_cm(dimensions) if d), reverse=True)


def fits_small(dimensions: Any) -> bool:
    sides = _dims_in(dimensions)
    if not sides:
        return True  # no size given: small parcel
    sides = (sides + [0.0, 0.0])[:3]
    return all(s <= lim + 1e-6 for s, lim in zip(sides, SMALL_MAX_IN))


def handling_tier(weight_kg: float | None, dimensions: Any) -> tuple[int, str, int]:
    """Higher of the weight tier and the footprint tier. Raises CustomQuote above Tier 2."""
    lb = float(weight_kg or 0) * _LB_KG
    sides = (_dims_in(dimensions) + [0.0, 0.0])[:2]
    by_w = by_s = None
    for tier, _label, max_lb, max_long, max_short, _c in HANDLING_TIERS:
        if by_w is None and lb <= max_lb + 1e-6:
            by_w = tier
        if by_s is None and sides[0] <= max_long + 1e-6 and sides[1] <= max_short + 1e-6:
            by_s = tier
    if by_w is None or by_s is None:
        raise CustomQuote("over_handling_tier_2")
    t = HANDLING_TIERS[max(by_w, by_s)]
    return t[0], t[1], t[5]


def _parcels(request: PricingRequest) -> list[tuple[float | None, Any]]:
    if request.parcels:
        return [(p.weight_kg, p.dimensions) for p in request.parcels]
    n = max(1, int(request.parcel_count or 1))
    per = (request.weight_kg / n) if request.weight_kg else None
    return [(per, request.dimensions)] * n


def _custom(reason: str, model: str) -> PriceBreakdown:
    return PriceBreakdown(metadata={
        "pricing": model, "manual_quote": True, "manual_reason": reason,
        "fsa_refused": True, "custom_quote": True, "custom_quote_reason": reason,
    })


def parcel_price(request: PricingRequest) -> PriceBreakdown:
    small = van = 0
    surcharges: dict[str, list[int]] = {}
    try:
        for weight, dims in _parcels(request):
            tier, label, cents = handling_tier(weight, dims)
            if fits_small(dims) and tier == 0:
                small += 1
            else:
                van += 1
            if cents:
                surcharges.setdefault(label, []).append(cents)
    except CustomQuote:
        return _custom("over 150 lb or over 90 x 50 in", "parcel_v2")
    items = []
    if small:
        items.append(PriceLineItem(code="small_parcel", label=f"Small parcel x{small} ($6 each)", amount_cents=small * SMALL_CENTS))
    if van:
        items.append(PriceLineItem(code="van_parcel", label=f"Van parcel x{van} ($9 each)", amount_cents=van * VAN_CENTS))
    for label, cs in surcharges.items():
        items.append(PriceLineItem(code="handling", label=f"{label} x{len(cs)} (+${cs[0] // 100} each)", amount_cents=sum(cs)))
    bd = PriceBreakdown(items=items, currency="CAD", metadata={
        "pricing": "parcel_v2", "price_rule": "parcel_6_9", "small_parcels": small, "van_parcels": van,
    })
    bd.finalize()
    bd.base_cents = bd.subtotal_cents
    return bd


def hourly_rate_cents(vehicle_class: str | None) -> int | None:
    key = (vehicle_class or "").strip().lower().replace("-", "_").replace(" ", "_")
    return HOURLY_RATES.get(key)


def billable_hours(request: PricingRequest) -> float:
    if request.dedicated_hours:
        raw = float(request.dedicated_hours)
    else:
        raw = float(request.estimated_duration_minutes or 0) / 60.0
    return max(HOURLY_MIN_HOURS, math.ceil(raw * 4 - 1e-9) / 4)


def hourly_price(request: PricingRequest) -> PriceBreakdown:
    rate = hourly_rate_cents(request.vehicle_class)
    if rate is None:
        return _custom(f"No hourly rate for vehicle '{request.vehicle_class}'", "vehicle_hourly")
    hours = billable_hours(request)
    items = [PriceLineItem(code="vehicle_hourly", label=f"{HOURLY_LABELS[rate]} {hours:g} h x ${rate // 100}/h (3 h minimum)",
                           amount_cents=int(round(rate * hours)))]
    help_stops = max(0, int(request.help_stops or 0))
    if help_stops:
        items.append(PriceLineItem(code="load_help", label=f"Load/unload help x{help_stops} stops ($30 each)",
                                   amount_cents=help_stops * HELP_PER_STOP_CENTS))
    bd = PriceBreakdown(items=items, currency="CAD", metadata={
        "pricing": "vehicle_hourly", "price_rule": "vehicle_hourly", "hours": hours, "rate_cents": rate,
        "help_stops": help_stops,
    })
    bd.finalize()
    bd.base_cents = bd.subtotal_cents
    return bd

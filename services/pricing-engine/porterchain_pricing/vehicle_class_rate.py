"""Per-vehicle-class rates (vehicle-pricing-proposal.md §5, approved by Ravi 2026-10-31).

price (before HST) = base + max(0, km - 10) x per_km; the base covers the first 10 km and is
the minimum charge. ``sedan_suv`` is one catalog id today, so it uses the Sedan row.
"""

from __future__ import annotations

from porterchain_pricing.distance import total_route_meters
from porterchain_pricing.types import PricingRequest

INCLUDED_KM = 10.0

#: catalog id -> (base cents for the first 10 km, cents per km after that)
CLASS_RATES: dict[str, tuple[int, int]] = {
    "sedan": (2500, 110),
    "sedan_suv": (2500, 110),
    "suv": (3200, 135),
    "pickup": (4500, 175),
    "cargo_van": (5500, 200),
    "sprinter_van": (7500, 240),
    "sprinter": (7500, 240),
    "box_16": (12000, 300),
    "box_20": (15000, 350),
}

ALIASES = {"sedansuv": "sedan_suv", "cargovan": "cargo_van", "van": "cargo_van", "sprintervan": "sprinter_van"}


def class_id(vehicle_class: str | None) -> str | None:
    key = (vehicle_class or "").strip().lower().replace("-", "_")
    key = ALIASES.get(key.replace("_", ""), key)
    return key if key in CLASS_RATES else None


def route_km(request: PricingRequest) -> float:
    meters = request.distance_meters
    if meters is None:
        meters = total_route_meters(request.pickup, request.dropoff, list(request.additional_stops or []))
    return max(0.0, float(meters or 0) / 1000.0)


def class_rate_cents(vehicle_class: str | None, km: float) -> int | None:
    cid = class_id(vehicle_class)
    if cid is None:
        return None
    base, per_km = CLASS_RATES[cid]
    return int(round(base + max(0.0, km - INCLUDED_KM) * per_km))


# Ravi 2026-10-31 correction (replaces the class-rate floor for parcel quotes):
# small parcel minimum $6, van minimum $9. Small = fits 20 x 14 x 14 in, with the largest
# side compared to 20 and the other two to 14. Anything larger is priced as van.
SMALL_PARCEL_MIN_CENTS = 600
VAN_MIN_CENTS = 900
_IN_CM = 2.54
SMALL_MAX_IN = (20.0, 14.0, 14.0)


def _fits_small(dimensions) -> bool:
    from porterchain_pricing.components.size_weight import parse_dimensions_cm

    dims = [d for d in parse_dimensions_cm(dimensions) if d is not None]
    if not dims:
        return True  # no size given: standard parcel
    sides = sorted((d / _IN_CM for d in dims), reverse=True) + [0.0, 0.0]
    return all(s <= lim + 1e-6 for s, lim in zip(sides[:3], SMALL_MAX_IN))


def is_small_parcel(request: PricingRequest) -> bool:
    parcels = list(getattr(request, "parcels", None) or [])
    if parcels:
        return all(_fits_small(p.dimensions) for p in parcels)
    return _fits_small(request.dimensions)


def parcel_minimum_cents(request: PricingRequest) -> tuple[int, str]:
    if is_small_parcel(request):
        return SMALL_PARCEL_MIN_CENTS, "small_parcel"
    return VAN_MIN_CENTS, "van"

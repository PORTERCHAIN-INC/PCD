"""Fuel / km scorecard for optimize plans — uses pricing_fuel × plan distance.

Does not invent routes. Estimates liters from class L/100km defaults and
``FuelConfig.current_fuel_price_cents``. Valhalla right-turn bias lives in
MapsService costing; this module only measures dollars/liters after the plan.
"""

from __future__ import annotations

import re
from typing import Any

from porterchain_pricing.types import FuelConfig

# Rough GTA urban duty-cycle defaults (L/100km). Product can override later via settings.
_L_PER_100KM: dict[str, float] = {
    "sedan": 9.0,
    "suv": 11.0,
    "sedan_suv": 10.0,
    "pickup": 13.0,
    "cargo_van": 12.5,
    "cargovan": 12.5,
    "sprinter_van": 14.0,
    "sprintvan": 14.0,
    "box_truck": 22.0,
    "boxtruck": 22.0,
    "box_16": 22.0,
    "box_20": 24.0,
    "straight_truck": 24.0,
    "truck": 22.0,
}
_DEFAULT_L_PER_100KM = 12.5


def _normalize_class(vehicle_class: str | None) -> str:
    raw = (vehicle_class or "").strip()
    if not raw:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    return spaced.lower().replace("-", "_").replace(" ", "_")


def liters_per_100km_for_class(vehicle_class: str | None) -> float:
    key = _normalize_class(vehicle_class)
    if not key:
        return _DEFAULT_L_PER_100KM
    if key in _L_PER_100KM:
        return _L_PER_100KM[key]
    if key.endswith("_truck") or "truck" in key:
        return _L_PER_100KM["box_truck"]
    if "van" in key:
        return _L_PER_100KM["cargo_van"]
    return _DEFAULT_L_PER_100KM


def fuel_scorecard(
    *,
    distance_km: float,
    fuel_price_cents_per_liter: int,
    liters_per_100km: float,
) -> dict[str, Any]:
    km = max(0.0, float(distance_km or 0.0))
    price = max(0, int(fuel_price_cents_per_liter or 0))
    l100 = max(0.1, float(liters_per_100km or _DEFAULT_L_PER_100KM))
    liters = km * l100 / 100.0
    cents = int(round(liters * price))
    return {
        "estimated_fuel_liters": round(liters, 2),
        "estimated_fuel_cents": cents,
        "liters_per_100km": l100,
        "fuel_price_cents_per_liter": price,
        "cents_per_km": round(cents / km, 2) if km > 0 else None,
    }


def enrich_optimize_metrics_fuel(
    metrics: dict[str, Any] | None,
    *,
    fuel: FuelConfig | None = None,
    vehicle_class: str | None = None,
) -> dict[str, Any]:
    """Attach fuel scorecard fields onto Fleetbase optimize metrics."""
    base = dict(metrics or {})
    cfg = fuel or FuelConfig()
    km = float(base.get("after_distance_km") or 0.0)
    if km <= 0 and base.get("after_distance_m") is not None:
        try:
            km = float(base["after_distance_m"]) / 1000.0
            base.setdefault("after_distance_km", round(km, 2))
        except (TypeError, ValueError):
            km = 0.0
    l100 = liters_per_100km_for_class(vehicle_class)
    card = fuel_scorecard(
        distance_km=km,
        fuel_price_cents_per_liter=int(cfg.current_fuel_price_cents),
        liters_per_100km=l100,
    )
    out = {**base, **card, "fuel_vehicle_class": vehicle_class or "cargo_van"}

    before_km = base.get("before_distance_km")
    if before_km is not None:
        try:
            bkm = float(before_km)
        except (TypeError, ValueError):
            bkm = None
        if bkm is not None:
            before = fuel_scorecard(
                distance_km=bkm,
                fuel_price_cents_per_liter=int(cfg.current_fuel_price_cents),
                liters_per_100km=l100,
            )
            out["before_estimated_fuel_liters"] = before["estimated_fuel_liters"]
            out["before_estimated_fuel_cents"] = before["estimated_fuel_cents"]
            out["fuel_delta_cents"] = int(before["estimated_fuel_cents"]) - int(
                card["estimated_fuel_cents"]
            )
            out["distance_delta_km"] = round(bkm - km, 2)
    return out


def fuel_delta(
    *,
    before_km: float,
    after_km: float,
    fuel: FuelConfig | None = None,
    vehicle_class: str | None = None,
) -> dict[str, Any]:
    """Compare estimated fuel before vs after a plan (NIM / UI)."""
    cfg = fuel or FuelConfig()
    l100 = liters_per_100km_for_class(vehicle_class)
    before = fuel_scorecard(
        distance_km=before_km,
        fuel_price_cents_per_liter=int(cfg.current_fuel_price_cents),
        liters_per_100km=l100,
    )
    after = fuel_scorecard(
        distance_km=after_km,
        fuel_price_cents_per_liter=int(cfg.current_fuel_price_cents),
        liters_per_100km=l100,
    )
    return {
        "before_km": round(float(before_km), 2),
        "after_km": round(float(after_km), 2),
        "distance_delta_km": round(float(before_km) - float(after_km), 2),
        "before": before,
        "after": after,
        "fuel_delta_cents": int(before["estimated_fuel_cents"])
        - int(after["estimated_fuel_cents"]),
        "fuel_delta_liters": round(
            float(before["estimated_fuel_liters"]) - float(after["estimated_fuel_liters"]),
            2,
        ),
        "liters_per_100km": l100,
        "vehicle_class": vehicle_class or "cargo_van",
        "note": (
            "Estimate only (pricing_fuel × L/100km). "
            "Valhalla right-turn bias is in matrix costing, not a PC left-turn ban."
        ),
    }

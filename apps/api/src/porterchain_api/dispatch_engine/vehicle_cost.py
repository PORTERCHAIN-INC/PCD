"""Planner vehicle cost from the shared pricing margin estimates (one source of truth).

Settings key ``pricing_margin_estimates`` (Pricing → margin estimates) carries the driver
hourly rate, the per-km vehicle cost and monthly insurance per vehicle class. The planner
charges each vehicle: driver hourly + its insurance share per working hour, plus per-km.
A fleet row's own ``cost_per_km_cents`` (> 0) overrides the shared per-km figure.
"""

from __future__ import annotations

from typing import Any

# Fleet class → pricing vehicle key (pricing uses rate-card names).
PRICING_KEY = {"sedan": "sedan_suv", "suv": "sedan_suv", "van": "cargo_van", "box_truck": "box_16"}


def load_estimates(db: Any) -> dict[str, Any]:
    """The shared ``pricing_margin_estimates`` setting, validated the same way Settings saves it."""
    from porterchain_api.admin_models import SystemConfig
    from porterchain_pricing.margin import normalize_margin_estimates

    row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_margin_estimates").first()
    try:
        return normalize_margin_estimates(row.value if row else None)
    except ValueError:
        return normalize_margin_estimates(None)


def insurance_per_hour_cents(estimates: dict[str, Any], vehicle_class: str) -> float:
    table = estimates.get("insurance_monthly_cents") or {}
    monthly = int(table.get(vehicle_class, table.get(PRICING_KEY.get(vehicle_class, ""), 0)))
    hours = float(estimates.get("working_days_per_month") or 22) * float(estimates.get("working_hours_per_day") or 10)
    return monthly / hours if hours > 0 else 0.0


def per_class(table: Any, vehicle_class: str) -> int | None:
    """Look a class up in a per-vehicle table (fleet id first, then the pricing key)."""
    if not isinstance(table, dict):
        return None
    for key in (vehicle_class, PRICING_KEY.get(vehicle_class, "")):
        if key in table and table[key] is not None:
            return int(table[key])
    return None


def km_cents(estimates: dict[str, Any], vehicle_class: str) -> int:
    """Per-km cost: the per-vehicle table when the shared settings carry one, else the flat figure."""
    flat = estimates.get("vehicle_cents_per_km")
    for table in (estimates.get("vehicle_cents_per_km_by_vehicle"), flat):
        if (v := per_class(table, vehicle_class)) is not None:
            return v
    return int(flat or 0) if not isinstance(flat, dict) else 0


def vehicle_costs(estimates: dict[str, Any], spec: dict[str, Any]) -> tuple[int, int]:
    """``(hourly_cents, km_cents)`` for one fleet vehicle class."""
    hourly = int(estimates.get("driver_hourly_cents") or 2700) + insurance_per_hour_cents(estimates, spec["id"])
    km = int(spec.get("cost_per_km_cents") or 0) or km_cents(estimates, spec["id"])
    return round(hourly), km

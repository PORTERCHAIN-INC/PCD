"""Margin guard + distance sanity check — pure, no I/O.

estimate_cost(): driver time at the hourly rate (drive + stop handling, plus a
return-deadhead share) + per-km vehicle cost. margin_check() compares a price
against it and returns ok / thin / below_cost. distance_outlier() flags the
0 km-style bugs (road distance far below straight-line, or implausibly far
above it). Defaults are explicit assumptions and overridable per call.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

DEFAULTS: dict[str, Any] = {
    "driver_hourly_cents": 2700,      # decided: $27/h
    "avg_speed_kmh": 40.0,            # when no routed duration
    "pickup_minutes": 10.0,
    "drop_minutes": 8.0,
    "deadhead_factor": 0.5,           # half the return leg counted
    "vehicle_cents_per_km": 35,       # fuel + wear
    "thin_margin_pct": 15.0,          # warn below this margin
    "working_days_per_month": 22,     # insurance spread
    "working_hours_per_day": 10,      # insurance spread
}

#: Fixed insurance per vehicle type, cents per month (Ravi: van $600; others editable).
DEFAULT_INSURANCE: dict[str, int] = {
    "sedan_suv": 0,
    "pickup": 0,
    "cargo_van": 60000,
    "sprinter_van": 60000,
    "box_16": 0,
    "box_20": 0,
}


@dataclass(frozen=True)
class MarginResult:
    status: str             # ok | thin | below_cost
    price_cents: int
    cost_cents: int
    margin_cents: int
    margin_pct: float
    driver_minutes: float
    labour_cents: int
    vehicle_cents: int
    explain: str
    insurance_cents: int = 0
    vehicle_class: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_BOUNDS: dict[str, tuple[float, float]] = {
    "driver_hourly_cents": (0, 100000),
    "avg_speed_kmh": (5, 120),
    "pickup_minutes": (0, 240),
    "drop_minutes": (0, 240),
    "deadhead_factor": (0, 1),
    "vehicle_cents_per_km": (0, 1000),
    "thin_margin_pct": (0, 90),
    "working_days_per_month": (1, 31),
    "working_hours_per_day": (1, 24),
}


def default_margin_estimates() -> dict[str, Any]:
    return {"schema": 1, **DEFAULTS, "insurance_monthly_cents": dict(DEFAULT_INSURANCE)}


def normalize_margin_estimates(raw: Any) -> dict[str, Any]:
    """Validate the admin-editable estimates (Settings → pricing_margin_estimates)."""
    out = default_margin_estimates()
    src = raw if isinstance(raw, dict) else {}
    ins = src.get("insurance_monthly_cents")
    if isinstance(ins, dict):
        for vk, vv in ins.items():
            try:
                cents = int(vv)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"margin_invalid:insurance:{vk}") from exc
            if not 0 <= cents <= 10_000_000:
                raise ValueError(f"margin_invalid:insurance:{vk}")
            out["insurance_monthly_cents"][str(vk)] = cents
    for key, value in src.items():
        if key not in DEFAULTS or value is None:
            continue
        try:
            num = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"margin_invalid:{key}") from exc
        lo, hi = _BOUNDS[key]
        if not lo <= num <= hi:
            raise ValueError(f"margin_invalid:{key}")
        out[key] = int(num) if isinstance(DEFAULTS[key], int) else num
    return out


def _cfg(overrides: dict[str, Any] | None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    cfg["insurance_monthly_cents"] = dict(DEFAULT_INSURANCE)
    for k, v in (overrides or {}).items():
        if k in cfg and v is not None:
            cfg[k] = dict(v) if isinstance(v, dict) else v
    return cfg


def insurance_cents_per_hour(vehicle_class: str | None, overrides: dict[str, Any] | None = None) -> float:
    c = _cfg(overrides)
    monthly = int((c["insurance_monthly_cents"] or {}).get(vehicle_class or "", 0))
    hours = float(c["working_days_per_month"]) * float(c["working_hours_per_day"])
    return monthly / hours if hours > 0 else 0.0


def estimate_cost(
    distance_meters: float | int | None,
    *,
    duration_seconds: float | None = None,
    pickups: int = 1,
    drops: int = 1,
    overrides: dict[str, Any] | None = None,
) -> tuple[int, float, int, int]:
    """Return (cost_cents, driver_minutes, labour_cents, vehicle_cents)."""
    c = _cfg(overrides)
    km = max(float(distance_meters or 0) / 1000.0, 0.0)
    drive_min = (duration_seconds / 60.0) if duration_seconds else (km / float(c["avg_speed_kmh"])) * 60.0
    drive_min *= 1.0 + float(c["deadhead_factor"])
    minutes = drive_min + max(pickups, 1) * float(c["pickup_minutes"]) + max(drops, 1) * float(c["drop_minutes"])
    labour = round(minutes / 60.0 * int(c["driver_hourly_cents"]))
    vehicle = round(km * (1.0 + float(c["deadhead_factor"])) * int(c["vehicle_cents_per_km"]))
    return labour + vehicle, round(minutes, 1), labour, vehicle


def margin_check(
    price_cents: int,
    distance_meters: float | int | None,
    *,
    duration_seconds: float | None = None,
    pickups: int = 1,
    drops: int = 1,
    vehicle_class: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> MarginResult:
    c = _cfg(overrides)
    cost, minutes, labour, vehicle = estimate_cost(
        distance_meters, duration_seconds=duration_seconds, pickups=pickups, drops=drops, overrides=overrides
    )
    insurance = round(insurance_cents_per_hour(vehicle_class, overrides) * minutes / 60.0)
    cost += insurance
    margin = int(price_cents) - cost
    pct = round(margin / price_cents * 100.0, 1) if price_cents > 0 else -100.0
    status = "below_cost" if margin < 0 else ("thin" if pct < float(c["thin_margin_pct"]) else "ok")
    explain = (
        f"Cost ${cost / 100:.2f}: {minutes:.0f} driver min at ${int(c['driver_hourly_cents']) / 100:.2f}/h "
        f"(${labour / 100:.2f}) + vehicle ${vehicle / 100:.2f} + insurance ${insurance / 100:.2f}. "
        f"Margin ${margin / 100:.2f} ({pct}%)."
    )
    return MarginResult(
        status, int(price_cents), cost, margin, pct, minutes, labour, vehicle, explain, insurance, vehicle_class
    )


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def distance_outlier(
    road_meters: float | int | None,
    pickup: tuple[float, float] | None,
    dropoff: tuple[float, float] | None,
) -> str | None:
    """Return a reason string when the road distance is implausible, else None."""
    if not pickup or not dropoff or None in pickup or None in dropoff:
        return "missing_coordinates"
    straight = haversine_m(pickup[0], pickup[1], dropoff[0], dropoff[1])
    road = float(road_meters or 0)
    if straight >= 1000 and road < straight * 0.9:
        return "road_shorter_than_straight_line"
    if straight >= 2000 and road > straight * 3.0:
        return "road_over_3x_straight_line"
    if straight < 1000 and road > 15000:
        return "road_far_for_nearby_points"
    return None

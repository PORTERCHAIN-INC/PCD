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
    "avg_speed_kmh": 40.0,            # assumption when no routed duration
    "pickup_minutes": 10.0,           # assumption
    "drop_minutes": 8.0,              # assumption
    "deadhead_factor": 0.5,           # assumption: half the return leg is unpaid
    "vehicle_cents_per_km": 35,       # assumption: fuel + wear, cargo van
    "thin_margin_pct": 15.0,          # warn below this margin
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

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cfg(overrides: dict[str, Any] | None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    for k, v in (overrides or {}).items():
        if k in cfg and v is not None:
            cfg[k] = v
    return cfg


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
    overrides: dict[str, Any] | None = None,
) -> MarginResult:
    c = _cfg(overrides)
    cost, minutes, labour, vehicle = estimate_cost(
        distance_meters, duration_seconds=duration_seconds, pickups=pickups, drops=drops, overrides=overrides
    )
    margin = int(price_cents) - cost
    pct = round(margin / price_cents * 100.0, 1) if price_cents > 0 else -100.0
    status = "below_cost" if margin < 0 else ("thin" if pct < float(c["thin_margin_pct"]) else "ok")
    explain = (
        f"Cost ≈ ${cost / 100:.2f}: {minutes:.0f} driver min at ${int(c['driver_hourly_cents']) / 100:.2f}/h "
        f"(${labour / 100:.2f}) + vehicle ${vehicle / 100:.2f}. Margin ${margin / 100:.2f} ({pct}%)."
    )
    return MarginResult(status, int(price_cents), cost, margin, pct, minutes, labour, vehicle, explain)


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

"""
Smart route pricing — one engine for every route shape.

Shapes: 1 pickup → 1 drop, 1 → N, N → 1, N → M. Pickups are visited before
drops (consolidation). The route is priced as ONE optimized tour, never as a sum
of legs:

1. Points. ``mode="fsa"`` snaps every stop to its FSA centroid (merchant's real
   pickup FSA → drop FSA), so two addresses in the same FSA pair always price the
   same. ``mode="distance"`` uses the real coordinates.
2. Matrix. Road km / minutes between all points come from an injected
   ``matrix`` callable (Valhalla, OSRM fallback, cached — see the API adapter).
3. Sequence. Exact search over pickup and drop orders for small routes; nearest
   neighbour + 2-opt (precedence kept) for larger ones.
4. Price = base + smooth distance curve (piecewise marginal rates — continuous,
   no cliffs between FSAs) + drive/service time + stop and parcel components +
   handling tiers + deadhead (return share) — then vehicle, peak and downtown
   factors, the vehicle minimum and finally the COST FLOOR from the cost model
   ($/h driver, per-vehicle km and insurance), so no quote goes below cost.
5. Every quote carries a confidence score, each stop's marginal (insertion)
   cost, and a line-by-line explanation.

All coefficients live in the ``smart_pricing`` setting; a merchant contract may
override any of them (``pricing_config.smart_pricing.overrides``).
"""

from __future__ import annotations

import copy
import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from porterchain_pricing.contract_schedule import (
    HandlingTier,
    deep_merge,
    footprint_cm,
    handling_tier_for,
)
from porterchain_pricing.margin import margin_check

KM_PER_MILE = 1.609344

DEFAULT_SMART_PRICING: dict[str, Any] = {
    "enabled": False,  # global switch; merchants can opt in individually
    "mode": "fsa",  # fsa | distance
    "distance_unit": "km",  # km | mi — rates below are per this unit
    "base_cents": 1500,
    # Piecewise marginal rate per unit: from `from` units onward, each unit costs `cents`.
    "distance_curve": [
        {"from": 0, "cents": 150},
        {"from": 25, "cents": 110},
        {"from": 60, "cents": 85},
        {"from": 120, "cents": 70},
    ],
    "minute_cents": 20,  # per drive + service minute
    "service_minutes": {"pickup": 10, "drop": 8},
    "extra_drop_cents": 600,
    "extra_pickup_cents": 1000,
    "parcels_included_per_stop": 3,
    "extra_parcel_cents": 150,
    # A3 handling tiers (higher of weight or footprint; beyond last = quote).
    "handling": {
        "weight_unit": "lb",
        "dimension_unit": "in",
        "tiers": [
            {
                "code": "standard",
                "max_weight": 100,
                "max_footprint": [70, 45],
                "surcharge_cents": 0,
            },
            {
                "code": "T1",
                "max_weight": 125,
                "max_footprint": [80, 45],
                "surcharge_cents": 3000,
            },
            {
                "code": "T2",
                "max_weight": 150,
                "max_footprint": [90, 50],
                "surcharge_cents": 6000,
            },
        ],
    },
    "deadhead_share": 0.35,  # share of the empty return priced in
    "vehicle_factor": {
        "sedan_suv": 0.85,
        "pickup": 1.0,
        "cargo_van": 1.0,
        "sprinter_van": 1.15,
        "box_16": 1.6,
        "box_20": 1.8,
    },
    "vehicle_minimum_cents": {
        "sedan_suv": 2500,
        "cargo_van": 4500,
        "sprinter_van": 5500,
        "box_16": 12000,
        "box_20": 15000,
    },
    "peak": {"factor": 1.1, "windows": [[7, 9], [16, 18]]},  # local hours [start, end)
    "downtown": {
        "factor": 1.1,
        "fsas": [
            "M5A",
            "M5B",
            "M5C",
            "M5E",
            "M5G",
            "M5H",
            "M5J",
            "M5K",
            "M5L",
            "M5T",
            "M5V",
            "M5W",
            "M5X",
            "M4Y",
        ],
    },
    "cost_floor_margin_pct": 10.0,  # price ≥ cost / (1 - pct)
    "max_route_km": 150,  # beyond = flagged, lower confidence
}


def default_smart_pricing() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_SMART_PRICING)


def normalize_smart_pricing(raw: Any) -> dict[str, Any]:
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("smart_pricing must be an object")
    out = deep_merge(default_smart_pricing(), raw or {})
    if out["mode"] not in ("fsa", "distance"):
        raise ValueError("smart_pricing.mode must be fsa or distance")
    if out["distance_unit"] not in ("km", "mi"):
        raise ValueError("smart_pricing.distance_unit must be km or mi")
    curve = sorted(out["distance_curve"], key=lambda b: float(b["from"]))
    if (
        not curve
        or float(curve[0]["from"]) != 0
        or any(int(b["cents"]) < 0 for b in curve)
    ):
        raise ValueError(
            "smart_pricing.distance_curve must start at 0 with non-negative rates"
        )
    out["distance_curve"] = curve
    if not 0 <= float(out["deadhead_share"]) <= 1:
        raise ValueError("smart_pricing.deadhead_share must be 0..1")
    if not 0 <= float(out["cost_floor_margin_pct"]) < 90:
        raise ValueError("smart_pricing.cost_floor_margin_pct must be 0..90")
    return out


@dataclass
class RouteStop:
    kind: str  # pickup | drop
    lat: float | None = None
    lng: float | None = None
    fsa: str | None = None
    parcels: list[tuple[float | None, tuple[float | None, ...] | None]] = field(
        default_factory=list
    )
    label: str | None = None


Matrix = Callable[
    [list[tuple[float, float]]], tuple[list[list[float]], list[list[float]], str]
]


def curve_cents(units: float, curve: list[dict[str, Any]]) -> float:
    """Integral of the piecewise marginal rate — continuous and monotone (no cliffs)."""
    total = 0.0
    for i, band in enumerate(curve):
        start = float(band["from"])
        end = float(curve[i + 1]["from"]) if i + 1 < len(curve) else math.inf
        if units <= start:
            break
        total += (min(units, end) - start) * int(band["cents"])
    return total


def _tour(order: list[int], km: list[list[float]]) -> float:
    return sum(km[a][b] for a, b in itertools.pairwise(order))


def optimize_sequence(
    pickups: list[int], drops: list[int], km: list[list[float]]
) -> list[int]:
    """Best visiting order with every pickup before every drop. Starts at a pickup."""
    if len(pickups) <= 4 and len(drops) <= 6:
        best, best_len = None, math.inf
        for p in itertools.permutations(pickups):
            for d in itertools.permutations(drops):
                order = [*p, *d]
                length = _tour(order, km)
                if length < best_len - 1e-9:
                    best, best_len = order, length
        return list(best or [*pickups, *drops])
    order = _nn(pickups, km, None)
    order += _nn(drops, km, order[-1])
    return _two_opt(order, len(pickups), km)


def _nn(nodes: list[int], km: list[list[float]], start: int | None) -> list[int]:
    left = list(nodes)
    out: list[int] = []
    cur = start if start is not None else left.pop(0)
    if start is None:
        out.append(cur)
    while left:
        nxt = min(left, key=lambda j: km[cur][j])
        left.remove(nxt)
        out.append(nxt)
        cur = nxt
    return out


def _two_opt(order: list[int], n_pick: int, km: list[list[float]]) -> list[int]:
    """2-opt inside the pickup block and inside the drop block (keeps precedence)."""
    improved = True
    while improved:
        improved = False
        for lo, hi in ((0, n_pick), (n_pick, len(order))):
            for i in range(max(lo, 1), hi - 1):
                for j in range(i + 1, hi):
                    cand = order[:i] + order[i : j + 1][::-1] + order[j + 1 :]
                    if _tour(cand, km) < _tour(order, km) - 1e-9:
                        order, improved = cand, True
    return order


def smart_quote(
    stops: list[RouteStop],
    *,
    vehicle_class: str,
    matrix: Matrix,
    config: dict[str, Any] | None = None,
    cost_overrides: dict[str, Any] | None = None,
    centroid: Callable[[str], tuple[float, float] | None] | None = None,
    when: datetime | None = None,
) -> dict[str, Any]:
    cfg = normalize_smart_pricing(config)
    pickups = [i for i, s in enumerate(stops) if s.kind == "pickup"]
    drops = [i for i, s in enumerate(stops) if s.kind == "drop"]
    if not pickups or not drops:
        raise ValueError("need at least one pickup and one drop")
    confidence = 1.0
    notes: list[str] = []

    # 1. points
    pts: list[tuple[float, float]] = []
    for s in stops:
        p = None
        if cfg["mode"] == "fsa" and s.fsa and centroid:
            p = centroid(s.fsa.upper()[:3])
            if p is None:
                confidence -= 0.15
                notes.append(f"No centroid for {s.fsa}; used the address.")
        if p is None and s.lat is not None and s.lng is not None:
            p = (float(s.lat), float(s.lng))
        if p is None:
            raise ValueError(f"stop {s.label or s.fsa} has no location")
        pts.append(p)

    # 2. matrix
    km, minutes, source = matrix(pts)
    if source not in ("valhalla", "osrm", "cache"):
        confidence -= 0.25
        notes.append(
            "Road network unavailable; straight-line distance × detour factor."
        )

    # 3. sequence
    order = optimize_sequence(pickups, drops, km)
    route_km = _tour(order, km)
    drive_min = sum(minutes[a][b] for a, b in itertools.pairwise(order))
    return_km = km[order[-1]][order[0]]

    unit = cfg["distance_unit"]
    to_unit = (lambda k: k / KM_PER_MILE) if unit == "mi" else (lambda k: k)
    curve = cfg["distance_curve"]

    def route_price_core(seq: list[int]) -> float:
        return curve_cents(to_unit(_tour(seq, km)), curve)

    # 4. components
    lines: list[dict[str, Any]] = []

    def add(code: str, label: str, cents: float) -> None:
        if round(cents):
            lines.append({"code": code, "label": label, "cents": round(cents)})

    add("base", "Base", cfg["base_cents"])
    add(
        "distance",
        f"Route distance {to_unit(route_km):.1f} {unit} (optimized order)",
        curve_cents(to_unit(route_km), curve),
    )
    service_min = (
        len(pickups) * cfg["service_minutes"]["pickup"]
        + len(drops) * cfg["service_minutes"]["drop"]
    )
    add(
        "time",
        f"Drive {drive_min:.0f} min + service {service_min:.0f} min",
        (drive_min + service_min) * cfg["minute_cents"],
    )
    add(
        "extra_drops",
        f"{len(drops) - 1} extra drop(s)",
        (len(drops) - 1) * cfg["extra_drop_cents"],
    )
    add(
        "extra_pickups",
        f"{len(pickups) - 1} extra pickup(s)",
        (len(pickups) - 1) * cfg["extra_pickup_cents"],
    )
    tiers = _tiers(cfg["handling"])
    extra_parcels, handling_cents, quote_needed = 0, 0, False
    for s in stops:
        if s.kind != "drop":
            continue
        extra_parcels += max(len(s.parcels) - int(cfg["parcels_included_per_stop"]), 0)
        for w, dims in s.parcels:
            tier = handling_tier_for(tiers, w, dims)
            if tier is None:
                quote_needed = True
            else:
                handling_cents += tier.surcharge_cents
    add(
        "parcels",
        f"{extra_parcels} parcel(s) over {cfg['parcels_included_per_stop']}/stop",
        extra_parcels * cfg["extra_parcel_cents"],
    )
    add("handling", "Heavy/large item handling", handling_cents)
    add(
        "deadhead",
        f"Return share {cfg['deadhead_share']:.0%} of {to_unit(return_km):.1f} {unit}",
        cfg["deadhead_share"] * curve_cents(to_unit(return_km), curve),
    )
    subtotal = sum(l["cents"] for l in lines)

    factor = float(cfg["vehicle_factor"].get(vehicle_class, 1.0))
    reasons = [f"vehicle ×{factor:g}"] if factor != 1 else []
    hour = (when or datetime.now()).hour
    if any(a <= hour < b for a, b in cfg["peak"]["windows"]):
        factor *= float(cfg["peak"]["factor"])
        reasons.append(f"peak ×{cfg['peak']['factor']:g}")
    downtown = {f.upper() for f in cfg["downtown"]["fsas"]}
    if any((s.fsa or "").upper()[:3] in downtown for s in stops):
        factor *= float(cfg["downtown"]["factor"])
        reasons.append(f"downtown ×{cfg['downtown']['factor']:g}")
    price = subtotal * factor
    if reasons:
        add("factors", "Factors: " + ", ".join(reasons), price - subtotal)

    minimum = int(cfg["vehicle_minimum_cents"].get(vehicle_class, 0))
    if price < minimum:
        add("minimum", f"{vehicle_class} minimum", minimum - price)
        price = minimum

    cost = margin_check(
        int(price),
        route_km * 1000,
        duration_seconds=drive_min * 60,
        pickups=len(pickups),
        drops=len(drops),
        vehicle_class=vehicle_class,
        overrides=cost_overrides,
    )
    floor = cost.cost_cents / (1 - float(cfg["cost_floor_margin_pct"]) / 100)
    if price < floor:
        add(
            "cost_floor",
            f"Cost floor (cost ${cost.cost_cents / 100:.2f} + {cfg['cost_floor_margin_pct']:g}% margin)",
            floor - price,
        )
        price = floor
    total = round(price)
    final_margin = margin_check(
        total,
        route_km * 1000,
        duration_seconds=drive_min * 60,
        pickups=len(pickups),
        drops=len(drops),
        vehicle_class=vehicle_class,
        overrides=cost_overrides,
    )

    # 5. marginal (insertion) cost of each extra stop — distance curve delta of removing it
    marginal = []
    for idx in order:
        group = pickups if stops[idx].kind == "pickup" else drops
        if len(group) < 2:
            continue
        rest = optimize_sequence(
            [p for p in pickups if p != idx], [d for d in drops if d != idx], km
        )
        marginal.append(
            {
                "stop": stops[idx].label or stops[idx].fsa or idx,
                "kind": stops[idx].kind,
                "insertion_km": round(route_km - _tour(rest, km), 2),
                "insertion_cents": round(
                    route_price_core(order) - route_price_core(rest)
                ),
            }
        )

    if route_km > cfg["max_route_km"]:
        confidence -= 0.2
        notes.append(f"Route over {cfg['max_route_km']} km — confirm by quote.")
    if quote_needed:
        confidence -= 0.3
        notes.append("An item is beyond the last handling tier — custom quote.")
    shape = f"{'multi' if len(pickups) > 1 else 'single'}_pickup_{'multi' if len(drops) > 1 else 'single'}_drop"
    return {
        "total_cents": total,
        "shape": shape,
        "mode": cfg["mode"],
        "unit": unit,
        "sequence": [stops[i].label or stops[i].fsa or i for i in order],
        "route_km": round(route_km, 2),
        "route_distance": round(to_unit(route_km), 2),
        "drive_minutes": round(drive_min, 1),
        "lines": lines,
        "marginal_stops": marginal,
        "cost": final_margin.as_dict(),
        "matrix_source": source,
        "confidence": round(max(confidence, 0.05), 2),
        "custom_quote": quote_needed,
        "notes": notes,
    }


def _tiers(handling: dict[str, Any]) -> tuple[HandlingTier, ...]:
    from porterchain_pricing.contract_schedule import handling_tiers_from_dict

    return handling_tiers_from_dict(handling)


def haversine_matrix(
    points: list[tuple[float, float]], *, detour: float = 1.3, kmh: float = 40.0
):
    """Fallback matrix: straight line × detour factor, minutes at an average speed."""
    from porterchain_pricing.margin import haversine_m

    km = [
        [haversine_m(a[0], a[1], b[0], b[1]) / 1000 * detour for b in points]
        for a in points
    ]
    mins = [[d / kmh * 60 for d in row] for row in km]
    return km, mins, "haversine"


__all__ = [
    "DEFAULT_SMART_PRICING",
    "RouteStop",
    "curve_cents",
    "default_smart_pricing",
    "footprint_cm",
    "haversine_matrix",
    "normalize_smart_pricing",
    "optimize_sequence",
    "smart_quote",
]

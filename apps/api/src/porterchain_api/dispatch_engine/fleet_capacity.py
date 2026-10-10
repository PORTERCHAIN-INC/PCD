"""Vehicle capacity table (settings-driven) and fill % maths.

Stored in ``system_config['dispatch_fleet']``. G-licence fleet only:
sedan, SUV, cargo van, box truck. Costs are driver time: gas is on the driver,
so a vehicle's cost is the driver-pay plan plus an optional per-km figure.

Volume is stored in m³ and shown in cubic feet (``max_ft3``); edits may send either.
``margin_floor_pct`` is the lowest margin a stop may run at before an alert.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

STORAGE_KEY = "dispatch_fleet"
MAX_FILL = 0.85
OFFER_TTL_SECONDS = 180
FT3_PER_M3 = 35.3147
MARGIN_FLOOR_PCT = 20

_DEFAULT: dict[str, Any] = {
    "schema": 1,
    "hourly_cost_cents": 2700,
    "max_fill": MAX_FILL,
    "offer_ttl_seconds": OFFER_TTL_SECONDS,
    "service_minutes_per_stop": 8,
    "at_risk_minutes": 10,
    "margin_floor_pct": MARGIN_FLOOR_PCT,
    "vehicles": [
        {"id": "sedan", "label": "Sedan", "max_kg": 150, "max_m3": 0.4, "max_boxes": 8, "cost_per_km_cents": 0, "enabled": True},
        {"id": "suv", "label": "SUV", "max_kg": 300, "max_m3": 0.9, "max_boxes": 16, "cost_per_km_cents": 0, "enabled": True},
        {"id": "van", "label": "Cargo van", "max_kg": 900, "max_m3": 3.5, "max_boxes": 45, "cost_per_km_cents": 0, "enabled": True},
        {"id": "box_truck", "label": "Box truck", "max_kg": 2500, "max_m3": 14.0, "max_boxes": 140, "cost_per_km_cents": 0, "enabled": True},
    ],
}

# Vehicle class aliases seen in driver/vehicle rows → canonical fleet id.
_ALIASES = {
    "car": "sedan", "sedan": "sedan", "compact": "sedan",
    "suv": "suv", "crossover": "suv", "minivan": "suv",
    "van": "van", "cargo_van": "van", "sprinter": "van", "cube_van": "van",
    "box_truck": "box_truck", "truck": "box_truck", "straight_truck": "box_truck",
}
RANK = {"sedan": 0, "suv": 1, "van": 2, "box_truck": 3}


def default_fleet() -> dict[str, Any]:
    out = copy.deepcopy(_DEFAULT)
    for v in out["vehicles"]:
        v["max_ft3"] = ft3(v["max_m3"])
    return out


def canonical_class(raw: str | None) -> str | None:
    key = str(raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    return _ALIASES.get(key)


def _num(value: Any, path: str, *, allow_zero: bool = True) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"dispatch_fleet_invalid:{path}") from exc
    if out < 0 or (not allow_zero and out == 0):
        raise ValueError(f"dispatch_fleet_invalid:{path}")
    return out


def normalize_fleet(raw: Any) -> dict[str, Any]:
    """Validate a stored/edited table. Unknown keys dropped; defaults fill gaps."""
    src = raw if isinstance(raw, dict) else {}
    out = default_fleet()
    for key in ("hourly_cost_cents", "service_minutes_per_stop", "at_risk_minutes", "offer_ttl_seconds",
                "margin_floor_pct"):
        if key in src:
            out[key] = int(_num(src[key], key))
    if "max_fill" in src:
        fill = _num(src["max_fill"], "max_fill", allow_zero=False)
        if fill > 1:
            raise ValueError("dispatch_fleet_invalid:max_fill")
        out["max_fill"] = round(fill, 3)
    if out["margin_floor_pct"] > 90:
        raise ValueError("dispatch_fleet_invalid:margin_floor_pct")
    if out["offer_ttl_seconds"] < 30:
        raise ValueError("dispatch_fleet_invalid:offer_ttl_seconds")
    if "vehicles" in src:
        rows = src["vehicles"]
        if not isinstance(rows, list) or not rows:
            raise ValueError("dispatch_fleet_invalid:vehicles")
        vehicles = []
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"dispatch_fleet_invalid:vehicles[{i}]")
            vid = canonical_class(row.get("id"))
            if vid is None:
                raise ValueError(f"dispatch_fleet_invalid:vehicles[{i}].id")
            vehicles.append(
                {
                    "id": vid,
                    "label": str(row.get("label") or vid)[:40],
                    "max_kg": _num(row.get("max_kg"), f"vehicles[{i}].max_kg", allow_zero=False),
                    "max_m3": _vehicle_m3(row, i),
                    "max_boxes": int(_num(row.get("max_boxes"), f"vehicles[{i}].max_boxes", allow_zero=False)),
                    "cost_per_km_cents": int(_num(row.get("cost_per_km_cents", 0), f"vehicles[{i}].cost_per_km_cents")),
                    "enabled": bool(row.get("enabled", True)),
                }
            )
        if len({v["id"] for v in vehicles}) != len(vehicles):
            raise ValueError("dispatch_fleet_invalid:vehicles_duplicate")
        out["vehicles"] = sorted(vehicles, key=lambda v: RANK.get(v["id"], 9))
    for v in out["vehicles"]:
        v["max_ft3"] = ft3(v["max_m3"])
    return out


def ft3(m3: float) -> float:
    return round(float(m3) * FT3_PER_M3, 1)


def _vehicle_m3(row: dict[str, Any], i: int) -> float:
    if row.get("max_ft3") not in (None, ""):
        return round(_num(row["max_ft3"], f"vehicles[{i}].max_ft3", allow_zero=False) / FT3_PER_M3, 3)
    return _num(row.get("max_m3"), f"vehicles[{i}].max_m3", allow_zero=False)


def load_fleet(db: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, STORAGE_KEY)
    try:
        return normalize_fleet(row.value if row is not None else None)
    except ValueError:
        return default_fleet()


@dataclass(frozen=True)
class Load:
    kg: float = 0.0
    m3: float = 0.0
    boxes: int = 0

    def __add__(self, other: "Load") -> "Load":
        return Load(self.kg + other.kg, self.m3 + other.m3, self.boxes + other.boxes)


def _dims_m3(dims: Any) -> float:
    if not isinstance(dims, dict):
        return 0.0
    try:
        l_, w, h = (float(dims.get(k) or 0) for k in ("length", "width", "height"))
    except (TypeError, ValueError):
        return 0.0
    unit = str(dims.get("unit") or "cm").lower()
    factor = {"cm": 1e-6, "in": 1.6387e-5, "ft": 1 / FT3_PER_M3, "m": 1.0, "mm": 1e-9}.get(unit, 1e-6)
    return max(l_ * w * h * factor, 0.0)


def order_load(order: Any) -> Load:
    """Load of one order from its packages; falls back to one box when none."""
    packages = list(getattr(order, "packages", None) or [])
    if not packages:
        return Load(0.0, 0.0, 1)
    kg = sum(float(p.weight_kg or 0) for p in packages)
    m3 = sum(_dims_m3(p.dimensions) for p in packages)
    return Load(round(kg, 2), round(m3, 3), len(packages))


def fill_ratio(load: Load, vehicle: dict[str, Any]) -> float:
    """Tightest of weight, volume and box count (0..n)."""
    return round(
        max(
            load.kg / float(vehicle["max_kg"]),
            load.m3 / float(vehicle["max_m3"]),
            load.boxes / float(vehicle["max_boxes"]),
        ),
        3,
    )


def smallest_fitting(load: Load, fleet: dict[str, Any], *, allowed: set[str] | None = None) -> dict[str, Any] | None:
    """Cheapest (smallest) enabled vehicle keeping fill ≤ max_fill."""
    cap = float(fleet.get("max_fill") or MAX_FILL)
    for vehicle in fleet["vehicles"]:
        if not vehicle.get("enabled", True):
            continue
        if allowed is not None and vehicle["id"] not in allowed:
            continue
        if fill_ratio(load, vehicle) <= cap:
            return vehicle
    return None


def vehicle_by_id(fleet: dict[str, Any], vid: str | None) -> dict[str, Any] | None:
    cid = canonical_class(vid)
    return next((v for v in fleet["vehicles"] if v["id"] == cid), None)

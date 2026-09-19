"""Valhalla costing selector — truck for box classes; auto otherwise.

Ontario drive-on-right already biases favorable (right) turns in Valhalla.
Preferring `truck` for box classes adds height/weight-aware restrictions and
maneuver costs without a PorterChain left-turn ban list.
"""

from __future__ import annotations

import re

# Explicit truck-profile classes (GTA booking catalog).
_TRUCK_COSTING_IDS = frozenset(
    {
        "box_truck",
        "boxtruck",
        "straight_truck",
        "straighttruck",
        "truck",
    }
)


def normalize_vehicle_class_key(vehicle_class: str | None) -> str:
    raw = (vehicle_class or "").strip()
    if not raw:
        return ""
    # cargoVan / boxTruck → cargo_van / box_truck
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw)
    return spaced.lower().replace("-", "_").replace(" ", "_")


def valhalla_costing_for_vehicle_class(vehicle_class: str | None) -> str:
    """Map PorterChain vehicle_class → Valhalla costing profile.

    Returns ``truck`` for box / straight truck classes; ``auto`` for vans/cars.
    Unknown / empty → ``auto`` (safe default; still right-turn biased in Ontario).
    """
    key = normalize_vehicle_class_key(vehicle_class)
    if not key:
        return "auto"
    if key in _TRUCK_COSTING_IDS:
        return "truck"
    # Catch vendor aliases like "Box Truck" already normalized, or "*_truck".
    if key.endswith("_truck") or key.startswith("truck_"):
        return "truck"
    return "auto"


def resolve_valhalla_costing(
    *,
    costing: str | None = None,
    vehicle_class: str | None = None,
) -> str:
    """Explicit costing wins; otherwise derive from vehicle_class."""
    explicit = (costing or "").strip().lower()
    if explicit in {"auto", "truck", "bus", "bicycle", "pedestrian", "motor_scooter"}:
        return explicit
    return valhalla_costing_for_vehicle_class(vehicle_class)

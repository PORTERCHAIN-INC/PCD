"""GTA delivery rate matrix — authoritative retail quote math.

Base price covers up to N km (default 20). Extra km, extra pickups (>1), extra drops (>1),
and flat downtown / upper-zone surcharges (each at most once per trip).

Rates are editable via admin Settings → Pricing (`system_config.pricing_gta_rate`).
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from porterchain_pricing.types import GeoPoint

# AUDIT P2-1 / PLAN Wave 4: downtown = south of Bloor latitude; Markham / North York
# are AABB surface-road boxes. Do NOT replace with Valhalla isochrones — that changes
# quoted CAD. Product must sign a map before any isochrone surcharge. Coverage UI may
# call MapsService.isochrone(); calculate_gta_delivery_rate must never.
BLOOR_LAT = 43.6708

# Rough bounding boxes for Markham / North York surface-road surcharge
_NORTH_YORK = {"min_lat": 43.72, "max_lat": 43.80, "min_lng": -79.55, "max_lng": -79.28}
_MARKHAM = {"min_lat": 43.80, "max_lat": 43.95, "min_lng": -79.42, "max_lng": -79.18}

# Defaults — CAD dollars (also seed for admin Settings → Pricing)
DEFAULT_BASE_KM_LIMIT = 20.0
DEFAULT_DOWNTOWN_FEE_CAD = 25.0
DEFAULT_UPPER_ZONE_FEE_CAD = 15.0

# Canonical matrix keys = Settings vehicle_types catalog ids
DEFAULT_VEHICLE_MATRIX: dict[str, dict[str, float]] = {
    "sedan": {"base_price": 45.0, "extra_km_rate": 1.25, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "suv": {"base_price": 55.0, "extra_km_rate": 1.75, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "pickup": {"base_price": 60.0, "extra_km_rate": 1.90, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "cargo_van": {"base_price": 65.0, "extra_km_rate": 2.00, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "sprinter_van": {"base_price": 75.0, "extra_km_rate": 2.50, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "box_truck": {"base_price": 125.0, "extra_km_rate": 3.50, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
}

# Legacy matrix keys → catalog ids (SystemConfig migration)
_LEGACY_MATRIX_KEYS: dict[str, str] = {
    "small_van": "cargo_van",
    "large_van": "sprinter_van",
}

# Back-compat aliases used by older call sites / tests
BASE_KM_LIMIT = DEFAULT_BASE_KM_LIMIT
DOWNTOWN_FEE_CAD = DEFAULT_DOWNTOWN_FEE_CAD
UPPER_ZONE_FEE_CAD = DEFAULT_UPPER_ZONE_FEE_CAD
VEHICLE_MATRIX = DEFAULT_VEHICLE_MATRIX

VEHICLE_LABELS: dict[str, str] = {
    "sedan": "Sedan",
    "suv": "SUV",
    "pickup": "Pickup",
    "cargo_van": "Cargo van",
    "sprinter_van": "Sprinter van",
    "box_truck": "Box truck",
    # legacy labels
    "small_van": "Cargo van",
    "large_van": "Sprinter van",
}

# Booking / website / legacy API vehicle keys → catalog matrix keys
VEHICLE_ALIAS: dict[str, str] = {
    "sedan": "sedan",
    "suv": "suv",
    "pickup": "pickup",
    "minivan": "cargo_van",
    "small_van": "cargo_van",
    "cargo_van": "cargo_van",
    "cargovan": "cargo_van",
    "cargoVan": "cargo_van",
    "large_van": "sprinter_van",
    "largevan": "sprinter_van",
    "high_roof": "sprinter_van",
    "highroof": "sprinter_van",
    "highRoof": "sprinter_van",
    "sprinter_van": "sprinter_van",
    "sprintervan": "sprinter_van",
    "sprinter": "sprinter_van",
    "box_truck": "box_truck",
    "boxtruck": "box_truck",
    "box_16ft": "box_truck",
    "box_20ft": "box_truck",
    "box16": "box_truck",
    "box20": "box_truck",
}

_VEHICLE_RATE_KEYS = ("base_price", "extra_km_rate", "extra_pick_fee", "extra_drop_fee")


@dataclass
class GtaRateConfig:
    """Editable GTA quote rates (CAD dollars)."""

    base_km_limit: float = DEFAULT_BASE_KM_LIMIT
    downtown_fee_cad: float = DEFAULT_DOWNTOWN_FEE_CAD
    upper_zone_fee_cad: float = DEFAULT_UPPER_ZONE_FEE_CAD
    vehicles: dict[str, dict[str, float]] = field(
        default_factory=lambda: deepcopy(DEFAULT_VEHICLE_MATRIX)
    )

    def vehicle(self, matrix_key: str) -> dict[str, float]:
        return self.vehicles.get(matrix_key) or DEFAULT_VEHICLE_MATRIX[matrix_key]

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_km_limit": self.base_km_limit,
            "downtown_fee_cad": self.downtown_fee_cad,
            "upper_zone_fee_cad": self.upper_zone_fee_cad,
            "vehicles": {k: dict(v) for k, v in self.vehicles.items()},
        }


def default_gta_rate_config() -> GtaRateConfig:
    return GtaRateConfig()


def gta_rate_config_from_dict(
    data: dict[str, Any] | None,
    *,
    base: GtaRateConfig | None = None,
) -> GtaRateConfig:
    """Build a GTA config, optionally starting from `base` then applying overlay keys."""
    if base is None and not data:
        return default_gta_rate_config()
    card = deepcopy(base) if base is not None else default_gta_rate_config()
    if not data:
        return card

    vehicles = deepcopy(card.vehicles)
    raw_vehicles = data.get("vehicles")
    if isinstance(raw_vehicles, dict):
        for key, rates in raw_vehicles.items():
            if not isinstance(rates, dict):
                continue
            matrix_key = _LEGACY_MATRIX_KEYS.get(str(key), str(key))
            if matrix_key not in DEFAULT_VEHICLE_MATRIX and matrix_key not in vehicles:
                continue
            merged = dict(vehicles.get(matrix_key) or DEFAULT_VEHICLE_MATRIX.get(matrix_key, {}))
            for rk in _VEHICLE_RATE_KEYS:
                if rk in rates and rates[rk] is not None:
                    merged[rk] = float(rates[rk])
            vehicles[matrix_key] = merged

    return GtaRateConfig(
        base_km_limit=float(data["base_km_limit"]) if data.get("base_km_limit") is not None else card.base_km_limit,
        downtown_fee_cad=(
            float(data["downtown_fee_cad"]) if data.get("downtown_fee_cad") is not None else card.downtown_fee_cad
        ),
        upper_zone_fee_cad=(
            float(data["upper_zone_fee_cad"])
            if data.get("upper_zone_fee_cad") is not None
            else card.upper_zone_fee_cad
        ),
        vehicles=vehicles,
    )


def merge_merchant_gta_overlay(system: GtaRateConfig, merchant_config: dict[str, Any] | None) -> GtaRateConfig:
    """Apply merchant `pricing_config.gta_rate` over the platform Settings matrix."""
    cfg = merchant_config if isinstance(merchant_config, dict) else {}
    overlay = cfg.get("gta_rate")
    if not isinstance(overlay, dict) or not overlay:
        return system
    return gta_rate_config_from_dict(overlay, base=system)


@dataclass(frozen=True)
class GtaRateResult:
    vehicle_type: str
    total_km: float
    total_pickups: int
    total_drops: int
    is_downtown: bool
    is_upper_zone: bool
    distance_cost_cad: float
    stop_fees_cad: float
    location_surcharges_cad: float
    total_cad: float
    downtown_fee_cad: float = 0.0
    upper_zone_fee_cad: float = 0.0

    @property
    def total_cents(self) -> int:
        return int(round(self.total_cad * 100))

    @property
    def distance_cost_cents(self) -> int:
        return int(round(self.distance_cost_cad * 100))

    @property
    def stop_fees_cents(self) -> int:
        return int(round(self.stop_fees_cad * 100))

    @property
    def location_surcharges_cents(self) -> int:
        return int(round(self.location_surcharges_cad * 100))

    @property
    def downtown_fee_cents(self) -> int:
        return int(round(self.downtown_fee_cad * 100))

    @property
    def upper_zone_fee_cents(self) -> int:
        return int(round(self.upper_zone_fee_cad * 100))


def normalize_vehicle_type(vehicle_type: str, *, known: Mapping[str, Any] | None = None) -> str:
    matrix = known or DEFAULT_VEHICLE_MATRIX
    raw = (vehicle_type or "").strip()
    if not raw:
        raise ValueError("Invalid vehicle type selected.")
    if raw in VEHICLE_ALIAS:
        return VEHICLE_ALIAS[raw]
    key = raw.lower().replace("-", "_").replace(" ", "_")
    compact = key.replace("_", "")
    if key in matrix:
        return key
    if key in VEHICLE_ALIAS:
        return VEHICLE_ALIAS[key]
    if compact in VEHICLE_ALIAS:
        return VEHICLE_ALIAS[compact]
    snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in raw).lstrip("_").lower()
    if snake in VEHICLE_ALIAS:
        return VEHICLE_ALIAS[snake]
    if snake in matrix:
        return snake
    raise ValueError("Invalid vehicle type selected.")


def _in_bounds(lat: float, lng: float, box: Mapping[str, float]) -> bool:
    return box["min_lat"] <= lat <= box["max_lat"] and box["min_lng"] <= lng <= box["max_lng"]


def is_downtown_point(point: GeoPoint) -> bool:
    """True if stop is south of Bloor St (central Toronto)."""
    text = (point.formatted or "").lower()
    if "south of bloor" in text or "financial district" in text:
        return True
    if point.lat is None:
        return False
    if point.lat >= BLOOR_LAT:
        return False
    if point.lng is None:
        return True
    return -79.55 <= point.lng <= -79.25


def is_upper_zone_point(point: GeoPoint) -> bool:
    """True if stop is Markham / North York surface-road area."""
    text = (point.formatted or "").lower()
    if "markham" in text or "north york" in text or "northyork" in text:
        return True
    if point.lat is None or point.lng is None:
        return False
    return _in_bounds(point.lat, point.lng, _NORTH_YORK) or _in_bounds(point.lat, point.lng, _MARKHAM)


def detect_location_flags(
    pickup: GeoPoint,
    dropoff: GeoPoint,
    additional_stops: list[GeoPoint] | None = None,
) -> tuple[bool, bool]:
    stops = [pickup, dropoff, *(additional_stops or [])]
    downtown = any(is_downtown_point(s) for s in stops)
    upper = any(is_upper_zone_point(s) for s in stops)
    return downtown, upper


def calculate_gta_delivery_rate(
    *,
    vehicle_type: str,
    total_km: float,
    total_pickups: int = 1,
    total_drops: int = 1,
    is_downtown: bool = False,
    is_upper_zone: bool = False,
    config: GtaRateConfig | None = None,
) -> GtaRateResult:
    """
    GTA quote function (CAD dollars, 2-decimal total). Uses editable config when provided.

    Composed from the distance, stop-fee and location components so quoting one
    of them on its own can never drift from the full matrix.
    """
    from porterchain_pricing.components.distance import DistanceRateService
    from porterchain_pricing.components.location import LocationSurchargeService
    from porterchain_pricing.components.stops import StopFeeService

    cfg = config or default_gta_rate_config()
    matrix_key = normalize_vehicle_type(vehicle_type, known=cfg.vehicles)

    km = max(float(total_km), 0.0)
    pickups = max(int(total_pickups), 1)
    drops = max(int(total_drops), 1)

    distance_q = DistanceRateService().quote(vehicle_type=matrix_key, total_km=km, config=cfg)
    stops_q = StopFeeService().quote(
        vehicle_type=matrix_key, total_pickups=pickups, total_drops=drops, config=cfg
    )
    location_q = LocationSurchargeService().quote(
        is_downtown=is_downtown, is_upper_zone=is_upper_zone, config=cfg
    )

    distance_cost = distance_q.total_cents / 100.0
    stop_fees = stops_q.total_cents / 100.0
    downtown_fee = location_q.metadata["downtown_fee_cents"] / 100.0
    upper_fee = location_q.metadata["upper_zone_fee_cents"] / 100.0
    location = downtown_fee + upper_fee

    total = round(distance_cost + stop_fees + location, 2)
    return GtaRateResult(
        vehicle_type=matrix_key,
        total_km=km,
        total_pickups=pickups,
        total_drops=drops,
        is_downtown=is_downtown,
        is_upper_zone=is_upper_zone,
        distance_cost_cad=round(distance_cost, 2),
        stop_fees_cad=round(stop_fees, 2),
        location_surcharges_cad=round(location, 2),
        total_cad=total,
        downtown_fee_cad=round(downtown_fee, 2),
        upper_zone_fee_cad=round(upper_fee, 2),
    )

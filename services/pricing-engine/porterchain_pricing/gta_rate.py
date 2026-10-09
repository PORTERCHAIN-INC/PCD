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

# Location surcharges are FSA / city based — never Valhalla isochrones or road
# matrices (HS-20 / verify_no_ops_spatial_math). Coverage UI may call Valhalla
# isochrones; quote math must never.
#
# BUSINESS DECISION (confirmed by Ravi 2026-10-09: FSA only, no lat/lng box):
# downtown = the City of Toronto Downtown Plan area FSAs below
# (Bathurst → Don River, lake → Bloor / Rosedale ravine,
# plus large-receiver codes). Markham / North York = FSA sets + whole-locality
# token in the formatted address (not street names like "Markham St").
# An address with no postal code / locality gets no surcharge.

# Defaults — CAD dollars (also seed for admin Settings → Pricing)
DEFAULT_BASE_KM_LIMIT = 20.0
DEFAULT_DOWNTOWN_FEE_CAD = 25.0
DEFAULT_UPPER_ZONE_FEE_CAD = 15.0

# Canonical matrix keys = Settings vehicle_types catalog ids
DEFAULT_VEHICLE_MATRIX: dict[str, dict[str, float]] = {
    "sedan_suv": {"base_price": 45.0, "extra_km_rate": 1.25, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "pickup": {"base_price": 60.0, "extra_km_rate": 1.90, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "cargo_van": {"base_price": 65.0, "extra_km_rate": 2.00, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "sprinter_van": {"base_price": 75.0, "extra_km_rate": 2.50, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "box_16": {"base_price": 125.0, "extra_km_rate": 3.50, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    "box_20": {"base_price": 125.0, "extra_km_rate": 3.50, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
}

# Legacy matrix keys → catalog ids (SystemConfig + older merchant overlays)
_LEGACY_MATRIX_KEYS: dict[str, str] = {
    "sedan": "sedan_suv",
    "suv": "sedan_suv",
    "box_truck": "box_16",
    "small_van": "cargo_van",
    "large_van": "sprinter_van",
}

VEHICLE_MATRIX = DEFAULT_VEHICLE_MATRIX

# One collapse table for every legacy / camelCase / alias vehicle key → catalog id.
# Used by normalize_vehicle_type, vehicle_classes_match, and config loaders.
VEHICLE_ALIAS: dict[str, str] = {
    "sedan": "sedan_suv",
    "suv": "sedan_suv",
    "sedan_suv": "sedan_suv",
    "sedansuv": "sedan_suv",
    "pickup": "pickup",
    "pickup_truck": "pickup",
    "minivan": "cargo_van",
    "small_van": "cargo_van",
    "cargo_van": "cargo_van",
    "cargovan": "cargo_van",
    "large_van": "sprinter_van",
    "largevan": "sprinter_van",
    "high_roof": "sprinter_van",
    "highroof": "sprinter_van",
    "sprinter_van": "sprinter_van",
    "sprintervan": "sprinter_van",
    "sprinter": "sprinter_van",
    "sprintervans": "sprinter_van",
    "box_truck": "box_16",
    "boxtruck": "box_16",
    "box_16ft": "box_16",
    "box_20ft": "box_20",
    "box16": "box_16",
    "box20": "box_20",
    "box_16": "box_16",
    "box_20": "box_20",
}

_VEHICLE_RATE_KEYS = ("base_price", "extra_km_rate", "extra_pick_fee", "extra_drop_fee")

CUSTOMER_VEHICLE_IDS = ("sedan_suv", "cargo_van", "pickup", "sprinter_van", "box_16", "box_20")


@dataclass
class GtaRateConfig:
    """Editable GTA quote rates (CAD dollars)."""

    base_km_limit: float = DEFAULT_BASE_KM_LIMIT
    downtown_fee_cad: float = DEFAULT_DOWNTOWN_FEE_CAD
    upper_zone_fee_cad: float = DEFAULT_UPPER_ZONE_FEE_CAD
    vehicles: dict[str, dict[str, float]] = field(
        default_factory=lambda: deepcopy(DEFAULT_VEHICLE_MATRIX)
    )
    #: Customer distance card: a missing vehicle is no price, not another class.
    strict_vehicles: bool = False
    weight_threshold_kg: float | None = None
    weight_cents_per_kg: int | None = None
    volume_threshold_cm3: float | None = None
    cents_per_10k_cm3: int | None = None
    declared_value_threshold_cents: int | None = None
    declared_value_rate: float | None = None

    def vehicle(self, matrix_key: str) -> dict[str, float]:
        row = self.vehicles.get(matrix_key)
        if row:
            return row
        if self.strict_vehicles or matrix_key not in DEFAULT_VEHICLE_MATRIX:
            raise ValueError("vehicle_rate_missing")
        return DEFAULT_VEHICLE_MATRIX[matrix_key]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "base_km_limit": self.base_km_limit,
            "downtown_fee_cad": self.downtown_fee_cad,
            "upper_zone_fee_cad": self.upper_zone_fee_cad,
            "vehicles": {k: dict(v) for k, v in self.vehicles.items()},
        }
        for key in (
            "weight_threshold_kg",
            "weight_cents_per_kg",
            "volume_threshold_cm3",
            "cents_per_10k_cm3",
            "declared_value_threshold_cents",
            "declared_value_rate",
        ):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        return out


def default_gta_rate_config() -> GtaRateConfig:
    return GtaRateConfig()


def _canonical_matrix_key(raw_key: str) -> str:
    """Map legacy GTA matrix keys onto the retail vehicle catalog ids."""
    return _LEGACY_MATRIX_KEYS.get(str(raw_key), str(raw_key))


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

    # Start from base with legacy keys already collapsed (first write wins).
    vehicles: dict[str, dict[str, float]] = {}
    for key, rates in card.vehicles.items():
        matrix_key = _canonical_matrix_key(str(key))
        if matrix_key in vehicles and str(key) != matrix_key:
            continue
        vehicles[matrix_key] = dict(rates)

    raw_vehicles = data.get("vehicles")
    legacy_claimed: set[str] = set()
    if isinstance(raw_vehicles, dict):
        for key, rates in raw_vehicles.items():
            if not isinstance(rates, dict):
                continue
            raw_key = str(key)
            matrix_key = _canonical_matrix_key(raw_key)
            if (
                matrix_key not in DEFAULT_VEHICLE_MATRIX
                and matrix_key not in vehicles
                and matrix_key not in CUSTOMER_VEHICLE_IDS
            ):
                continue
            # sedan + suv both collapse to sedan_suv — keep the first write (prefer sedan).
            if raw_key != matrix_key and matrix_key in legacy_claimed:
                continue
            seed = vehicles.get(matrix_key) or DEFAULT_VEHICLE_MATRIX.get(matrix_key) or {
                "base_price": 0.0,
                "extra_km_rate": 0.0,
                "extra_pick_fee": 0.0,
                "extra_drop_fee": 0.0,
            }
            merged = dict(seed)
            for rk in _VEHICLE_RATE_KEYS:
                if rk in rates and rates[rk] is not None:
                    merged[rk] = float(rates[rk])
            vehicles[matrix_key] = merged
            if raw_key != matrix_key:
                legacy_claimed.add(matrix_key)

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
        strict_vehicles=bool(data.get("strict_vehicles", card.strict_vehicles)),
        weight_threshold_kg=_optional_float(data, "weight_threshold_kg", card.weight_threshold_kg),
        weight_cents_per_kg=_optional_int(data, "weight_cents_per_kg", card.weight_cents_per_kg),
        volume_threshold_cm3=_optional_float(data, "volume_threshold_cm3", card.volume_threshold_cm3),
        cents_per_10k_cm3=_optional_int(data, "cents_per_10k_cm3", card.cents_per_10k_cm3),
        declared_value_threshold_cents=_optional_int(
            data, "declared_value_threshold_cents", card.declared_value_threshold_cents
        ),
        declared_value_rate=_optional_float(data, "declared_value_rate", card.declared_value_rate),
    )


def _optional_float(data: Mapping[str, Any], key: str, fallback: float | None) -> float | None:
    if key not in data or data.get(key) is None or data.get(key) == "":
        return fallback
    return float(data[key])


def _optional_int(data: Mapping[str, Any], key: str, fallback: int | None) -> int | None:
    if key not in data or data.get(key) is None or data.get(key) == "":
        return fallback
    return int(data[key])


def default_customer_distance_dict() -> dict[str, Any]:
    """Day-one customer card, collapsed from the current merchant distance rates."""
    sedan = DEFAULT_VEHICLE_MATRIX["sedan_suv"]
    box = DEFAULT_VEHICLE_MATRIX["box_16"]
    return {
        "strict_vehicles": True,
        "base_km_limit": DEFAULT_BASE_KM_LIMIT,
        "downtown_fee_cad": DEFAULT_DOWNTOWN_FEE_CAD,
        "upper_zone_fee_cad": DEFAULT_UPPER_ZONE_FEE_CAD,
        "weight_threshold_kg": 50,
        "weight_cents_per_kg": 0,
        "volume_threshold_cm3": 100_000,
        "cents_per_10k_cm3": 0,
        "declared_value_threshold_cents": 0,
        "declared_value_rate": 0,
        "vehicles": {
            "sedan_suv": dict(sedan),
            "cargo_van": dict(DEFAULT_VEHICLE_MATRIX["cargo_van"]),
            "pickup": dict(DEFAULT_VEHICLE_MATRIX["pickup"]),
            "sprinter_van": dict(DEFAULT_VEHICLE_MATRIX["sprinter_van"]),
            "box_16": dict(box),
            "box_20": dict(DEFAULT_VEHICLE_MATRIX["box_20"]),
        },
    }


def customer_gta_from_dict(data: dict[str, Any] | None) -> GtaRateConfig:
    """Customer card only. Unknown vehicles are kept; missing ones are not filled from sedan."""
    raw = data if isinstance(data, dict) else default_customer_distance_dict()
    empty = GtaRateConfig(vehicles={}, strict_vehicles=True)
    card = gta_rate_config_from_dict(raw, base=empty)
    card.strict_vehicles = True
    card.vehicles = {
        key: rates
        for key, rates in card.vehicles.items()
        if key in CUSTOMER_VEHICLE_IDS
    }
    return card


def merge_merchant_gta_overlay(system: GtaRateConfig, merchant_config: dict[str, Any] | None) -> GtaRateConfig:
    """Apply merchant `pricing_config.gta_rate` over the platform Settings matrix."""
    cfg = merchant_config if isinstance(merchant_config, dict) else {}
    overlay = cfg.get("gta_rate")
    if not isinstance(overlay, dict) or not overlay:
        return system
    return gta_rate_config_from_dict(overlay, base=system)



def _canon_vehicle_key(value: str) -> str:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    compact = key.replace("_", "")
    return VEHICLE_ALIAS.get(key) or VEHICLE_ALIAS.get(compact) or key


def vehicle_classes_match(stored: str | None, requested: str | None) -> bool:
    """A saved suv or box_truck row still matches the merged catalog id."""
    if not stored:
        return True
    if not requested:
        return False
    if stored == requested:
        return True
    return _canon_vehicle_key(stored) == _canon_vehicle_key(requested)


def normalize_vehicle_type(vehicle_type: str, *, known: Mapping[str, Any] | None = None) -> str:
    matrix = known or DEFAULT_VEHICLE_MATRIX
    raw = (vehicle_type or "").strip()
    if not raw:
        raise ValueError("Invalid vehicle type selected.")
    key = raw.lower().replace("-", "_").replace(" ", "_")
    compact = key.replace("_", "")
    snake = "".join(f"_{c.lower()}" if c.isupper() else c for c in raw).lstrip("_").lower()
    candidates = [raw, key, compact, snake]
    for candidate in candidates:
        if candidate in matrix:
            return candidate
    for candidate in candidates:
        alias = VEHICLE_ALIAS.get(candidate) or VEHICLE_ALIAS.get(candidate.replace("_", ""))
        if alias and alias in matrix:
            return alias
    raise ValueError("Invalid vehicle type selected.")


# --- Location surcharges (FSA / city; not lat/lon boxes or street-name match) ---

# Downtown = City of Toronto "Downtown Plan" area (Bathurst St → Don River,
# lake → Bloor / Rosedale ravine), expressed as the FSAs that sit inside it,
# plus Canada Post large-receiver codes in the core (M5K/M5L/M5W/M5X).
DOWNTOWN_FSAS: frozenset[str] = frozenset(
    {
        "M4X",  # St. James Town / Cabbagetown
        "M4Y",  # Church and Wellesley
        "M5A",  # Regent Park / Harbourfront
        "M5B",  # Garden District
        "M5C",  # St. James Town (south)
        "M5E",  # Berczy Park
        "M5G",  # Central Bay Street
        "M5H",  # Richmond / Adelaide / King
        "M5J",  # Harbourfront East / Union Station / Islands
        "M5K",  # TD Centre (large receiver)
        "M5L",  # Commerce Court (large receiver)
        "M5S",  # University of Toronto / Harbord
        "M5T",  # Kensington Market / Chinatown
        "M5V",  # CN Tower / King West / Railway Lands
        "M5W",  # Stn A (large receiver)
        "M5X",  # First Canadian Place (large receiver)
    }
)

# Markham (Canada Post). L3T is Thornhill-east (Markham side of Yonge).
MARKHAM_FSAS: frozenset[str] = frozenset({"L3P", "L3R", "L3S", "L3T", "L6B", "L6C", "L6E", "L6G"})

# North York (Canada Post district name "North York").
NORTH_YORK_FSAS: frozenset[str] = frozenset(
    {
        "M2H", "M2J", "M2K", "M2L", "M2M", "M2N", "M2P", "M2R",
        "M3A", "M3B", "M3C", "M3H", "M3J", "M3K", "M3L", "M3M", "M3N",
        "M4A", "M5M", "M6A", "M6B", "M6L", "M9L", "M9M",
    }
)  # fmt: skip

UPPER_ZONE_FSAS: frozenset[str] = MARKHAM_FSAS | NORTH_YORK_FSAS


def _fsa_of(point: GeoPoint) -> str:
    from porterchain_pricing.components.fsa import fsa_from_point

    return fsa_from_point(point)


def _formatted_city_token(formatted: str, city: str) -> bool:
    """
    True when `city` is the locality segment of a comma-separated address
    ("…, Markham, ON L3R…"), never a street name ("600 Markham St, Toronto").
    """
    city = " ".join(city.lower().split())
    for raw in (formatted or "").lower().split(","):
        part = " ".join(raw.strip().split())
        if part == city:
            return True
        # "Markham ON" / "North York ON L…" when province shares the segment.
        if part.startswith(city + " "):
            rest = part[len(city) :].strip().split()
            if rest and rest[0] == "on":
                return True
    return False


def is_downtown_point(point: GeoPoint) -> bool:
    """True when the stop's FSA is in DOWNTOWN_FSAS (no lat/lon box, no text match)."""
    fsa = _fsa_of(point)
    return bool(fsa) and fsa in DOWNTOWN_FSAS


def is_upper_zone_point(point: GeoPoint) -> bool:
    """True when the stop is Markham or North York by FSA or city token."""
    fsa = _fsa_of(point)
    if fsa and fsa in UPPER_ZONE_FSAS:
        return True
    formatted = point.formatted or ""
    return _formatted_city_token(formatted, "markham") or _formatted_city_token(
        formatted, "north york"
    )


def detect_location_flags(
    pickup: GeoPoint,
    dropoff: GeoPoint,
    additional_stops: list[GeoPoint] | None = None,
) -> tuple[bool, bool]:
    stops = [pickup, dropoff, *(additional_stops or [])]
    downtown = any(is_downtown_point(s) for s in stops)
    upper = any(is_upper_zone_point(s) for s in stops)
    return downtown, upper

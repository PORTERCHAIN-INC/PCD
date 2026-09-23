"""
Per-merchant pricing policy, parsed out of `merchants.pricing_config`.

Three things a merchant can be set up with, independently of the platform
defaults: which model prices the trip, whether the geographic surcharges apply
to them, and a table of size / weight bands that add a surcharge.

Everything here is parsed defensively — `pricing_config` is a free-form JSON
column that predates this module, so a malformed value must degrade to the
platform default rather than break a quote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: How the base price is chosen for this merchant.
MODEL_AUTO = "auto"
MODEL_DISTANCE = "distance"
MODEL_FSA = "fsa"
PRICING_MODELS = (MODEL_AUTO, MODEL_DISTANCE, MODEL_FSA)

#: Admins enter tier limits in whatever unit they think in; we bill in cm / kg.
CM_PER_UNIT = {"cm": 1.0, "in": 2.54, "ft": 30.48}
KG_PER_UNIT = {"kg": 1.0, "lb": 0.45359237}

DIMENSION_UNITS = tuple(CM_PER_UNIT)
WEIGHT_UNITS = tuple(KG_PER_UNIT)


def _f(value: Any) -> float | None:
    """Positive float, or None when blank / unparseable. Blank means no limit."""
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out >= 0 else None


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _b(value: Any, default: bool) -> bool:
    return default if value is None else bool(value)


#: How size/weight tier limits combine when matching a shipment.
SIZE_MATCH_ALL = "all"
SIZE_MATCH_ANY = "any"
SIZE_MATCHES = (SIZE_MATCH_ALL, SIZE_MATCH_ANY)

#: When no FSA flat covers the destination.
FSA_MISS_FALLBACK = "fallback_distance"
FSA_MISS_REFUSE = "refuse"
FSA_MISS_MODES = (FSA_MISS_FALLBACK, FSA_MISS_REFUSE)


@dataclass
class CompactStopBand:
    """Bill this cents when billable stop count is ≤ max_stops (None = open-ended)."""

    cents: int = 0
    max_stops: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"cents": self.cents, "max_stops": self.max_stops}


@dataclass
class CompactSchedule:
    """Compact-vehicle stop banding (e.g. sedan/SUV territory rates)."""

    enabled: bool = False
    vehicle_classes: list[str] = field(default_factory=lambda: ["sedan_suv", "sedan", "suv"])
    max_packed_inches: tuple[float, float] = (10.0, 10.0)
    parcels_per_stop: int = 3
    stop_rates: list[CompactStopBand] = field(
        default_factory=lambda: [
            CompactStopBand(cents=1000, max_stops=4),
            CompactStopBand(cents=600, max_stops=None),
        ]
    )
    route_minimum_cents: int = 5000

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "vehicle_classes": list(self.vehicle_classes),
            "max_packed_inches": list(self.max_packed_inches),
            "parcels_per_stop": self.parcels_per_stop,
            "stop_rates_cents": [b.to_dict() for b in self.stop_rates],
            "route_minimum_cents": self.route_minimum_cents,
        }


@dataclass
class MerchantSchedule:
    """
    Commercial schedule knobs on `pricing_config.schedule`.

    Defaults preserve today's engine behavior for merchants with no schedule block.
    """

    fuel_surcharge_percent: float | None = None
    fsa_miss: str = FSA_MISS_FALLBACK
    origin_pickup_cents: int = 0
    origin_pickup_vehicle_classes: list[str] = field(default_factory=lambda: ["cargo_van"])
    route_minimums_cents: dict[str, int] = field(default_factory=dict)
    compact: CompactSchedule = field(default_factory=CompactSchedule)
    size_match: str = SIZE_MATCH_ALL

    def to_dict(self) -> dict[str, Any]:
        return {
            "fuel_surcharge_percent": self.fuel_surcharge_percent,
            "fsa_miss": self.fsa_miss,
            "origin_pickup_cents": self.origin_pickup_cents,
            "origin_pickup_vehicle_classes": list(self.origin_pickup_vehicle_classes),
            "route_minimums_cents": dict(self.route_minimums_cents),
            "compact": self.compact.to_dict(),
            "size_match": self.size_match,
        }


def _compact_from_dict(raw: Any) -> CompactSchedule:
    if not isinstance(raw, dict):
        return CompactSchedule()
    bands_raw = raw.get("stop_rates_cents") or raw.get("stop_rates") or []
    bands: list[CompactStopBand] = []
    if isinstance(bands_raw, list):
        for row in bands_raw:
            if not isinstance(row, dict):
                continue
            max_stops = row.get("max_stops")
            bands.append(
                CompactStopBand(
                    cents=max(_i(row.get("cents")), 0),
                    max_stops=None if max_stops is None else max(_i(max_stops), 0),
                )
            )
    packed = raw.get("max_packed_inches")
    if isinstance(packed, (list, tuple)) and len(packed) >= 2:
        try:
            packed_t = (float(packed[0]), float(packed[1]))
        except (TypeError, ValueError):
            packed_t = (10.0, 10.0)
    else:
        packed_t = (10.0, 10.0)
    classes = raw.get("vehicle_classes")
    return CompactSchedule(
        enabled=_b(raw.get("enabled"), False),
        vehicle_classes=(
            [str(c) for c in classes if c]
            if isinstance(classes, list)
            else ["sedan_suv", "sedan", "suv"]
        ),
        max_packed_inches=packed_t,
        parcels_per_stop=max(_i(raw.get("parcels_per_stop"), 3), 1),
        stop_rates=bands
        or [
            CompactStopBand(cents=1000, max_stops=4),
            CompactStopBand(cents=600, max_stops=None),
        ],
        route_minimum_cents=max(_i(raw.get("route_minimum_cents")), 0),
    )


def schedule_from_dict(raw: Any) -> MerchantSchedule:
    """Parse `pricing_config.schedule`; junk → defaults (today's behavior)."""
    if not isinstance(raw, dict):
        return MerchantSchedule()

    # Missing / null → no override (platform fuel). Number including 0 → override.
    if "fuel_surcharge_percent" not in raw or raw.get("fuel_surcharge_percent") is None:
        fuel: float | None = None
    else:
        try:
            fuel = float(raw["fuel_surcharge_percent"])
        except (TypeError, ValueError):
            fuel = None

    miss = str(raw.get("fsa_miss") or FSA_MISS_FALLBACK).lower()
    size_match = str(raw.get("size_match") or SIZE_MATCH_ALL).lower()
    vehicles = raw.get("origin_pickup_vehicle_classes")
    mins_raw = raw.get("route_minimums_cents")
    mins: dict[str, int] = {}
    if isinstance(mins_raw, dict):
        for k, v in mins_raw.items():
            if k is None:
                continue
            try:
                mins[str(k)] = max(int(v), 0)
            except (TypeError, ValueError):
                continue
    return MerchantSchedule(
        fuel_surcharge_percent=fuel,
        fsa_miss=miss if miss in FSA_MISS_MODES else FSA_MISS_FALLBACK,
        origin_pickup_cents=max(_i(raw.get("origin_pickup_cents")), 0),
        origin_pickup_vehicle_classes=(
            [str(c) for c in vehicles if c]
            if isinstance(vehicles, list)
            else ["cargo_van"]
        ),
        route_minimums_cents=mins,
        compact=_compact_from_dict(raw.get("compact")),
        size_match=size_match if size_match in SIZE_MATCHES else SIZE_MATCH_ALL,
    )


@dataclass
class SizeTier:
    """
    One row of a merchant's size / weight table.

    A limit left blank is unbounded, so a row with every limit blank is a
    catch-all. Limits are stored in the unit the admin typed them in and
    converted at quote time, so nothing is lost to rounding on the way back
    into the form.
    """

    surcharge_cents: int = 0
    label: str = ""
    max_length: float | None = None
    max_width: float | None = None
    max_height: float | None = None
    dimension_unit: str = "cm"
    max_weight: float | None = None
    weight_unit: str = "kg"

    def _to_cm(self, value: float | None) -> float | None:
        if value is None:
            return None
        return value * CM_PER_UNIT.get(self.dimension_unit, 1.0)

    def limits_cm(self) -> tuple[float | None, float | None, float | None]:
        return (self._to_cm(self.max_length), self._to_cm(self.max_width), self._to_cm(self.max_height))

    def limit_kg(self) -> float | None:
        if self.max_weight is None:
            return None
        return self.max_weight * KG_PER_UNIT.get(self.weight_unit, 1.0)

    def accepts(
        self,
        *,
        length_cm: float | None,
        width_cm: float | None,
        height_cm: float | None,
        weight_kg: float | None,
        size_match: str = SIZE_MATCH_ALL,
    ) -> bool:
        """
        True when the shipment fits this row's limits.

        `size_match=all` (default): every set limit must pass (AND).
        `size_match=any`: weight within its limit OR two-longest-sides footprint
        within the two longest tier limits (OR). Unknown shipment values never
        fail a limit (omit a dim → that check does not block).
        """
        weight_ok = self._weight_ok(weight_kg)
        dims_ok = self._dims_ok(length_cm, width_cm, height_cm)
        footprint_ok = self._footprint_ok(length_cm, width_cm, height_cm)

        if size_match == SIZE_MATCH_ANY:
            # OR of weight vs footprint when both axis families have limits;
            # if only one family is set, that family alone decides.
            has_weight_limit = self.limit_kg() is not None
            has_footprint_limit = any(x is not None for x in self.limits_cm())
            if has_weight_limit and has_footprint_limit:
                return weight_ok or footprint_ok
            if has_weight_limit:
                return weight_ok
            if has_footprint_limit:
                return footprint_ok
            return True

        return weight_ok and dims_ok

    def _weight_ok(self, weight_kg: float | None) -> bool:
        weight_limit = self.limit_kg()
        if weight_limit is not None and weight_kg is not None and weight_kg > weight_limit:
            return False
        return True

    def _dims_ok(
        self,
        length_cm: float | None,
        width_cm: float | None,
        height_cm: float | None,
    ) -> bool:
        for limit, actual in zip(self.limits_cm(), (length_cm, width_cm, height_cm)):
            if limit is not None and actual is not None and actual > limit:
                return False
        return True

    def _footprint_ok(
        self,
        length_cm: float | None,
        width_cm: float | None,
        height_cm: float | None,
    ) -> bool:
        """
        Two longest shipment sides vs two longest set tier limits (cm).
        Missing shipment sides that would be needed do not fail the check.
        """
        limits = sorted((x for x in self.limits_cm() if x is not None), reverse=True)
        if not limits:
            return True
        sides = sorted(
            (x for x in (length_cm, width_cm, height_cm) if x is not None),
            reverse=True,
        )
        if not sides:
            return True
        for limit, actual in zip(limits[:2], sides[:2]):
            if actual > limit:
                return False
        return True

    def describe(self) -> str:
        if self.label:
            return self.label
        dims = [d for d in (self.max_length, self.max_width, self.max_height) if d is not None]
        parts = []
        if dims:
            parts.append("×".join(f"{d:g}" for d in dims) + f" {self.dimension_unit}")
        if self.max_weight is not None:
            parts.append(f"{self.max_weight:g} {self.weight_unit}")
        return "Up to " + ", ".join(parts) if parts else "Any size"

    def to_dict(self) -> dict[str, Any]:
        return {
            "surcharge_cents": self.surcharge_cents,
            "label": self.label,
            "max_length": self.max_length,
            "max_width": self.max_width,
            "max_height": self.max_height,
            "dimension_unit": self.dimension_unit,
            "max_weight": self.max_weight,
            "weight_unit": self.weight_unit,
        }


def size_tier_from_dict(raw: Any) -> SizeTier | None:
    if not isinstance(raw, dict):
        return None
    dimension_unit = str(raw.get("dimension_unit") or "cm").lower()
    weight_unit = str(raw.get("weight_unit") or "kg").lower()
    return SizeTier(
        surcharge_cents=max(_i(raw.get("surcharge_cents")), 0),
        label=str(raw.get("label") or ""),
        max_length=_f(raw.get("max_length")),
        max_width=_f(raw.get("max_width")),
        max_height=_f(raw.get("max_height")),
        dimension_unit=dimension_unit if dimension_unit in CM_PER_UNIT else "cm",
        max_weight=_f(raw.get("max_weight")),
        weight_unit=weight_unit if weight_unit in KG_PER_UNIT else "kg",
    )


@dataclass
class MerchantPricingPolicy:
    """Platform defaults until a merchant is configured otherwise."""

    pricing_model: str = MODEL_AUTO
    charge_downtown: bool = True
    charge_upper_zone: bool = True
    size_tiers: list[SizeTier] = field(default_factory=list)
    schedule: MerchantSchedule = field(default_factory=MerchantSchedule)

    @property
    def suppresses_location_fees(self) -> bool:
        return not (self.charge_downtown and self.charge_upper_zone)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pricing_model": self.pricing_model,
            "surcharges": {
                "downtown": self.charge_downtown,
                "upper_zone": self.charge_upper_zone,
            },
            "size_tiers": [t.to_dict() for t in self.size_tiers],
            "schedule": self.schedule.to_dict(),
        }


def policy_from_config(config: dict[str, Any] | None) -> MerchantPricingPolicy:
    """Read the policy out of a merchant's `pricing_config`, ignoring junk."""
    cfg = config if isinstance(config, dict) else {}

    model = str(cfg.get("pricing_model") or MODEL_AUTO).lower()
    surcharges = cfg.get("surcharges")
    surcharges = surcharges if isinstance(surcharges, dict) else {}

    tiers_raw = cfg.get("size_tiers")
    tiers = [t for t in (size_tier_from_dict(r) for r in tiers_raw) if t] if isinstance(tiers_raw, list) else []

    return MerchantPricingPolicy(
        pricing_model=model if model in PRICING_MODELS else MODEL_AUTO,
        charge_downtown=_b(surcharges.get("downtown"), True),
        charge_upper_zone=_b(surcharges.get("upper_zone"), True),
        size_tiers=tiers,
        schedule=schedule_from_dict(cfg.get("schedule")),
    )

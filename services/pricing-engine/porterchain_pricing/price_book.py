"""
Price book — the global, super-admin-edited price settings (`system_config`
key `pricing_book`) plus each merchant's overrides in
`pricing_config.price_book`.

One engine: `PricingEngine.calculate` reads the book through `ctx.price_book`.
Contract schedules (Kaylulu) always win and never read it. Every switch that
changes a price starts OFF, so saving these defaults changes no existing quote:

* `merchant_parcels.enabled` — parcel quantity tiers, small-parcel rule and
  handling tiers for non-contract merchants (a merchant can turn it on alone).
* `retail.enabled` — one fixed customer price instead of the distance card.
* `dedicated.enabled` — whole-vehicle bookings priced per hour / half-day.

Money is integer cents. Sizes are inches and pounds as written in the contract
PDF. Values listed in `PLACEHOLDER_PATHS` are EXAMPLE numbers from the plan,
not decided prices — every one is editable in Settings.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any

from porterchain_pricing.contract_schedule import (
    HandlingTier,
    fits,
    footprint_cm,
    handling_tier_for,
    handling_tiers_from_dict,
)
from porterchain_pricing.policy import CM_PER_UNIT, KG_PER_UNIT

#: Vehicle classes judged by the compact small-parcel size (else the van size).
COMPACT_CLASSES = frozenset({"sedan_suv", "sedan", "suv", "car"})

SMALL_FREE = "free"
SMALL_PER_GROUP = "per_group"
SMALL_MODES = (SMALL_FREE, SMALL_PER_GROUP)

UNIT_HOUR = "hour"
UNIT_HALF_DAY = "half_day"
DEDICATED_UNITS = (UNIT_HOUR, UNIT_HALF_DAY)

MIN_PER_ROUTE = "per_route"
MIN_PER_STOP = "per_stop"
MINIMUM_MODES = (MIN_PER_ROUTE, MIN_PER_STOP)

#: Dotted paths whose default is an EXAMPLE value awaiting a pricing decision.
PLACEHOLDER_PATHS: tuple[str, ...] = (
    "stop_price_cents",
    "parcel_tiers",
    "small_parcel.max_lb",
    "small_parcel.charge_mode",
    "minimum.cents",
    "minimum.mode",
    "retail.fixed_price_cents",
    "retail.included_parcels",
    "retail.extra_parcel_cents",
    "dedicated.unit",
    "dedicated.vehicles",
)

_DEFAULT_BOOK: dict[str, Any] = {
    "schema": 1,
    "merchant_parcels": {"enabled": False},
    # FSA merchants: price when no FSA row matches. Distance merchants use the card.
    "stop_price_cents": 2000,
    # Billable units at one stop pick the tier; every unit is charged that tier's rate.
    "parcel_tiers": [
        {"max_parcels": 5, "cents_per_parcel": 400, "custom_quote": False},
        {"max_parcels": 10, "cents_per_parcel": 350, "custom_quote": False},
        {"max_parcels": 20, "cents_per_parcel": 300, "custom_quote": False},
        {"max_parcels": None, "cents_per_parcel": 0, "custom_quote": True},
    ],
    # Kaylulu contract sizes: compact 10"×10", van 12"×12", 3 small parcels per group.
    "small_parcel": {
        "compact_max_in": [10, 10],
        "van_max_in": [12, 12],
        "max_lb": 10,
        "group_size": 3,
        "charge_mode": SMALL_FREE,
    },
    # Kaylulu contract handling tiers: higher of weight or footprint, no stacking.
    "handling": {
        "weight_unit": "lb",
        "dimension_unit": "in",
        "tiers": [
            {"code": "standard", "max_weight": 100, "max_footprint": [70, 45], "surcharge_cents": 0},
            {"code": "handling_1", "max_weight": 125, "max_footprint": [80, 45], "surcharge_cents": 3000},
            {"code": "handling_2", "max_weight": 150, "max_footprint": [90, 50], "surcharge_cents": 6000},
        ],
        "beyond": "custom_quote",
    },
    "minimum": {"cents": 6000, "mode": MIN_PER_ROUTE},
    "retail": {
        "enabled": False,
        "fixed_price_cents": 4500,
        "included_parcels": 5,
        "extra_parcel_cents": 500,
    },
    "dedicated": {
        "enabled": False,
        "unit": UNIT_HALF_DAY,
        "block_hours": 4,
        "min_units": 1,
        "vehicles": {
            "sedan_suv": {"hour_cents": 4500, "half_day_cents": 16000},
            "cargo_van": {"hour_cents": 6500, "half_day_cents": 24000},
            "sprinter_van": {"hour_cents": 7500, "half_day_cents": 28000},
            "box_16": {"hour_cents": 12500, "half_day_cents": 45000},
        },
    },
    # Per merchant only (pricing_config.price_book); OFF unless the merchant opts in.
    "multi_box_as_one_item": False,
}

#: Keys a merchant may override in `pricing_config.price_book`. Retail is global.
MERCHANT_OVERRIDE_KEYS = frozenset(
    {
        "enabled",
        "multi_box_as_one_item",
        "stop_price_cents",
        "parcel_tiers",
        "small_parcel",
        "handling",
        "minimum",
        "dedicated",
    }
)


def default_price_book() -> dict[str, Any]:
    return copy.deepcopy(_DEFAULT_BOOK)


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (over or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _cents(value: Any, path: str) -> int:
    try:
        cents = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"price_book_invalid:{path}") from exc
    if cents < 0:
        raise ValueError(f"price_book_invalid:{path}")
    return cents


def _pair(value: Any, path: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"price_book_invalid:{path}")
    try:
        out = [float(value[0]), float(value[1])]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"price_book_invalid:{path}") from exc
    if min(out) <= 0:
        raise ValueError(f"price_book_invalid:{path}")
    return out


def normalize_price_book(raw: Any) -> dict[str, Any]:
    """Defaults + `raw`, validated. Raises ValueError('price_book_invalid:<path>')."""
    book = _deep_merge(_DEFAULT_BOOK, raw if isinstance(raw, dict) else {})
    book["schema"] = 1
    book["merchant_parcels"] = {"enabled": bool((book.get("merchant_parcels") or {}).get("enabled"))}
    book["stop_price_cents"] = _cents(book.get("stop_price_cents"), "stop_price_cents")
    book["multi_box_as_one_item"] = bool(book.get("multi_box_as_one_item"))

    tiers_raw = book.get("parcel_tiers")
    if not isinstance(tiers_raw, list) or not tiers_raw or len(tiers_raw) > 8:
        raise ValueError("price_book_invalid:parcel_tiers")
    tiers: list[dict[str, Any]] = []
    for i, row in enumerate(tiers_raw):
        if not isinstance(row, dict):
            raise ValueError(f"price_book_invalid:parcel_tiers.{i}")
        cap = row.get("max_parcels")
        tiers.append(
            {
                "max_parcels": None if cap in (None, "") else max(1, _cents(cap, f"parcel_tiers.{i}.max_parcels")),
                "cents_per_parcel": _cents(row.get("cents_per_parcel", 0), f"parcel_tiers.{i}.cents_per_parcel"),
                "custom_quote": bool(row.get("custom_quote")),
            }
        )
    tiers.sort(key=lambda t: (t["max_parcels"] is None, t["max_parcels"] or 0))
    if tiers[-1]["max_parcels"] is not None:
        raise ValueError("price_book_invalid:parcel_tiers.open_tier_required")
    if sum(1 for t in tiers if t["max_parcels"] is None) != 1:
        raise ValueError("price_book_invalid:parcel_tiers.one_open_tier")
    book["parcel_tiers"] = tiers

    small = book.get("small_parcel") or {}
    mode = str(small.get("charge_mode") or SMALL_FREE)
    if mode not in SMALL_MODES:
        raise ValueError("price_book_invalid:small_parcel.charge_mode")
    max_lb = small.get("max_lb")
    book["small_parcel"] = {
        "compact_max_in": _pair(small.get("compact_max_in"), "small_parcel.compact_max_in"),
        "van_max_in": _pair(small.get("van_max_in"), "small_parcel.van_max_in"),
        "max_lb": None if max_lb in (None, "") else float(max_lb),
        "group_size": max(1, _cents(small.get("group_size", 3), "small_parcel.group_size")),
        "charge_mode": mode,
    }

    handling = book.get("handling") or {}
    try:
        parsed = handling_tiers_from_dict(handling)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("price_book_invalid:handling") from exc
    if not parsed or len(parsed) > 6:
        raise ValueError("price_book_invalid:handling.tiers")

    minimum = book.get("minimum") or {}
    min_mode = str(minimum.get("mode") or MIN_PER_ROUTE)
    if min_mode not in MINIMUM_MODES:
        raise ValueError("price_book_invalid:minimum.mode")
    book["minimum"] = {"cents": _cents(minimum.get("cents", 0), "minimum.cents"), "mode": min_mode}

    retail = book.get("retail") or {}
    book["retail"] = {
        "enabled": bool(retail.get("enabled")),
        "fixed_price_cents": _cents(retail.get("fixed_price_cents", 0), "retail.fixed_price_cents"),
        "included_parcels": max(1, _cents(retail.get("included_parcels", 1), "retail.included_parcels")),
        "extra_parcel_cents": _cents(retail.get("extra_parcel_cents", 0), "retail.extra_parcel_cents"),
    }
    if book["retail"]["enabled"] and book["retail"]["fixed_price_cents"] <= 0:
        raise ValueError("price_book_invalid:retail.fixed_price_cents")

    ded = book.get("dedicated") or {}
    unit = str(ded.get("unit") or UNIT_HALF_DAY)
    if unit not in DEDICATED_UNITS:
        raise ValueError("price_book_invalid:dedicated.unit")
    vehicles: dict[str, dict[str, int]] = {}
    for vid, row in (ded.get("vehicles") or {}).items():
        row = row if isinstance(row, dict) else {}
        vehicles[str(vid)] = {
            "hour_cents": _cents(row.get("hour_cents", 0), f"dedicated.vehicles.{vid}.hour_cents"),
            "half_day_cents": _cents(row.get("half_day_cents", 0), f"dedicated.vehicles.{vid}.half_day_cents"),
        }
    book["dedicated"] = {
        "enabled": bool(ded.get("enabled")),
        "unit": unit,
        "block_hours": max(1.0, float(ded.get("block_hours") or 4)),
        "min_units": max(1, _cents(ded.get("min_units", 1), "dedicated.min_units")),
        "vehicles": vehicles,
    }
    book["handling"] = {
        "weight_unit": handling.get("weight_unit", "lb"),
        "dimension_unit": handling.get("dimension_unit", "in"),
        "tiers": [
            {
                "code": str(t["code"]),
                "max_weight": float(t["max_weight"]),
                "max_footprint": _pair(t["max_footprint"], "handling.max_footprint"),
                "surcharge_cents": _cents(t["surcharge_cents"], "handling.surcharge_cents"),
            }
            for t in handling["tiers"]
        ],
        "beyond": "custom_quote",
    }
    return {key: book[key] for key in _DEFAULT_BOOK}


def merchant_overrides(merchant_cfg: dict[str, Any] | None) -> dict[str, Any]:
    raw = (merchant_cfg or {}).get("price_book") if isinstance(merchant_cfg, dict) else None
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in MERCHANT_OVERRIDE_KEYS}


def effective_price_book(global_raw: Any, merchant_cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Global book with this merchant's overrides on top (validated)."""
    book = normalize_price_book(global_raw)
    over = merchant_overrides(merchant_cfg)
    if not over:
        return book
    merged = _deep_merge(book, {k: v for k, v in over.items() if k != "enabled"})
    out = normalize_price_book(merged)
    if "enabled" in over:
        out["merchant_parcels"] = {"enabled": bool(over["enabled"])}
    return out


# ----------------------------------------------------------------- calculation


@dataclass(frozen=True)
class BookParcel:
    """One physical box. `item_key` groups the boxes of one item."""

    stop_index: int
    weight_kg: float | None
    dims_cm: tuple[float | None, float | None, float | None]
    item_key: str | None = None


@dataclass(frozen=True)
class StopUnits:
    stop_index: int
    small_boxes: int
    small_units: int
    full_units: int
    handling_cents: int
    handling_codes: tuple[str, ...]

    @property
    def billable_units(self) -> int:
        return self.small_units + self.full_units


@dataclass(frozen=True)
class ParcelCharge:
    """Price-book parcel charges for a route, or a custom-quote refusal."""

    stops: tuple[StopUnits, ...]
    parcel_cents: int
    handling_cents: int
    tier_rates: tuple[int, ...]
    custom_quote_reason: str = ""


def _small_limit_cm(book: dict[str, Any], vehicle_class: str) -> tuple[float, float]:
    small = book["small_parcel"]
    key = "compact_max_in" if str(vehicle_class or "").lower() in COMPACT_CLASSES else "van_max_in"
    a, b = small[key]
    return (a * CM_PER_UNIT["in"], b * CM_PER_UNIT["in"])


def _is_small(book: dict[str, Any], parcel: BookParcel, limit_cm: tuple[float, float]) -> bool:
    fp = footprint_cm(parcel.dims_cm)
    if fp is None or not fits(fp, limit_cm):
        return False
    max_lb = book["small_parcel"].get("max_lb")
    if max_lb is not None and parcel.weight_kg is not None:
        return parcel.weight_kg <= float(max_lb) * KG_PER_UNIT["lb"] + 1e-6
    return True


def tier_for(book: dict[str, Any], units: int) -> dict[str, Any]:
    for tier in book["parcel_tiers"]:
        if tier["max_parcels"] is None or units <= tier["max_parcels"]:
            return tier
    return book["parcel_tiers"][-1]


def price_parcels(
    book: dict[str, Any],
    parcels: list[BookParcel],
    *,
    vehicle_class: str,
    multi_box_as_one_item: bool,
    n_stops: int,
) -> ParcelCharge:
    """
    Parcel units and charges per stop.

    * Small box (fits the class size and weight): grouped `group_size` per unit;
      `free` mode bills no unit for them, `per_group` one unit per group.
    * Any other box is one unit — or, with multi-box ON, every box sharing an
      `item_key` at the stop is one unit together.
    * Each box is judged for handling on its own (it is lifted on its own);
      beyond the last tier is a custom quote for the whole route.
    * The billable count at a stop picks the quantity tier; its rate applies to
      every billable unit there. A custom-quote tier refuses the route.
    """
    handling = handling_tiers_from_dict(book["handling"])
    limit = _small_limit_cm(book, vehicle_class)
    small_cfg = book["small_parcel"]
    stops: list[StopUnits] = []
    rates: list[int] = []
    parcel_cents = 0
    handling_total = 0
    for idx in range(max(n_stops, 1)):
        here = [p for p in parcels if p.stop_index == idx]
        small = 0
        full_units = 0
        items_seen: set[str] = set()
        h_cents = 0
        codes: list[str] = []
        for parcel in here:
            tier: HandlingTier | None = handling_tier_for(handling, parcel.weight_kg, parcel.dims_cm)
            if tier is None:
                return ParcelCharge((), 0, 0, (), custom_quote_reason="handling_beyond_last_tier")
            if tier.surcharge_cents:
                h_cents += tier.surcharge_cents
                codes.append(tier.code)
            grouped_item = multi_box_as_one_item and parcel.item_key
            if not grouped_item and tier.surcharge_cents == 0 and _is_small(book, parcel, limit):
                small += 1
                continue
            if grouped_item:
                if parcel.item_key in items_seen:
                    continue
                items_seen.add(str(parcel.item_key))
            full_units += 1
        small_units = 0
        if small and small_cfg["charge_mode"] == SMALL_PER_GROUP:
            small_units = math.ceil(small / small_cfg["group_size"])
        row = StopUnits(idx, small, small_units, full_units, h_cents, tuple(codes))
        units = row.billable_units
        if units:
            tier_row = tier_for(book, units)
            if tier_row["custom_quote"]:
                return ParcelCharge((), 0, 0, (), custom_quote_reason="parcel_quantity_custom_quote")
            rates.append(int(tier_row["cents_per_parcel"]))
            parcel_cents += units * int(tier_row["cents_per_parcel"])
        else:
            rates.append(0)
        handling_total += h_cents
        stops.append(row)
    return ParcelCharge(tuple(stops), parcel_cents, handling_total, tuple(rates))


def dedicated_charge(
    book: dict[str, Any], vehicle_class: str, hours: float | None
) -> tuple[int, int, str] | None:
    """(cents, units, unit) for a whole-vehicle booking, or None when not priced here."""
    ded = book["dedicated"]
    if not ded["enabled"]:
        return None
    row = ded["vehicles"].get(str(vehicle_class or "").lower())
    if not row:
        return None
    unit = ded["unit"]
    rate = row["hour_cents"] if unit == UNIT_HOUR else row["half_day_cents"]
    if rate <= 0:
        return None
    if hours and hours > 0:
        units = math.ceil(hours) if unit == UNIT_HOUR else math.ceil(hours / ded["block_hours"])
    else:
        units = 0
    units = max(units, ded["min_units"])
    return rate * units, units, unit


def retail_charge(book: dict[str, Any], parcel_count: int) -> int | None:
    retail = book["retail"]
    if not retail["enabled"]:
        return None
    extra = max(int(parcel_count or 1) - retail["included_parcels"], 0)
    return retail["fixed_price_cents"] + extra * retail["extra_parcel_cents"]

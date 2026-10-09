"""Kaylulu pricing_config template — values come from the checked-in contract schedule.

Used by ``apply_kaylulu_schedule.py`` and the admin "Apply Kaylulu template"
action. The engine prices Kaylulu routes from
``porterchain_pricing/data/kaylulu_schedule_2026_09.json`` (named by
``schedule.contract_schedule``); the schedule fields copied here only keep the
admin form and rate-card preview truthful.
"""

from __future__ import annotations

from typing import Any

from porterchain_pricing.contract_schedule import raw_contract_schedule

# Prod Kaylulu merchant id (verify on staging/prod — often absent from local DB).
DEFAULT_KAYLULU_MERCHANT_ID = "8a1704f3-eaa1-46bb-a848-0ccb5d38f870"

KAYLULU_CONTRACT_SCHEDULE_ID = "kaylulu-2026-09"

_RAW = raw_contract_schedule(KAYLULU_CONTRACT_SCHEDULE_ID)
_VAN = _RAW["van"]
_COMPACT = _RAW["compact"]
_HANDLING = _RAW["handling"]

KAYLULU_SCHEDULE: dict[str, Any] = {
    "contract_schedule": KAYLULU_CONTRACT_SCHEDULE_ID,
    "fuel_surcharge_percent": 0,
    "fsa_miss": "refuse",
    "origin_pickup_cents": _VAN["pickup_cents"],
    "origin_pickup_vehicle_classes": ["cargo_van"],
    "route_minimums_cents": {t["code"]: t["route_minimum_cents"] for t in _VAN["tiers"]},
    "compact": {
        "enabled": True,
        "vehicle_classes": list(_COMPACT["vehicle_classes"]),
        "max_packed_inches": list(_COMPACT["max_packed_inches"]),
        "parcels_per_stop": _COMPACT["parcels_per_stop"],
        "stop_rates_cents": [
            {"max_stops": b["max_stops"], "cents": b["stop_cents"]} for b in _COMPACT["bands"]
        ],
        "route_minimum_cents": _COMPACT["route_minimum_cents"],
    },
    "size_match": "all",
}

# A3 Heavy-Item Handling, for display. The contract path assigns the tier per
# parcel from the schedule (higher of weight and footprint); beyond Tier 2 is a
# custom quotation and refuses the route.
KAYLULU_SIZE_TIERS: list[dict[str, Any]] = [
    {
        "label": "Standard" if i == 0 else f"Handling Tier {i}",
        "surcharge_cents": t["surcharge_cents"],
        "max_length": t["max_footprint"][0],
        "max_width": t["max_footprint"][1],
        "max_height": None,
        "dimension_unit": _HANDLING["dimension_unit"],
        "max_weight": t["max_weight"],
        "weight_unit": _HANDLING["weight_unit"],
    }
    for i, t in enumerate(_HANDLING["tiers"])
] + [
    {
        "label": f"Handling Tier {len(_HANDLING['tiers'])} — custom quotation",
        "surcharge_cents": 0,
        "max_length": None,
        "max_width": None,
        "max_height": None,
        "dimension_unit": _HANDLING["dimension_unit"],
        "max_weight": None,
        "weight_unit": _HANDLING["weight_unit"],
    }
]

# Van stop rates → geographic tier tags on legacy FSA rows.
FLAT_TO_TIER: dict[int, str] = {t["stop_cents"]: t["code"] for t in _VAN["tiers"]}


def kaylulu_pricing_config(*, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge the Kaylulu schedule, handling tiers and surcharge opt-outs into pricing_config."""
    cfg = dict(existing or {})
    cfg["schedule"] = {**KAYLULU_SCHEDULE, "compact": dict(KAYLULU_SCHEDULE["compact"])}
    cfg["size_tiers"] = [dict(t) for t in KAYLULU_SIZE_TIERS]
    # The contract prices location; no downtown / upper-zone surcharge on top.
    cfg["surcharges"] = {"downtown": False, "upper_zone": False}
    return cfg

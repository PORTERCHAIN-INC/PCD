"""Kaylulu commercial schedule + A3 handling tiers — data template, not engine forks.

Used by ``apply_kaylulu_schedule.py`` and admin clone / Load Kaylulu presets.
PDF A3: Standard / Handling Tier 1–3; either weight or footprint triggers;
``size_match=any`` + highest-surcharge wins among fits.
"""

from __future__ import annotations

from typing import Any

# Prod Kaylulu merchant id (verify on staging/prod — often absent from local DB).
DEFAULT_KAYLULU_MERCHANT_ID = "8a1704f3-eaa1-46bb-a848-0ccb5d38f870"

KAYLULU_SCHEDULE: dict[str, Any] = {
    "fuel_surcharge_percent": 0,
    "fsa_miss": "refuse",
    "origin_pickup_cents": 4000,
    "origin_pickup_vehicle_classes": ["cargo_van"],
    "route_minimums_cents": {"T1": 12000, "T2": 20000, "T3": 25000},
    "compact": {
        "enabled": True,
        "vehicle_classes": ["sedan_suv"],
        "max_packed_inches": [10, 10],
        "parcels_per_stop": 3,
        "stop_rates_cents": [
            {"max_stops": 4, "cents": 1000},
            {"max_stops": None, "cents": 600},
        ],
        "route_minimum_cents": 5000,
    },
    "size_match": "any",
}

# PDF A3 Heavy-Item Handling — inches + lb; surcharge on geographic stop.
# Tier 3 is catch-all (custom quotation) — $0 auto so ops quote manually.
KAYLULU_SIZE_TIERS: list[dict[str, Any]] = [
    {
        "label": "Standard",
        "surcharge_cents": 0,
        "max_length": 70,
        "max_width": 45,
        "max_height": None,
        "dimension_unit": "in",
        "max_weight": 100,
        "weight_unit": "lb",
    },
    {
        "label": "Handling Tier 1",
        "surcharge_cents": 3000,
        "max_length": 80,
        "max_width": 45,
        "max_height": None,
        "dimension_unit": "in",
        "max_weight": 125,
        "weight_unit": "lb",
    },
    {
        "label": "Handling Tier 2",
        "surcharge_cents": 6000,
        "max_length": 90,
        "max_width": 50,
        "max_height": None,
        "dimension_unit": "in",
        "max_weight": 150,
        "weight_unit": "lb",
    },
    {
        "label": "Handling Tier 3 — custom quotation",
        "surcharge_cents": 0,
        "max_length": None,
        "max_width": None,
        "max_height": None,
        "dimension_unit": "in",
        "max_weight": None,
        "weight_unit": "lb",
    },
]

# PDF van flats → geographic tier tags on FSA rows
FLAT_TO_TIER: dict[int, str] = {
    3000: "T1",
    4500: "T2",
    6000: "T3",
}


def kaylulu_pricing_config(*, existing: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge Kaylulu schedule + A3 size_tiers into a pricing_config dict."""
    cfg = dict(existing or {})
    cfg["schedule"] = dict(KAYLULU_SCHEDULE)
    cfg["size_tiers"] = [dict(t) for t in KAYLULU_SIZE_TIERS]
    return cfg

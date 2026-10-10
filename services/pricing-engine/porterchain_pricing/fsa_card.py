"""FSA rate card math: drive distance + time from one pickup → one clean price per drop FSA.

Pure functions. Routing (Valhalla / OSRM) and storage live in the API
(`porterchain_api.pricing_engine.fsa_rate_card`); parcel tiers, handling (size)
charges and the route minimum stay in the price book so checkout and the card
are priced by the same PricingEngine.

Settings → `pricing_fsa_card` (super_admin). Money in cents.
"""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any

from porterchain_pricing.gta_rate import DOWNTOWN_FSAS

_DEFAULT_CARD: dict[str, Any] = {
    "base_cents": 1200,
    "per_km_cents": 85,
    "per_minute_cents": 30,
    # Dense core: slower stops, parking, towers. Applied to the drop FSA.
    "downtown_uplift_pct": 20.0,
    "downtown_fsas": sorted(DOWNTOWN_FSAS),
    # Floor per drop before banding.
    "minimum_cents": 1800,
    # Round *up* into clean bands: $1 steps under $40, then $5 steps.
    "bands": [
        {"below_cents": 4000, "step_cents": 100},
        {"below_cents": None, "step_cents": 500},
    ],
    # Drop FSAs whose centroid is farther than this from the Toronto hub are off the
    # card. Defaults to the service radius (gta150_fsa.service_radius_km); editable.
    "radius_km": None,
    # Parcel counts shown as columns (the price-book tiers bill them).
    "tier_columns": [5, 10, 20],
}


def default_fsa_card() -> dict[str, Any]:
    from porterchain_pricing.gta150_fsa import service_radius_km

    card = deepcopy(_DEFAULT_CARD)
    card["radius_km"] = service_radius_km()
    return card


def normalize_fsa_card(raw: Any) -> dict[str, Any]:
    """Defaults + `raw`, validated. Raises ValueError('fsa_card_invalid:<key>')."""
    card = default_fsa_card()
    if isinstance(raw, dict):
        card.update({k: deepcopy(v) for k, v in raw.items() if k in _DEFAULT_CARD and v is not None})
    for key in ("base_cents", "per_km_cents", "per_minute_cents", "minimum_cents"):
        if not isinstance(card[key], int) or card[key] < 0:
            raise ValueError(f"fsa_card_invalid:{key}")
    for key in ("downtown_uplift_pct", "radius_km"):
        if not isinstance(card[key], (int, float)) or card[key] < 0:
            raise ValueError(f"fsa_card_invalid:{key}")
    bands = card["bands"]
    if not isinstance(bands, list) or not bands or bands[-1].get("below_cents") is not None:
        raise ValueError("fsa_card_invalid:bands")
    if any(int(b.get("step_cents") or 0) <= 0 for b in bands):
        raise ValueError("fsa_card_invalid:bands")
    cols = card["tier_columns"]
    if not isinstance(cols, list) or not all(isinstance(c, int) and c > 0 for c in cols):
        raise ValueError("fsa_card_invalid:tier_columns")
    card["tier_columns"] = sorted(set(cols))
    card["downtown_fsas"] = sorted({str(f).strip().upper()[:3] for f in card["downtown_fsas"]})
    return card


def band_cents(cents: int, card: dict[str, Any]) -> int:
    """Round up to the band step that covers this amount ($18.40 → $19, $43 → $45)."""
    for band in card["bands"]:
        below = band.get("below_cents")
        if below is None or cents < below:
            step = int(band["step_cents"])
            return int(math.ceil(cents / step) * step)
    return cents  # unreachable: the last band is open-ended


def drop_price_cents(km: float, minutes: float, dest_fsa: str, card: dict[str, Any]) -> int:
    """One drop (1 parcel) from the merchant pickup to `dest_fsa`: base + km + minutes,
    downtown uplift, minimum, then banded."""
    raw = card["base_cents"] + card["per_km_cents"] * km + card["per_minute_cents"] * minutes
    if dest_fsa.upper() in card["downtown_fsas"]:
        raw *= 1 + float(card["downtown_uplift_pct"]) / 100.0
    return band_cents(max(int(round(raw)), int(card["minimum_cents"])), card)

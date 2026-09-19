"""GTA ±150 km FSA registry — service-area SoT for the Valhalla tile.

`is_ontario_fsa` remains a weak postal-district check (K/L/M/N/P). Coverage,
booking gates, and FSA pricing seeds must use `is_gta150_fsa` / this registry
so Ottawa / Sudbury / Northern Ontario are not silently treated as in-tile.

Artifact: `porterchain_pricing/data/gta150_fsa_registry.json`
Regenerate: `python scripts/build_gta150_fsa_registry.py`
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from porterchain_pricing.components.fsa import normalize_fsa

_REGISTRY_PATH = Path(__file__).resolve().parent / "data" / "gta150_fsa_registry.json"

# Canada Post large-receiver / non-geographic FSAs in downtown Toronto. StatsCan
# 2021 FSA polygons often omit these; they are still valid pickup/dropoff codes
# inside the Valhalla GTA ±150 km hub (e.g. M5X = First Canadian Place).
_GTA150_HUB_OVERRIDES: frozenset[str] = frozenset({"M5D", "M5K", "M5L", "M5W", "M5X"})
_HUB_CENTROID = {"lat": 43.6488, "lng": -79.3817}


@lru_cache(maxsize=1)
def load_gta150_registry() -> dict[str, Any]:
    data = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("fsas"), list):
        raise RuntimeError("gta150_fsa_registry_invalid")
    return data


@lru_cache(maxsize=1)
def gta150_fsa_codes() -> frozenset[str]:
    codes = {
        normalize_fsa(str(row.get("code") or ""))
        for row in load_gta150_registry().get("fsas", [])
        if isinstance(row, dict) and row.get("active", True)
    }
    return frozenset(c for c in codes if c) | _GTA150_HUB_OVERRIDES


def is_gta150_fsa(fsa: str | None) -> bool:
    """True when the FSA boundary intersects the PorterChain GTA ±150 km tile."""
    code = normalize_fsa(fsa)
    return bool(code) and code in gta150_fsa_codes()


def gta150_fsa_record(fsa: str | None) -> dict[str, Any] | None:
    code = normalize_fsa(fsa)
    if not code:
        return None
    for row in load_gta150_registry().get("fsas", []):
        if isinstance(row, dict) and normalize_fsa(str(row.get("code") or "")) == code:
            return dict(row)
    if code in _GTA150_HUB_OVERRIDES:
        return {
            "code": code,
            "active": True,
            "centroid": dict(_HUB_CENTROID),
            "source": "hub_override_non_geographic",
        }
    return None


def gta150_registry_meta() -> dict[str, Any]:
    data = load_gta150_registry()
    return {
        "version": data.get("version"),
        "count": len(gta150_fsa_codes()),
        "ontario_fsa_count": data.get("ontario_fsa_count"),
        "tile": data.get("tile"),
        "source": data.get("source"),
        "hub_overrides": sorted(_GTA150_HUB_OVERRIDES),
    }

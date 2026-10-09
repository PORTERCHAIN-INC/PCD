"""
Checked-in contract rate schedules — machine-readable copies of signed PDFs.

An FSA-model merchant whose `pricing_config.schedule.contract_schedule` names
one of these is priced from the file, not from `pricing_fsa_rates` rows: van
tier per stop, route pickup, compact banding, heavy-item handling, and which
destination FSAs are quotable at all. Anything the schedule does not list —
unlisted urban FSAs, rural FSAs (second character 0), and its custom-quote
list — is a custom quotation for the whole route.

Files live in `porterchain_pricing/data/`; add a row to `SCHEDULE_FILES` when a
new contract is signed rather than editing an old file in place.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from porterchain_pricing.policy import CM_PER_UNIT, KG_PER_UNIT

_DATA_DIR = Path(__file__).resolve().parent / "data"

#: Schedule id → file under `data/`. The id is what `pricing_config` stores.
SCHEDULE_FILES: dict[str, str] = {
    "kaylulu-2026-09": "kaylulu_schedule_2026_09.json",
}

#: Float slack when comparing converted units (Shopify grams → kg, in → cm).
_EPS = 1e-6


@dataclass(frozen=True)
class VanTier:
    code: str
    name: str
    stop_cents: int
    route_minimum_cents: int
    fsas: frozenset[str]


@dataclass(frozen=True)
class CompactBand:
    """Rate for a compact route whose billable stops are ≤ `max_stops` (None = open)."""

    max_stops: int | None
    stop_cents: int
    pickup_cents: int


@dataclass(frozen=True)
class CompactTerms:
    vehicle_classes: tuple[str, ...]
    max_packed_cm: tuple[float, float]
    parcels_per_stop: int
    bands: tuple[CompactBand, ...]
    route_minimum_cents: int
    fsas: frozenset[str]

    def band_for(self, stops: int) -> CompactBand:
        ordered = sorted(self.bands, key=lambda b: (b.max_stops is None, b.max_stops or 0))
        for band in ordered:
            if band.max_stops is None or stops <= band.max_stops:
                return band
        return ordered[-1]

    def billable_stops(self, parcels: int) -> int:
        return max(1, math.ceil(max(parcels, 1) / max(self.parcels_per_stop, 1)))


@dataclass(frozen=True)
class HandlingTier:
    code: str
    max_weight_kg: float
    max_footprint_cm: tuple[float, float]
    surcharge_cents: int


@dataclass(frozen=True)
class ContractSchedule:
    id: str
    pickup_cents: int
    group_max_cm: tuple[float, float]
    group_parcels_per_stop: int
    van_tiers: tuple[VanTier, ...]
    custom_quote_fsas: frozenset[str]
    compact: CompactTerms
    handling: tuple[HandlingTier, ...]

    def van_tier(self, fsa: str) -> VanTier | None:
        """Tier for a destination, or None when it is a custom quotation."""
        code = (fsa or "").strip().upper()[:3]
        if len(code) != 3 or code[1] == "0" or code in self.custom_quote_fsas:
            return None
        return next((t for t in self.van_tiers if code in t.fsas), None)

    def in_compact_territory(self, fsa: str) -> bool:
        return (fsa or "").strip().upper()[:3] in self.compact.fsas

    def coverage_fsas(self) -> frozenset[str]:
        """Every destination FSA this contract prices without a custom quote."""
        out: set[str] = set()
        for tier in self.van_tiers:
            out |= tier.fsas
        return frozenset(out | self.compact.fsas)

    def handling_tier(
        self, weight_kg: float | None, dims_cm: tuple[float | None, ...] | None
    ) -> HandlingTier | None:
        """
        Higher of the weight tier and the footprint tier (they do not stack).

        Unknown weight or size counts as the lowest tier for that trigger.
        None means beyond the last tier — a custom quotation.
        """
        weight_idx = 0
        if weight_kg is not None and weight_kg > 0:
            weight_idx = next(
                (i for i, t in enumerate(self.handling) if weight_kg <= t.max_weight_kg + _EPS),
                len(self.handling),
            )
        fp = footprint_cm(dims_cm)
        size_idx = 0
        if fp is not None:
            size_idx = next(
                (i for i, t in enumerate(self.handling) if fits(fp, t.max_footprint_cm)),
                len(self.handling),
            )
        idx = max(weight_idx, size_idx)
        return self.handling[idx] if idx < len(self.handling) else None


def footprint_cm(dims_cm: tuple[float | None, ...] | None) -> tuple[float, float] | None:
    """Two longest packed sides, longest first. None unless two sides are known."""
    sides = sorted((float(x) for x in (dims_cm or ()) if x is not None and x > 0), reverse=True)
    if len(sides) < 2:
        return None
    return (sides[0], sides[1])


def fits(footprint: tuple[float, float], limit: tuple[float, float]) -> bool:
    longest, second = sorted(limit, reverse=True)
    return footprint[0] <= longest + _EPS and footprint[1] <= second + _EPS


def _inches(pair: Any) -> tuple[float, float]:
    a, b = (float(x) * CM_PER_UNIT["in"] for x in pair)
    return (a, b)


def _codes(raw: Any) -> frozenset[str]:
    return frozenset(str(c).strip().upper() for c in raw or [])


def schedule_from_dict(raw: dict[str, Any]) -> ContractSchedule:
    van = raw["van"]
    compact = raw["compact"]
    handling = raw["handling"]
    kg_per = KG_PER_UNIT[handling.get("weight_unit", "lb")]
    cm_per = CM_PER_UNIT[handling.get("dimension_unit", "in")]
    return ContractSchedule(
        id=str(raw["id"]),
        pickup_cents=int(van["pickup_cents"]),
        group_max_cm=_inches(van["grouping"]["max_packed_inches"]),
        group_parcels_per_stop=int(van["grouping"]["parcels_per_stop"]),
        van_tiers=tuple(
            VanTier(
                code=str(t["code"]),
                name=str(t.get("name") or t["code"]),
                stop_cents=int(t["stop_cents"]),
                route_minimum_cents=int(t["route_minimum_cents"]),
                fsas=_codes(t["fsas"]),
            )
            for t in van["tiers"]
        ),
        custom_quote_fsas=_codes(raw.get("custom_quote_fsas")),
        compact=CompactTerms(
            vehicle_classes=tuple(str(v).lower() for v in compact["vehicle_classes"]),
            max_packed_cm=_inches(compact["max_packed_inches"]),
            parcels_per_stop=int(compact["parcels_per_stop"]),
            bands=tuple(
                CompactBand(
                    max_stops=None if b.get("max_stops") is None else int(b["max_stops"]),
                    stop_cents=int(b["stop_cents"]),
                    pickup_cents=int(b["pickup_cents"]),
                )
                for b in compact["bands"]
            ),
            route_minimum_cents=int(compact["route_minimum_cents"]),
            fsas=_codes(compact["fsas"]),
        ),
        handling=tuple(
            HandlingTier(
                code=str(t["code"]),
                max_weight_kg=float(t["max_weight"]) * kg_per,
                max_footprint_cm=(
                    float(t["max_footprint"][0]) * cm_per,
                    float(t["max_footprint"][1]) * cm_per,
                ),
                surcharge_cents=int(t["surcharge_cents"]),
            )
            for t in handling["tiers"]
        ),
    )


@lru_cache(maxsize=None)
def load_contract_schedule(schedule_id: str | None) -> ContractSchedule | None:
    """Parsed schedule for an id stored in `pricing_config`, or None when unknown."""
    filename = SCHEDULE_FILES.get(str(schedule_id or "").strip())
    if not filename:
        return None
    with open(_DATA_DIR / filename, encoding="utf-8") as handle:
        return schedule_from_dict(json.load(handle))


def raw_contract_schedule(schedule_id: str) -> dict[str, Any]:
    """The file as written — for templates that copy rates into `pricing_config`."""
    with open(_DATA_DIR / SCHEDULE_FILES[schedule_id], encoding="utf-8") as handle:
        return json.load(handle)

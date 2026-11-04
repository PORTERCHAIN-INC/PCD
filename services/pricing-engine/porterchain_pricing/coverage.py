"""Parcel coverage for the engine path (merchant FSA/distance, Shopify, quotes) — pure, no I/O.

Ravi 2026-10-29 replaced the old "free $2,500 + $25,000 upgrade for $10/stop" model (it promised cargo
insurance we do not have yet). Now, via ``declared_value`` (the single source):
default liability $4.41/kg; optional declared-value cover at 1.5% of value, $3 minimum, per parcel,
max $2,500 per parcel, excluding cash/jewellery/medicines/perishables, proof of value to claim,
and OFF until cargo insurance is confirmed (G-INS). ``coverage_upgrade`` now means "buy declared-value cover".
"""

from __future__ import annotations

from typing import Any

from porterchain_pricing import declared_value as DV

SETTINGS_KEY = "parcel_coverage"
_KEYS = tuple(DV.RULES)


def default_coverage() -> dict[str, Any]:
    return store_coverage(None)


def store_coverage(raw: Any) -> dict[str, Any]:
    """Settings normalizer: validated rules as stored. ``enabled`` here is only a request (see G-INS)."""
    src = raw if isinstance(raw, dict) else {}
    out = {k: v for k, v in DV.RULES.items()}
    out["excluded_categories"] = list(DV.RULES["excluded_categories"])
    for key in ("rate_bps", "min_cents", "max_value_cents", "default_liability_cents_per_kg"):
        if src.get(key) is None:
            continue
        try:
            val = int(src[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"coverage_invalid:{key}") from exc
        if val < 0:
            raise ValueError(f"coverage_invalid:{key}")
        out[key] = val
    if isinstance(src.get("enabled"), bool):
        out["enabled"] = src["enabled"]
    if isinstance(src.get("excluded_categories"), list):
        cats = [str(c).strip().lower() for c in src["excluded_categories"] if str(c).strip()]
        out["excluded_categories"] = sorted(set(cats) | set(DV.RULES["excluded_categories"]))  # can't un-exclude
    return out


def normalize_coverage(raw: Any, insurance: Any = None) -> dict[str, Any]:
    """Effective rules for pricing. G-INS: cover is on only if requested AND ``cargo_insurance`` is confirmed.
    Old-model keys (included_cents, upgrade_cents...) are ignored. Already-effective dicts pass through."""
    if isinstance(raw, DV.Effective) and insurance is None:
        return DV.rules(raw)  # already gated earlier in the same quote
    return DV.rules(store_coverage(raw), insurance)


def recommend(declared_value_cents: int | None, category: str | None = None, cfg: dict[str, Any] | None = None,
              parcels: int = 1) -> dict:
    """``included`` (default liability) | ``upgrade`` (cover worth buying) | ``over_max`` | ``excluded``."""
    c = normalize_coverage(cfg)
    declared = max(int(declared_value_cents or 0), 0)
    per = declared // max(int(parcels or 1), 1)
    if DV.excluded_group(category, c):
        return {"tier": "excluded", "reason": "Cash, jewellery, medicines and perishables can't be covered."}
    if per > c["max_value_cents"]:
        return {"tier": "over_max",
                "reason": f"Declared value is above the ${c['max_value_cents'] / 100:,.0f} per-parcel maximum."}
    if not c["enabled"]:
        return {"tier": "included", "reason": "Declared-value cover is not available yet. Standard liability "
                f"is ${c['default_liability_cents_per_kg'] / 100:.2f}/kg."}
    if declared:
        return {"tier": "upgrade", "reason": "Standard liability is per kg; cover pays up to the declared value."}
    return {"tier": "included", "reason": f"Standard liability ${c['default_liability_cents_per_kg'] / 100:.2f}/kg."}


def charge_cents(upgrade: bool, parcels: int = 1, cfg: dict[str, Any] | None = None,
                 declared_value_cents: int | None = None) -> int:
    c = normalize_coverage(cfg)
    if not upgrade or not c["enabled"] or not declared_value_cents:
        return 0
    n = max(int(parcels or 1), 1)
    per = int(declared_value_cents) // n
    return DV.cover_cents(per, c) * n


def coverage_label(upgrade: bool, cfg: dict[str, Any] | None = None) -> str:
    c = normalize_coverage(cfg)
    if upgrade:
        return f"Declared-value cover ({c['rate_bps'] / 100:g}%, min ${c['min_cents'] / 100:.0f})"
    return f"Standard liability ${c['default_liability_cents_per_kg'] / 100:.2f}/kg"

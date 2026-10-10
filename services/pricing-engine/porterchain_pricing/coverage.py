"""Parcel coverage (declared value cover) — pure, no I/O.

Every delivery is covered up to ``included_cents`` ($2,500) at no charge. An opt-in
upgrade covers up to ``upgrade_cents`` ($25,000) for ``upgrade_price_cents`` ($10),
charged per delivery or per parcel (``unit``). Declared values above the upgrade
ceiling are flagged (``over_max``) so booking can block or route to manual review.
``recommend`` picks the tier from declared value + item category.
"""

from __future__ import annotations

from typing import Any

SETTINGS_KEY = "parcel_coverage"
UNITS = ("delivery", "parcel")

DEFAULT_COVERAGE: dict[str, Any] = {
    "schema": 1,
    "included_cents": 250_000,
    "upgrade_cents": 2_500_000,
    "upgrade_price_cents": 1_000,
    "unit": "delivery",
    #: Categories that should carry the upgrade even below the included cap.
    "high_risk_categories": ["electronics", "jewelry", "art", "medical", "luxury"],
    #: Recommend the upgrade once declared value reaches this share of the included cap.
    "recommend_at_pct": 80,
}


def default_coverage() -> dict[str, Any]:
    out = dict(DEFAULT_COVERAGE)
    out["high_risk_categories"] = list(DEFAULT_COVERAGE["high_risk_categories"])
    return out


def normalize_coverage(raw: Any) -> dict[str, Any]:
    out = default_coverage()
    src = raw if isinstance(raw, dict) else {}
    for key in ("included_cents", "upgrade_cents", "upgrade_price_cents", "recommend_at_pct"):
        if src.get(key) is None:
            continue
        try:
            val = int(src[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"coverage_invalid:{key}") from exc
        if val < 0:
            raise ValueError(f"coverage_invalid:{key}")
        out[key] = val
    if src.get("unit") is not None:
        if src["unit"] not in UNITS:
            raise ValueError("coverage_invalid:unit")
        out["unit"] = src["unit"]
    if isinstance(src.get("high_risk_categories"), list):
        out["high_risk_categories"] = [str(c).strip().lower() for c in src["high_risk_categories"] if str(c).strip()]
    if out["upgrade_cents"] < out["included_cents"]:
        raise ValueError("coverage_invalid:upgrade_below_included")
    return out


def recommend(declared_value_cents: int | None, category: str | None = None, cfg: dict[str, Any] | None = None) -> dict:
    """Which tier fits: ``included`` | ``upgrade`` | ``over_max``, with a one-line reason."""
    c = normalize_coverage(cfg)
    declared = max(int(declared_value_cents or 0), 0)
    cat = (category or "").strip().lower()
    if declared > c["upgrade_cents"]:
        return {"tier": "over_max", "reason": f"Declared value is above the ${c['upgrade_cents'] / 100:,.0f} maximum."}
    if declared > c["included_cents"]:
        return {"tier": "upgrade", "reason": f"Declared value is above the free ${c['included_cents'] / 100:,.0f} cover."}
    if cat and cat in c["high_risk_categories"]:
        return {"tier": "upgrade", "reason": f"{cat.title()} items are usually worth upgrading."}
    if declared and declared * 100 >= c["included_cents"] * c["recommend_at_pct"]:
        return {"tier": "upgrade", "reason": "Declared value is close to the free cover limit."}
    return {"tier": "included", "reason": f"Free cover up to ${c['included_cents'] / 100:,.0f} is enough."}


def charge_cents(upgrade: bool, parcels: int = 1, cfg: dict[str, Any] | None = None) -> int:
    c = normalize_coverage(cfg)
    if not upgrade:
        return 0
    units = max(int(parcels or 1), 1) if c["unit"] == "parcel" else 1
    return c["upgrade_price_cents"] * units


def coverage_label(upgrade: bool, cfg: dict[str, Any] | None = None) -> str:
    c = normalize_coverage(cfg)
    cap = c["upgrade_cents"] if upgrade else c["included_cents"]
    return f"Coverage up to ${cap / 100:,.0f}"

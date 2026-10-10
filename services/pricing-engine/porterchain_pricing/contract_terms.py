"""Per-merchant conditions of carriage — pure calculators over a schedule's ``terms``.

Kaylulu is one instance (``data/kaylulu_schedule_2026_09.json`` → ``terms``); any
contract can carry the same block and every number is editable through
``pricing_config.schedule.contract_overrides``.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

#: PorterChain's universal Conditions of Carriage (B2–B5, C03, C07, C13, C15).
#: Stored as the ``carriage_terms`` system setting (editable in admin Settings);
#: a merchant contract may override any part via ``schedule.contract_overrides.terms``.
DEFAULT_TERMS: dict[str, Any] = {
    # Global fleet offers liftgate trucks (surcharge in pricing); a contract may set False.
    "liftgate_available": True,
    "waiting": {
        "pickup_included_minutes": 45,
        "stop_included_minutes": 15,
        "cents_per_hour": 3000,
        "increment_minutes": 15,
        "pooled": False,
    },
    "failed_delivery": {
        "van_pct": 50,
        "compact_pct": 50,
        "compact_min_cents": 1500,
        "route_minimum_on_return": False,
        "pickup_on_return": False,
        "handling_in_pct": False,
    },
    # None = the ``parcel_coverage`` setting (B4 values live there).
    "coverage": None,
    "concierge": {"available": True, "past_designated_point_cents": 3000},
    "claims": {
        "window_business_days": 5,
        "notify_email": "enterprise@porterchain.com",
        "required_records": [
            "order_reference",
            "issue_description",
            "damage_photos",
            "proof_of_value",
            "delivery_information",
            "pod_documentation",
        ],
    },
    "declarations": {
        "dangerous_goods_require_approval": True,
        "prohibited": [
            "firearms_or_weapons",
            "currency_or_securities",
            "cannabis",
            "human_or_animal_remains",
            "live_animals",
            "live_plants_or_cut_flowers",
            "interprovincial_tobacco_or_alcohol",
            "illegal_articles",
        ],
    },
}


def default_carriage_terms() -> dict[str, Any]:
    import copy

    return copy.deepcopy(DEFAULT_TERMS)


def normalize_carriage_terms(raw: Any) -> dict[str, Any]:
    """Admin edits merged over defaults; numbers must be non-negative."""
    from porterchain_pricing.contract_schedule import deep_merge

    if raw is not None and not isinstance(raw, dict):
        raise ValueError("carriage_terms must be an object")
    out = deep_merge(default_carriage_terms(), raw or {})
    for section in ("waiting", "failed_delivery", "concierge"):
        for k, v in out[section].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v < 0:
                raise ValueError(f"carriage_terms.{section}.{k} must be >= 0")
    if out["waiting"]["increment_minutes"] <= 0:
        raise ValueError("carriage_terms.waiting.increment_minutes must be > 0")
    out["liftgate_available"] = bool(out["liftgate_available"])
    return out


def terms_of(
    schedule: Any = None, global_terms: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Global terms (setting) with a contract's own ``terms`` merged on top."""
    from porterchain_pricing.contract_schedule import deep_merge

    raw = getattr(schedule, "terms", None) if schedule is not None else None
    return deep_merge(deep_merge(DEFAULT_TERMS, global_terms or {}), raw or {})


def _billable_blocks(over_minutes: float, increment: int) -> int:
    return (
        math.ceil(max(over_minutes, 0) / max(increment, 1)) if over_minutes > 0 else 0
    )


def waiting_cents(
    terms: dict[str, Any],
    *,
    pickup_minutes: float = 0,
    stop_minutes: list[float] | None = None,
) -> dict[str, Any]:
    """B2: allowance per location (pickup / each stop), not pooled; billed in increments."""
    w = terms["waiting"]
    rate_per_block = w["cents_per_hour"] * w["increment_minutes"] / 60
    lines = []
    over = pickup_minutes - w["pickup_included_minutes"]
    blocks = _billable_blocks(over, w["increment_minutes"])
    if blocks:
        lines.append(
            {
                "where": "pickup",
                "minutes_over": over,
                "cents": round(blocks * rate_per_block),
            }
        )
    for i, mins in enumerate(stop_minutes or [], start=1):
        over = mins - w["stop_included_minutes"]
        blocks = _billable_blocks(over, w["increment_minutes"])
        if blocks:
            lines.append(
                {
                    "where": f"stop {i}",
                    "minutes_over": over,
                    "cents": round(blocks * rate_per_block),
                }
            )
    return {"total_cents": sum(x["cents"] for x in lines), "lines": lines}


def failed_delivery_cents(
    terms: dict[str, Any], *, vehicle: str, stop_rate_cents: int
) -> int:
    """B3 return fee for one failed stop. Handling is never inside the percentage."""
    f = terms["failed_delivery"]
    if vehicle == "compact":
        return max(
            round(stop_rate_cents * f["compact_pct"] / 100), int(f["compact_min_cents"])
        )
    return round(stop_rate_cents * f["van_pct"] / 100)


def concierge_cents(terms: dict[str, Any], delivery_point: str | None) -> int:
    """C03: lobby/concierge is included; past the designated point is a surcharge."""
    c = terms["concierge"]
    if delivery_point == "past_designated_point" and c.get("available"):
        return int(c.get("past_designated_point_cents") or 0)
    return 0


def claim_deadline(terms: dict[str, Any], delivered_on: date) -> date:
    """B5: N business days after delivery or attempted delivery (Mon–Fri)."""
    days = int(terms["claims"]["window_business_days"])
    d = delivered_on
    while days:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days -= 1
    return d


def missing_claim_records(
    terms: dict[str, Any], provided: list[str] | set[str]
) -> list[str]:
    have = set(provided or [])
    return [r for r in terms["claims"]["required_records"] if r not in have]


def declaration_problem(
    terms: dict[str, Any], *, dangerous_goods: bool, prohibited: list[str] | None
) -> str | None:
    """C13/C15: DG needs written approval first; listed prohibited articles are refused."""
    d = terms["declarations"]
    if prohibited:
        bad = [p for p in prohibited if not d["prohibited"] or p in d["prohibited"]]
        if bad:
            return "prohibited_article"
    if dangerous_goods and d.get("dangerous_goods_require_approval"):
        return "dangerous_goods_need_approval"
    return None

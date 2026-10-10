"""Cost per stop vs price: the margin alert.

Price is what the pricing engine quoted (pre-tax ``summary.subtotal_cents`` on the
quote's ``pricing_breakdown``; the order total when there is no quote). Nothing is
re-priced here. Cost is the committed route's driver time, split over its stops.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def order_price_cents(order: Any) -> int:
    quote = getattr(order, "quote", None)
    breakdown = getattr(quote, "pricing_breakdown", None) if quote is not None else None
    summary = breakdown.get("summary") if isinstance(breakdown, dict) else None
    if isinstance(summary, dict) and isinstance(summary.get("subtotal_cents"), (int, float)):
        return int(summary["subtotal_cents"])
    return int(getattr(order, "amount_cents", 0) or 0)


def order_costs(routes: list[dict[str, Any]]) -> dict[str, int]:
    """Route cost split by stop count: an order with 2 of a route's 10 stops carries 20 %."""
    out: Counter[str] = Counter()
    for r in routes:
        stops = r.get("stops") or []
        if not stops:
            continue
        per_stop = int(r.get("cost_cents") or 0) / len(stops)
        for s in stops:
            out[s["order_id"]] += per_stop
    return {k: int(round(v)) for k, v in out.items()}


def margin_pct(price_cents: int, cost_cents: int) -> float | None:
    if price_cents <= 0:
        return None
    return round((price_cents - cost_cents) / price_cents * 100, 1)


def below_floor(price_cents: int, cost_cents: int, floor_pct: float) -> bool:
    m = margin_pct(price_cents, cost_cents)
    return m is not None and m < floor_pct

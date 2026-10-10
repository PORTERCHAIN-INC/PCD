"""Plan insights: what a re-plan changes, and which waiting orders share an area. Pure, no DB."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

MIN_GROUP = 2


def driver_by_order(routes: list[dict[str, Any]]) -> dict[str, str | None]:
    """``order_id → driver_id`` across a plan's routes."""
    return {s["order_id"]: r.get("driver_id") for r in routes for s in r.get("stops") or []}


def diff(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Orders added, moved between drivers, or dropped by a re-plan."""
    a, b = driver_by_order(before), driver_by_order(after)
    return {
        "added": [{"order_id": o, "to": d} for o, d in b.items() if o not in a],
        "moved": [{"order_id": o, "from": a[o], "to": d} for o, d in b.items() if o in a and a[o] != d],
        "removed": [{"order_id": o, "from": d} for o, d in a.items() if o not in b],
    }


def area_of(order: Any) -> str | None:
    """Drop FSA (first 3 postal characters); the merge key for same-area orders."""
    drop = order.dropoff if isinstance(order.dropoff, dict) else {}
    raw = str(drop.get("postal_code") or drop.get("postalCode") or drop.get("fsa") or "").replace(" ", "").upper()
    return raw[:3] if len(raw) >= 3 else None


def consolidation(waiting: list[Any], planned: dict[str, str | None] | None = None) -> list[dict[str, Any]]:
    """Same-area groups worth one route: 2+ orders in one FSA, biggest group first.

    ``planned`` (order → driver) marks orders a plan already split across drivers.
    """
    groups: dict[str, list[Any]] = defaultdict(list)
    for o in waiting:
        if (fsa := area_of(o)) is not None:
            groups[fsa].append(o)
    out = []
    for fsa, orders in groups.items():
        if len(orders) < MIN_GROUP:
            continue
        drivers = {(planned or {}).get(o.id) for o in orders} - {None}
        out.append({
            "fsa": fsa, "order_ids": [o.id for o in orders], "order_numbers": [o.order_number for o in orders],
            "split_across": len(drivers), "why": f"{len(orders)} drops in {fsa}" + (
                f", now split over {len(drivers)} drivers" if len(drivers) > 1 else ""),
        })
    return sorted(out, key=lambda g: (-g["split_across"], -len(g["order_ids"])))

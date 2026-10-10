"""Partner legs: local van, warehouse cross-dock, FTL/LTL linehaul, 3PL final mile.

Rules-first and free. Pure: callers pass plain dicts for the order and partners.
"""

from __future__ import annotations

import math
from typing import Any

TORONTO = (43.6532, -79.3832)
DEFAULTS = {"local_radius_km": 80.0, "ftl_min_kg": 4500.0, "local_max_kg": 2500.0}


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    dlat, dlng = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlng / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _covers(partner: dict[str, Any], fsa: str | None) -> int:
    """Longest matching FSA prefix length (0 = no cover)."""
    if not fsa:
        return 0
    best = 0
    for pre in partner.get("fsa_coverage") or []:
        p = str(pre).upper().strip()
        if p and fsa.startswith(p):
            best = max(best, len(p))
    return best


def _price(partner: dict[str, Any], kg: float) -> int:
    return max(int(partner.get("min_charge_cents") or 0), int(round((partner.get("rate_per_kg_cents") or 0) * kg)))


def plan_legs(order: dict[str, Any], partners: list[dict[str, Any]], cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return ``{mode, legs:[{seq, mode, partner_id, from_label, to_label, est_cost_cents, meta}], notes}``.

    ``order`` = {pickup:(lat,lng), drop:(lat,lng), pickup_fsa, drop_fsa, kg, warehouse_hold: bool}.
    """
    c = {**DEFAULTS, **(cfg or {})}
    pu, do = tuple(order["pickup"]), tuple(order["drop"])
    kg = float(order.get("kg") or 0)
    pf, df = order.get("pickup_fsa") or "pickup", order.get("drop_fsa") or "drop"
    active = [p for p in partners if p.get("active", True)]
    whs = [p for p in active if p.get("kind") == "warehouse" and p.get("lat") is not None]
    legs: list[dict[str, Any]] = []
    notes: list[str] = []

    def leg(mode: str, frm: str, to: str, partner: dict[str, Any] | None = None, **meta: Any) -> None:
        legs.append({
            "seq": len(legs), "mode": mode, "partner_id": partner.get("id") if partner else None,
            "from_label": frm, "to_label": to,
            "est_cost_cents": _price(partner, kg) if partner and mode != "local" else 0, "meta": meta,
        })

    local = km(TORONTO, pu) <= c["local_radius_km"] and km(TORONTO, do) <= c["local_radius_km"]
    if local and kg <= c["local_max_kg"]:
        if order.get("warehouse_hold") and whs:
            wh = min(whs, key=lambda w: km(pu, (w["lat"], w["lng"])))
            leg("local", pf, wh["name"], wh, to_lat=wh["lat"], to_lng=wh["lng"], stop_kind="hub")
            leg("warehouse", wh["name"], wh["name"], wh, hold=True)
            leg("local", wh["name"], df, wh, from_lat=wh["lat"], from_lng=wh["lng"])
            return {"mode": "warehouse", "legs": legs, "notes": ["held at warehouse"]}
        leg("local", pf, df)
        return {"mode": "local", "legs": legs, "notes": notes}

    kind = "ftl" if kg >= c["ftl_min_kg"] else "ltl"
    hauls = [p for p in active if p.get("kind") == kind]
    haul = min(hauls, key=lambda p: _price(p, kg)) if hauls else None
    tpl = max((p for p in active if p.get("kind") == "3pl"), key=lambda p: _covers(p, order.get("drop_fsa")), default=None)
    if tpl is not None and _covers(tpl, order.get("drop_fsa")) == 0:
        tpl = None
    wh = min(whs, key=lambda w: km(pu, (w["lat"], w["lng"]))) if whs and kind == "ltl" else None

    start = pf
    if wh is not None:
        leg("local", pf, wh["name"], wh, to_lat=wh["lat"], to_lng=wh["lng"], stop_kind="hub")
        start = wh["name"]
    end = tpl["name"] if tpl else df
    if haul is None:
        notes.append(f"no active {kind.upper()} partner — add one in Fleet → Partners")
    leg(kind, start, end, haul)
    if tpl is not None:
        leg("3pl", tpl["name"], df, tpl)
    elif not local:
        notes.append("no 3PL covers the drop FSA — linehaul delivers direct")
    return {"mode": kind, "legs": legs, "notes": notes}

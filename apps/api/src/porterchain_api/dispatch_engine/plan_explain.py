"""Explain a fleet plan with plain rules (no external AI): coverage, fill, length, unplanned pairs.

Suggest-only: nothing here assigns, sends or commits.
"""

from __future__ import annotations

from typing import Any


def summarize(plan: dict[str, Any], stops_by_key: dict[str, Any]) -> dict[str, Any]:
    """Compact view of an evaluated plan: route labels (R1…), FSAs, minutes, fill %, cost."""
    routes = []
    for i, r in enumerate(plan.get("routes", []), start=1):
        seq = []
        for s in r.get("stops", []):
            spec = stops_by_key.get(s["key"])
            seq.append({
                "kind": s["kind"],
                "fsa": s.get("fsa"),
                "at": [round(spec.lat, 2), round(spec.lng, 2)] if spec is not None else None,
                "eta_min": round(s.get("eta_s", 0) / 60),
            })
        routes.append({
            "route": f"R{i}", "vehicle": r.get("vehicle_class"), "stops": seq,
            "minutes": round(r.get("seconds", 0) / 60), "fill_pct": r.get("fill_pct"),
            "cost_dollars": round(r.get("cost_cents", 0) / 100, 2),
        })
    out = {
        "routes": routes,
        "unplanned_pairs": len(plan.get("dropped", [])),
        "total_cost_dollars": round(plan.get("cost_cents", 0) / 100, 2),
    }
    return out


def rules_explain(summary: dict[str, Any], *, max_fill: float = 85.0) -> dict[str, Any]:
    lines: list[str] = []
    sugg: list[str] = []
    routes = summary.get("routes", [])
    stops = sum(len(r["stops"]) for r in routes)
    lines.append(f"{len(routes)} vehicle(s) cover {stops} stop(s) for ${summary.get('total_cost_dollars', 0):.2f}.")
    for r in routes:
        fsas = [s["fsa"] for s in r["stops"] if s.get("fsa")]
        area = " → ".join(dict.fromkeys(fsas)) or "un-coded area"
        lines.append(f"{r['route']} ({r['vehicle']}): {len(r['stops'])} stops, {r['minutes']} min, fill {r['fill_pct']}% — {area}.")
        if (r.get("fill_pct") or 0) < 25 and len(routes) > 1:
            sugg.append(f"{r['route']} is under 25% full — consider merging it into another route or a smaller vehicle.")
        if (r.get("fill_pct") or 0) > max_fill:
            sugg.append(f"{r['route']} is above {max_fill:.0f}% — check box counts before loading.")
        if r["minutes"] > 480:
            sugg.append(f"{r['route']} runs over 8 hours — split it or start earlier.")
    if summary.get("unplanned_pairs"):
        sugg.append(f"{summary['unplanned_pairs']} pickup→drop pair(s) did not fit — add a vehicle or move a window.")
    return {"source": "rules", "explanation": lines, "suggestions": sugg, "suggest_only": True}

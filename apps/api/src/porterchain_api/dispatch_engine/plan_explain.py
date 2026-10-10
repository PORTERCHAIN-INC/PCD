"""Explain a fleet plan — rules-first; optional NVIDIA NIM LLM (suggest-only).

The LLM never assigns, sends or commits. It only sees a redacted summary:
route labels (R1…), stop kinds, FSA codes, coordinates rounded to 2 dp (~1 km),
minutes, fill %, cost. No names, phones, emails, street addresses, order numbers
or driver ids. :func:`assert_no_pii` is a hard gate before any network call.
"""

from __future__ import annotations

import json
import re
from typing import Any

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", re.IGNORECASE)
_PHONE = re.compile(r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_POSTAL = re.compile(r"\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b", re.IGNORECASE)
_STREET = re.compile(r"\b\d{1,5}\s+[A-Za-z][A-Za-z .'-]{2,}\b(?:St|Ave|Rd|Dr|Blvd|Cres|Ct|Way|Lane|Ln|Pkwy)\b", re.IGNORECASE)
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_ORDER_NO = re.compile(r"\b(?:ORD|PC)-\d{8}-[0-9A-F]+\b", re.IGNORECASE)


class PiiLeak(ValueError):
    pass


def assert_no_pii(payload: Any) -> None:
    text = json.dumps(payload, default=str)
    for name, rx in (("email", _EMAIL), ("phone", _PHONE), ("postal", _POSTAL), ("street", _STREET),
                     ("id", _UUID), ("order_number", _ORDER_NO)):
        if rx.search(text):
            raise PiiLeak(f"pii_blocked:{name}")


def redact(plan: dict[str, Any], stops_by_key: dict[str, Any]) -> dict[str, Any]:
    """PII-free view of an evaluated plan (output of ``vrp.evaluate`` + solver compare)."""
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
        "solver": plan.get("solver"),
        "compare": {
            k: {"cost_dollars": round(v.get("cost_cents", 0) / 100, 2), "dropped": v.get("dropped"), "feasible": v.get("feasible")}
            for k, v in (plan.get("compare") or {}).items() if isinstance(v, dict)
        },
    }
    assert_no_pii(out)
    return out


def rules_explain(summary: dict[str, Any], *, max_fill: float = 85.0) -> dict[str, Any]:
    lines: list[str] = []
    sugg: list[str] = []
    routes = summary.get("routes", [])
    stops = sum(len(r["stops"]) for r in routes)
    lines.append(f"{len(routes)} vehicle(s) cover {stops} stop(s) for ${summary.get('total_cost_dollars', 0):.2f}.")
    comp = summary.get("compare") or {}
    if len(comp) > 1:
        lines.append("Solvers: " + ", ".join(f"{k} ${v['cost_dollars']:.2f}" for k, v in comp.items())
                     + f" → kept {summary.get('solver')}.")
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


SYSTEM_PROMPT = (
    "You are a dispatch analyst for a Toronto same-day delivery company. You receive an anonymised "
    "route plan (FSA codes, rounded coordinates, minutes, fill %, cost). Explain in plain English why the "
    "plan looks this way and suggest at most 4 concrete improvements. You cannot assign drivers, send "
    "messages or change the plan; a human admin decides. Reply as JSON: "
    '{"explanation": [short sentences], "suggestions": [short sentences]}.'
)


def llm_explain(summary: dict[str, Any], chat: Any) -> dict[str, Any]:
    """``chat`` = ``nim_client.chat_completion``. Raises on PII or transport failure."""
    assert_no_pii(summary)
    res = chat(messages=[{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": json.dumps(summary)}], max_tokens=600)
    try:
        body = json.loads(res.get("content") or "{}")
    except json.JSONDecodeError:
        body = {"explanation": [str(res.get("content") or "")[:800]], "suggestions": []}
    return {
        "source": "nvidia_nim", "model": res.get("model"),
        "explanation": [str(x)[:400] for x in body.get("explanation", [])][:8],
        "suggestions": [str(x)[:400] for x in body.get("suggestions", [])][:4],
        "suggest_only": True,
    }

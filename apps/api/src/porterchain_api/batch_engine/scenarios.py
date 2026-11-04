"""Bulk-delivery scenario rules (pure, deterministic; the service/routers persist the outcome).

Covers: one pickup split across drivers, depot cross-dock, multi-pickup -> one drop consolidation,
partial pickup, reverse pickups on the same route, failed-delivery disposition per merchant rule,
oversize reassignment, containers (cage/tote/pallet), mixed business types, driver unavailable
mid-route, time-window clashes, and pickup verification by risk.
"""
from __future__ import annotations

import random
from typing import Any

from porterchain_api.batch_engine.planner import SAMPLE_MAX, SAMPLE_MIN, SCAN_REQUIRED, VEHICLE_CAPACITY

HIGH_RISK = SCAN_REQUIRED  # pharmacy, high_value, contract, customs
VEHICLE_ORDER = ("car", "suv", "cargo_van", "box_truck")
#: Per-vehicle single-item limits (kg, longest side cm).
ITEM_LIMITS = {"car": (30, 100), "suv": (45, 150), "cargo_van": (70, 300), "box_truck": (250, 600)}
CONTAINER_KINDS = ("cage", "tote", "pallet")
#: Ravi 2026-10-29: no overnight holding and no depot storage. A failed delivery is re-attempted
#: the same day or returned to the sender the same day; nothing is kept overnight.
FAIL_OPTIONS = ("reattempt", "locker", "neighbour", "return_to_sender")
DEFAULT_FAIL_RULE = {"order": ["reattempt", "return_to_sender"], "max_attempts": 2,
                     "neighbour_ok": False, "locker_ok": False}
#: Business types keep their own handling and documents even when sharing a route.
BUSINESS_RULES = {
    "pharmacy": {"handling": ["pharmacy", "signature", "id_check"], "docs": ["pharmacy_custody", "seal_number"]},
    "retail": {"handling": [], "docs": []},
    "grocery": {"handling": ["cold"], "docs": []},
    "b2b": {"handling": ["signature"], "docs": ["bol"]},
    "customs": {"handling": ["customs", "signature"], "docs": ["commercial_invoice", "cbsa_release"]},
    "high_value": {"handling": ["high_value", "signature", "id_check"], "docs": ["signed_handover"]},
}


# --- pickup verification by risk ------------------------------------------------------------
def verification(route_id: str, parcels: list[dict[str, Any]]) -> dict[str, Any]:
    """Low risk: count + photo + 3-5 random spot scans. High risk parcels (pharmacy, high value,
    contract, customs): every one scanned. Mixed routes do both."""
    high = sorted(p["barcode"] for p in parcels if HIGH_RISK & set(p.get("handling") or []) or p.get("scan_required"))
    low = sorted(p["barcode"] for p in parcels if p["barcode"] not in set(high))
    rng = random.Random(route_id)
    k = min(len(low), rng.randint(SAMPLE_MIN, SAMPLE_MAX)) if low else 0
    spot = sorted(rng.sample(low, k)) if k else []
    level = "high" if high and not low else "mixed" if high else "low"
    return {"level": level, "count_required": True, "photo_required": True, "merchant_confirm": True,
            "scan_all": high, "spot_scan": spot, "must_scan": sorted({*high, *spot})}


def verification_blockers(v: dict[str, Any], *, counted: int | None, photo: bool, merchant_confirmed: bool,
                          scanned: set[str]) -> list[str]:
    out = []
    if counted is None:
        out.append("count_required")
    if not photo:
        out.append("photo_required")
    if not merchant_confirmed:
        out.append("merchant_confirm_required")
    out += [f"scan_required:{b}" for b in v["must_scan"] if b not in scanned]
    return out


# --- split one pickup across drivers by their routes ----------------------------------------
def split_pickup(parcels: list[dict[str, Any]], routes: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """routes: {route_id: {"zones": [...], "vehicle_class": ..}}. Each parcel goes to the route serving its
    zone with room left; unmatched -> "unassigned" (ops decides)."""
    out: dict[str, list[str]] = {rid: [] for rid in routes}
    out["unassigned"] = []
    load = {rid: 0 for rid in routes}
    for p in sorted(parcels, key=lambda x: x["barcode"]):
        cands = [rid for rid, r in routes.items() if p.get("zone") in r.get("zones", [])
                 and load[rid] < VEHICLE_CAPACITY[r.get("vehicle_class", "cargo_van")]["parcels"]]
        if not cands:
            out["unassigned"].append(p["barcode"])
            continue
        rid = min(cands, key=lambda c: (load[c], c))
        out[rid].append(p["barcode"])
        load[rid] += 1
    return out


# --- same-day vehicle-to-vehicle transfer (replaces depot cross-dock; no depot storage) -------
def cross_dock(parcels: list[dict[str, Any]], zone_routes: dict[str, str]) -> dict[str, Any]:
    """Inbound sweep collects all, then hands each parcel straight to the outbound vehicle for its
    zone at a meet point the same day. Nothing is stored at a depot. Parcels with no outbound route
    go back to the sender the same day. Custody: pickup -> handover_out -> handover_in."""
    out: dict[str, list[str]] = {}
    back = []
    for p in parcels:
        rid = zone_routes.get(p.get("zone") or "")
        (out.setdefault(rid, []) if rid else back).append(p["barcode"])
    return {"outbound": {k: sorted(v) for k, v in out.items()}, "return_to_sender_same_day": sorted(back),
            "mode": "vehicle_to_vehicle_same_day", "depot_storage": False,
            "custody_steps": ["picked_up", "handover_out", "handover_in"]}


def consolidate(pickups: list[dict[str, Any]], drop: dict[str, Any]) -> dict[str, Any]:
    """Several pickups feed one drop: the drop unlocks only once every pickup is confirmed;
    expected count at the drop is the sum of confirmed counts."""
    pending = [p["id"] for p in pickups if p.get("status") != "confirmed"]
    counted = sum(int(p.get("counted") or 0) for p in pickups if p.get("status") == "confirmed")
    return {"drop_id": drop["id"], "locked": bool(pending), "waiting_on": pending,
            "expected_at_drop": counted, "stops": [p["id"] for p in pickups] + [drop["id"]]}


# --- partial pickup -------------------------------------------------------------------------
def partial_pickup(expected: list[str], ready: list[str], *, next_slot: str | None) -> dict[str, Any]:
    left = sorted(set(expected) - set(ready))
    if not left:
        return {"status": "complete", "picked": sorted(ready), "second_pickup": None}
    if not next_slot:
        return {"status": "partial", "picked": sorted(ready), "second_pickup": None,
                "exception": {"kind": "partial_pickup_unscheduled", "quantity": len(left)}, "ask_admin": True}
    return {"status": "partial", "picked": sorted(ready),
            "second_pickup": {"barcodes": left, "slot": next_slot, "status": "scheduled"}}


# --- reverse / return pickup on the same route ------------------------------------------------
def add_reverse_pickup(stops: list[dict[str, Any]], ret: dict[str, Any], capacity: int) -> list[dict[str, Any]]:
    """Insert a return pickup on the same route: at its building's existing stop if there is one and the van
    has room by then, otherwise after the first stop that frees enough room. Load never exceeds capacity."""
    load = sum(s.get("deliver", 0) for s in stops)
    if load > capacity:
        raise ValueError("over_capacity")
    after: list[int] = []
    for i, s in enumerate(stops):
        load += s.get("collect", 0) - s.get("deliver", 0)
        after.append(load)
    same = [i for i, s in enumerate(stops) if ret.get("building_key") and s.get("building_key") == ret["building_key"]]
    for i in same + list(range(len(stops))):
        if all(x + ret["collect"] <= capacity for x in after[i:]):
            return [*stops[: i + 1], {**ret, "kind": "reverse_pickup"}, *stops[i + 1:]]
    raise ValueError("no_capacity_for_return")


# --- failed delivery disposition --------------------------------------------------------------
def failed_disposition(parcel: dict[str, Any], rule: dict[str, Any] | None) -> dict[str, Any]:
    r = {**DEFAULT_FAIL_RULE, **(rule or {})}
    attempts = int(parcel.get("attempts") or 1)
    high = bool(HIGH_RISK & set(parcel.get("handling") or []))
    if "pharmacy" in (parcel.get("handling") or []):
        # Doc 70 controlled_substance profile: same-day return to the pharmacy, signed back in, never held.
        return {"action": "return_to_sender", "same_day": True, "requires": ["signed_back_in"]}
    for opt in r["order"]:
        if opt == "reattempt" and attempts < r["max_attempts"]:
            return {"action": "reattempt", "attempt": attempts + 1, "same_day": True}
        if opt == "neighbour" and r["neighbour_ok"] and not high:
            return {"action": "neighbour", "requires": ["neighbour_name", "photo"]}
        if opt == "locker" and r["locker_ok"] and not high and parcel.get("locker_fits", True):
            return {"action": "locker", "requires": ["locker_code"]}
        if opt in ("depot", "return_to_sender"):  # legacy "depot" rules now mean same-day return
            return {"action": "return_to_sender", "same_day": True}
    return {"action": "return_to_sender", "same_day": True}


# --- oversize / overweight -------------------------------------------------------------------
def fits_vehicle(item: dict[str, Any], vehicle: str) -> bool:
    kg, cm = ITEM_LIMITS[vehicle]
    return float(item.get("weight_kg") or 0) <= kg and float(item.get("longest_cm") or 0) <= cm


def reassign_oversize(item: dict[str, Any], current: str, drivers: list[dict[str, Any]]) -> dict[str, Any]:
    if fits_vehicle(item, current):
        return {"action": "keep"}
    ok = [d for d in drivers if d.get("available", True) and fits_vehicle(item, d["vehicle_class"])]
    if not ok:
        return {"action": "ask_admin", "reason": "no_vehicle_fits"}
    d = min(ok, key=lambda d: (VEHICLE_ORDER.index(d["vehicle_class"]), d.get("distance_km", 0), d["id"]))
    return {"action": "reassign", "driver_id": d["id"], "vehicle_class": d["vehicle_class"], "dolly":
            float(item.get("weight_kg") or 0) > 32}


# --- containers -------------------------------------------------------------------------------
def container_count(containers: list[dict[str, Any]], counted: dict[str, int] | None = None) -> dict[str, Any]:
    """Count cages/totes/pallets, not parcels; parcels inside are known from the manifest. A sealed
    container with a seal mismatch -> open and scan it."""
    for c in containers:
        if c["kind"] not in CONTAINER_KINDS:
            raise ValueError("unknown_container_kind")
    by_kind: dict[str, int] = {}
    for c in containers:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    exc = []
    for k, n in (counted or {}).items():
        if n != by_kind.get(k, 0):
            exc.append({"kind": "short" if n < by_kind.get(k, 0) else "extra", "container": k,
                        "quantity": abs(n - by_kind.get(k, 0))})
    open_scan = [c["id"] for c in containers if c.get("seal") and c.get("seal_seen") not in (None, c["seal"])]
    return {"expected": by_kind, "parcels": sum(len(c.get("parcels") or []) for c in containers),
            "exceptions": exc, "open_and_scan": open_scan}


# --- mixed business types ------------------------------------------------------------------------
def stop_rules(parcel: dict[str, Any]) -> dict[str, Any]:
    b = BUSINESS_RULES.get(parcel.get("business_type") or "retail", BUSINESS_RULES["retail"])
    handling = sorted({*(parcel.get("handling") or []), *b["handling"]})
    return {"handling": handling, "docs": list(b["docs"]), "scan_required": bool(HIGH_RISK & set(handling))}


# --- driver unavailable mid-route ---------------------------------------------------------------
def reassign_remaining(remaining: list[dict[str, Any]], from_driver: str, drivers: list[dict[str, Any]],
                       at: dict[str, float]) -> dict[str, Any]:
    from porterchain_api.batch_engine.vrp import _hav_m

    ok = [d for d in drivers if d["id"] != from_driver and d.get("available", True)]
    if not remaining:
        return {"action": "none"}
    if not ok:
        return {"action": "ask_admin", "reason": "no_driver_available"}
    need = len(remaining)
    room = [d for d in ok if VEHICLE_CAPACITY[d["vehicle_class"]]["parcels"] - int(d.get("load") or 0) >= need]
    if not room:
        return {"action": "ask_admin", "reason": "no_capacity"}
    d = min(room, key=lambda d: (_hav_m((at["lat"], at["lng"]), (d["lat"], d["lng"])), d["id"]))
    return {"action": "reassign", "to_driver_id": d["id"],
            "handover": {"from": from_driver, "to": d["id"], "barcodes": sorted(p["barcode"] for p in remaining),
                         "point": at, "custody": "scan_each" if any(HIGH_RISK & set(p.get("handling") or [])
                                                                     for p in remaining) else "count"}}


# --- time-window clash -------------------------------------------------------------------------
def resolve_windows(stops: list[dict[str, Any]], *, start_s: float, travel_s: float = 600,
                    service_s: float = 120) -> dict[str, Any]:
    """Try current order; if a window is missed, resequence by window end (EDF). If still infeasible,
    ask admin with the clashing stops."""
    def run(seq):
        t, late = start_s, []
        for s in seq:
            t += travel_s
            t = max(t, s.get("window_start", 0))
            if t > s.get("window_end", 10**12):
                late.append(s["id"])
            t += service_s
        return late
    if not run(stops):
        return {"action": "keep", "sequence": [s["id"] for s in stops]}
    edf = sorted(stops, key=lambda s: (s.get("window_end", 10**12), s.get("window_start", 0), s["id"]))
    late = run(edf)
    if not late:
        return {"action": "resequenced", "sequence": [s["id"] for s in edf]}
    return {"action": "ask_admin", "sequence": [s["id"] for s in edf], "clashes": late}

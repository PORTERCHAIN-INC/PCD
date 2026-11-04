"""Pure batch planning + scan advice (no DB). Shared rules for web + mobile via driver-flows."""
from __future__ import annotations

import csv
import hashlib
import io
import random
import re
from typing import Any

#: Parcels per vehicle (no dims in CSV -> count + kg caps).
VEHICLE_CAPACITY = {
    "car": {"parcels": 40, "kg": 300},
    "suv": {"parcels": 70, "kg": 500},
    "cargo_van": {"parcels": 150, "kg": 1200},
    "box_truck": {"parcels": 400, "kg": 3500},
}
HANDLING = ("fragile", "upright", "cold", "pharmacy", "id_check", "signature", "dolly", "high_value", "contract", "customs")
PICKUP_SOURCES = ("house", "shop", "warehouse", "storage", "driver")
SCAN_REQUIRED = {"pharmacy", "high_value", "contract", "customs"}
SAMPLE_MIN, SAMPLE_MAX = 3, 5


def norm_label(raw: str) -> str:
    """Client labels compare case/space/dash-insensitive; Shopify '#1001' == '1001'."""
    return re.sub(r"[\s\-#]", "", (raw or "")).upper()


def building_key(address: str) -> tuple[str, str | None]:
    """'Unit 5, 100 King St W' / '5-100 King St W' -> ('100 KING ST W', '5')."""
    a = (address or "").strip()
    unit = None
    m = re.match(r"^\s*(?:unit|apt|suite|ste|#)\s*(\w+)\s*[-,]?\s*(.*)$", a, re.I)
    if m:
        unit, a = m.group(1), m.group(2)
    else:
        m = re.match(r"^\s*(\w+)\s*-\s*(\d.*)$", a)
        if m:
            unit, a = m.group(1), m.group(2)
    street = a.split(",")[0]
    m = re.search(r",?\s*(?:unit|apt|suite|ste|#)\s*(\w+)\s*$", street, re.I)
    if m:
        unit = unit or m.group(1)
        street = street[: m.start()]
    return re.sub(r"\s+", " ", street).strip().upper(), unit


def parse_csv(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Columns: address (required), recipient, unit, weight_kg, handling ('fragile;cold'), client_label."""
    rows, errors = [], []
    for i, r in enumerate(csv.DictReader(io.StringIO(text)), start=1):
        if None in r:  # more cells than headers: an address with commas that is not "quoted"
            errors.append({"row": i, "error": "too_many_columns:quote_values_with_commas"})
            continue
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        if not r.get("address"):
            errors.append({"row": i, "error": "address_required"})
            continue
        flags = [f for f in re.split(r"[;|,\s]+", r.get("handling", "").lower()) if f]
        flags = ["dolly" if f in ("two_person", "2_person", "2-person") else f for f in flags]  # no 2-person service
        bad = [f for f in flags if f not in HANDLING]
        if bad:
            errors.append({"row": i, "error": f"unknown_handling:{bad[0]}"})
            continue
        try:
            w = float(r.get("weight_kg") or 0)
        except ValueError:
            errors.append({"row": i, "error": "weight_invalid"})
            continue
        labels = [x for x in re.split(r"[;|]", r.get("client_label", "")) if x.strip()]
        try:
            lat = float(r["lat"]) if r.get("lat") else None
            lng = float(r["lng"]) if r.get("lng") else None
        except ValueError:
            errors.append({"row": i, "error": "coordinates_invalid"})
            continue
        rows.append({"row": i, "address": r["address"], "recipient": r.get("recipient") or None,
                     "unit": r.get("unit") or None, "weight_kg": w, "handling": flags, "client_labels": labels,
                     "lat": lat, "lng": lng})
    return rows, errors


def plan(rows: list[dict[str, Any]], *, vehicle_class: str = "cargo_van", drivers: int = 1) -> list[dict[str, Any]]:
    """Group same-building rows into one stop, then fill routes up to vehicle capacity without splitting a
    building unless it alone exceeds capacity. Routes beyond the driver count go into later waves."""
    if vehicle_class not in VEHICLE_CAPACITY:
        raise ValueError("unknown_vehicle_class")
    if drivers < 1:
        raise ValueError("drivers_required")
    cap = VEHICLE_CAPACITY[vehicle_class]
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key, unit = building_key(r["address"])
        groups.setdefault(key, []).append({**r, "building_key": key, "unit": r.get("unit") or unit})
    routes: list[list[list[dict[str, Any]]]] = [[]]
    load = {"parcels": 0, "kg": 0.0}

    def fits(n: int, kg: float) -> bool:
        return load["parcels"] + n <= cap["parcels"] and load["kg"] + kg <= cap["kg"]

    for key in sorted(groups):  # stable order; real sequencing happens in the router optimiser
        chunk = groups[key]
        while chunk:
            n, kg = len(chunk), sum(p["weight_kg"] for p in chunk)
            if not fits(n, kg) and routes[-1]:
                routes.append([])
                load = {"parcels": 0, "kg": 0.0}
            take = []
            for p in chunk:
                if fits(len(take) + 1, sum(x["weight_kg"] for x in take) + p["weight_kg"]):
                    take.append(p)
                else:
                    break
            if not take:
                raise ValueError("parcel_exceeds_vehicle_capacity")
            routes[-1].append(take)
            load["parcels"] += len(take)
            load["kg"] += sum(p["weight_kg"] for p in take)
            chunk = chunk[len(take):]
    out = []
    for i, stops in enumerate(r for r in routes if r):
        parcels = []
        for seq, stop in enumerate(stops, start=1):
            parcels += [{**p, "stop_seq": seq, "scan_required": bool(SCAN_REQUIRED & set(p["handling"]))} for p in stop]
        out.append({"route_no": i + 1, "wave": i // drivers + 1, "vehicle_class": vehicle_class,
                    "stops": len(stops), "parcels": parcels, "kg": round(sum(p["weight_kg"] for p in parcels), 2)})
    return out


def make_barcode(batch_id: str, row_no: int) -> str:
    h = hashlib.sha1(f"{batch_id}:{row_no}".encode()).hexdigest()[:8].upper()
    return f"PCB{h}{row_no:04d}"


def spot_sample(route_id: str, barcodes: list[str]) -> list[str]:
    """Deterministic per route (server and app agree; re-opening shows the same prompts)."""
    if not barcodes:
        return []
    rng = random.Random(route_id)
    k = min(len(barcodes), rng.randint(SAMPLE_MIN, SAMPLE_MAX))
    return sorted(rng.sample(sorted(barcodes), k))


def load_order(parcels: list[dict[str, Any]]) -> dict[str, int]:
    """Last stop loaded first: position 1 goes deepest in the vehicle."""
    order = sorted(parcels, key=lambda p: (-p["stop_seq"], p["barcode"]))
    return {p["barcode"]: i + 1 for i, p in enumerate(order)}


def count_exceptions(expected: int, counted: int, damaged: int = 0) -> list[dict[str, Any]]:
    out = []
    if counted < expected:
        out.append({"kind": "short", "quantity": expected - counted})
    if counted > expected:
        out.append({"kind": "extra", "quantity": counted - expected})
    if damaged:
        out.append({"kind": "damaged", "quantity": damaged})
    return out


def scan_advice(parcel: dict[str, Any] | None, *, route_id: str, phase: str, driver_id: str,
                scanned_before: bool = False, pending_handover_to: str | None = None,
                load_position: int | None = None, owner_driver_id: str | None = None) -> dict[str, Any]:
    """What to do with the parcel just scanned. `action` codes are rendered by driver-flows scanAdviceText."""
    if parcel is None:
        return {"action": "unknown_label", "exception": True, "next": ["lookup_address", "lookup_recipient", "photo_flag"]}
    base = {"parcel_id": parcel["id"], "barcode": parcel["barcode"], "stop_seq": parcel["stop_seq"],
            "building_key": parcel["building_key"], "unit": parcel.get("unit"),
            "handling": list(parcel.get("handling") or []), "recipient": parcel.get("recipient")}
    if scanned_before:
        return {**base, "action": "duplicate", "exception": True}
    st = parcel["status"]
    if st == "delivered":
        return {**base, "action": "already_delivered", "exception": True}
    if st in ("return_to_depot", "reattempt"):
        return {**base, "action": "return_to_depot", "exception": False}
    if pending_handover_to:
        return {**base, "action": "hand_to_driver", "to_driver_id": pending_handover_to, "exception": False}
    if parcel.get("route_id") != route_id:
        return {**base, "action": "not_this_route", "owner_driver_id": owner_driver_id, "exception": True}
    if phase == "pickup":
        return {**base, "action": "load", "load_position": load_position, "exception": False}
    return {**base, "action": "deliver", "exception": False}

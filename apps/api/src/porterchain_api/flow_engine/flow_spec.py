"""Doc 82 §1: server-generated guided job flow specs.

Pure functions: inputs are the order's documents (70 §2.2 matrix after C-trigger evaluation),
order flags, org capabilities, pickup mode and vehicle. Apps (driver web + mobile) only render.
Rule (A-GF): a capture appears only if a document/pack asks for it, and every required one appears.
"""
from __future__ import annotations

from typing import Any

FLOW_VERSION = 1
HEAVY_TRUCK_KG = 4500

CARDS = (
    "pre_trip_dvir", "navigate", "arrive_geofence", "accept_offer", "scan_packages", "load_photo",
    "hub_scan_in", "zone_photo", "place_parcel", "seal_check", "temp_read", "id_check", "signature",
    "dolly_check", "damage_before", "damage_after", "bol_present", "count_units", "osd_note",
    "failed_reason", "pod_summary", "leave",
    # Bulk batches
    "batch_parcel_list", "spot_check", "count_photo", "merchant_handover", "count_exception",
    "scan_parcel", "building_scan", "handover_out", "handover_in", "leftover_disposition",
    # Pickup documents + instructions
    "pickup_docs", "instructions",
)

# Conditional triggers (doc 70 §2.2): Cn fires when the order flag is set.
_TRIGGERS = {
    "C1": "bol_required", "C2": "pallets", "C3": "pallets", "C4": "customs", "C5": "rx",
    "C6": "cold_chain", "C7": "dangerous_goods", "C8": "packing_slip", "C10": "signature_required",
    "C11": "dolly", "C12": "bulk_api",
}


def _step(id: str, card: str, capture: list[str] | None = None, block_if: list[str] | None = None,
          only_if: str | None = None) -> dict[str, Any]:
    s: dict[str, Any] = {"id": id, "card": card, "capture": capture or [], "block_if": block_if or []}
    if only_if:
        s["only_if"] = only_if
    return s


def active_documents(doc_matrix: dict[str, str], flags: dict[str, Any]) -> set[str]:
    """A = always; Cn only when its trigger flag is set on the order."""
    out = set()
    for doc, rule in doc_matrix.items():
        if rule == "A" or (rule in _TRIGGERS and flags.get(_TRIGGERS[rule])):
            out.add(doc)
    return out


def delivery_type(docs: set[str], flags: dict[str, Any]) -> str:
    if flags.get("failed"):
        return "return_failed"
    if "rx_custody_log" in docs:
        return "pharmacy_custody"
    if "bol" in docs:
        return "b2b_dock_bol"
    if "dolly" in docs or "two_person" in docs:  # Ravi 2026-10-29: dolly replaces two-person
        return "dolly"
    if "cold_chain_log" in docs:
        return "cold_chain"
    if "signature_id" in docs:
        return "signature_id"
    return "parcel"


def pickup_flow(pickup_mode: str, *, vehicle_gvwr_kg: int | None = None, multi_stop: bool = False) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    heavy = (vehicle_gvwr_kg or 0) > HEAVY_TRUCK_KG
    if heavy:
        steps.append(_step("dvir", "pre_trip_dvir", ["dvir"], ["dvir_missing", "hos_block"]))
    if pickup_mode == "on_demand":
        steps += [_step("offer", "accept_offer", [], ["offer_expired"]),
                  _step("nav", "navigate"),
                  _step("arrive", "arrive_geofence", [], ["not_at_pickup"]),
                  _step("scan", "scan_packages", ["scan"], []),
                  _step("leave", "leave")]
    elif pickup_mode == "hub_dropoff":
        steps += [_step("arrive", "arrive_geofence", [], ["not_at_stop"]),
                  _step("scan_in", "hub_scan_in", ["scan"], ["unknown_package"]),
                  _step("zone", "zone_photo", ["photo"], ["wrong_zone"])]
    else:  # scheduled_daily, recurring_route, dock_appointment, multi_location
        steps += [_step("nav", "navigate"),
                  _step("arrive", "arrive_geofence", [], ["not_at_stop"]),
                  _step("scan", "scan_packages", ["scan"], ["count_mismatch"]),
                  _step("load", "load_photo", ["photo"]),
                  _step("leave", "leave")]
    return {"flow_id": f"pickup_{pickup_mode}", "version": FLOW_VERSION, "locale_keys": True,
            "multi_stop": multi_stop, "warn_if": ["out_of_sequence"] if multi_stop else [],
            "steps": steps}


def delivery_flow(docs: set[str], flags: dict[str, Any]) -> dict[str, Any]:
    kind = delivery_type(docs, flags)
    arrive = _step("arrive", "arrive_geofence", [], ["not_at_stop"])
    scan = _step("scan", "scan_packages", ["scan"], ["scan_mismatch"])
    steps: list[dict[str, Any]]
    if kind == "return_failed":
        block = ["no_reason"] + (["same_day_return_required"] if flags.get("rx") else [])
        steps = [_step("reason", "failed_reason", ["reason"], block),
                 _step("door", "place_parcel", ["photo"]),
                 _step("return_scan", "scan_packages", ["scan"])]
    elif kind == "pharmacy_custody":
        steps = [arrive, _step("seal", "seal_check", ["scan", "seal_no", "photo"], ["seal_mismatch"])]
        if "cold_chain_log" in docs:
            steps.append(_step("temp", "temp_read", ["temp"], ["temp_out_of_range"], only_if="cold_chain"))
        steps += [_step("id", "id_check", ["id_name_match"], ["id_fail", "agent_not_named"]),
                  _step("sign", "signature", ["signature"], ["no_signature"]),
                  _step("done", "pod_summary", ["photo"])]
    elif kind == "b2b_dock_bol":
        steps = [arrive, _step("bol", "bol_present", [], ["bol_missing"]),
                 _step("count", "count_units", ["scan"], ["count_short_without_osd"])]
        if flags.get("sealed"):
            steps.append(_step("seal", "seal_check", ["seal_no"], ["seal_mismatch"]))
        steps += [_step("sign", "signature", ["bol_signature"], ["no_signature"]),
                  _step("osd", "osd_note", [])]
    elif kind == "dolly":
        steps = [_step("equip", "dolly_check", ["dolly_confirmed"], ["dolly_missing", "over_dolly_safe_limit"]), arrive,
                 _step("before", "damage_before", ["photo"], ["no_before_photos"]),
                 _step("place", "place_parcel"),
                 _step("after", "damage_after", ["photo"]),
                 _step("sign", "signature", ["signature"], ["no_signature"])]
    elif kind == "cold_chain":
        steps = [arrive, scan, _step("temp", "temp_read", ["temp"], ["temp_out_of_range"], only_if="cold_chain"),
                 _step("place", "place_parcel", ["photo"])]
    elif kind == "signature_id":
        block = ["id_fail"] + (["under_19"] if flags.get("age_restricted") else [])
        steps = [arrive, scan, _step("id", "id_check", ["id_name_match"], block),
                 _step("sign", "signature", ["signature"], ["no_signature"])]
    else:
        steps = [arrive, scan, _step("place", "place_parcel", ["photo"])]
    if "cold_chain_log" in docs and kind not in ("cold_chain", "pharmacy_custody", "return_failed"):
        steps.insert(1, _step("temp", "temp_read", ["temp"], ["temp_out_of_range"], only_if="cold_chain"))
    return {"flow_id": f"delivery_{kind}", "version": FLOW_VERSION, "locale_keys": True,
            "temp_range_c": flags.get("temp_range_c") or ([2, 8] if "cold_chain_log" in docs else None),
            "steps": steps}


def all_captures(spec: dict[str, Any]) -> set[str]:
    return {c for s in spec["steps"] for c in s["capture"]}


def batch_pickup_flow(*, scan_required: bool) -> dict[str, Any]:
    """Bulk pickup: full list + random spot sample; count + one photo + merchant handover confirm.
    Per-parcel scan only when the share has pharmacy / high-value / contract parcels."""
    steps = [_step("arrive", "arrive_geofence", [], ["not_at_pickup"]),
             _step("list", "batch_parcel_list"),
             _step("spot", "spot_check", ["scan"], ["spot_check_incomplete"])]
    if scan_required:
        steps.append(_step("scan_each", "scan_packages", ["scan"], ["per_parcel_scan_required"]))
    steps += [_step("count", "count_photo", ["count", "photo"], ["count_not_entered", "photo_missing"]),
              _step("exception", "count_exception", ["exception"], ["count_mismatch_unreported"]),
              _step("handover", "merchant_handover", ["merchant_confirm"], ["merchant_not_confirmed"]),
              _step("leave", "leave")]
    return {"flow_id": "pickup_batch", "version": FLOW_VERSION, "locale_keys": True, "steps": steps}


def batch_delivery_flow(*, grouped: bool, handling: list[str] | None = None) -> dict[str, Any]:
    """Stop list unlocks after pickup confirm. Each parcel is scanned; a building stop scans all its parcels."""
    h = set(handling or [])
    steps = [_step("unlock", "navigate", [], ["pickup_not_confirmed"]),
             _step("arrive", "arrive_geofence", [], ["not_at_stop"])]
    if grouped:
        steps.append(_step("building", "building_scan", ["scan"], ["building_scan_incomplete"]))
    else:
        steps.append(_step("scan", "scan_parcel", ["scan"], ["scan_mismatch"]))
    if h & {"id_check", "pharmacy"}:
        steps.append(_step("id", "id_check", ["id_name_match"], ["id_fail"]))
    if h & {"signature", "pharmacy", "id_check"}:
        steps.append(_step("sign", "signature", ["signature"], ["no_signature"]))
    steps.append(_step("place", "place_parcel", ["photo"]))
    return {"flow_id": "delivery_batch" + ("_building" if grouped else ""), "version": FLOW_VERSION,
            "locale_keys": True, "steps": steps}


def batch_handover_flow(side: str) -> dict[str, Any]:
    """Driver-to-driver at a meeting point or depot; both sides log time, location and photo."""
    if side == "give":
        steps = [_step("select", "handover_out", ["scan", "photo", "location"], ["handover_needs_photo_and_location"])]
    else:
        steps = [_step("receive", "handover_in", ["scan", "photo", "location"],
                       ["handover_needs_photo_and_location", "handover_scan_mismatch"])]
    return {"flow_id": f"handover_{side}", "version": FLOW_VERSION, "locale_keys": True, "steps": steps}


def batch_close_flow() -> dict[str, Any]:
    return {"flow_id": "batch_close", "version": FLOW_VERSION, "locale_keys": True,
            "steps": [_step("leftover", "leftover_disposition", ["disposition"], ["leftover_without_disposition"])]}


def with_pickup_docs(spec: dict[str, Any], required: list[str]) -> dict[str, Any]:
    """Insert the document checklist (photo/scan + shipper name + signature each) before leaving pickup."""
    if not required:
        return spec
    steps = list(spec["steps"])
    at = next((i for i, s in enumerate(steps) if s["card"] in ("leave", "merchant_handover")), len(steps))
    steps.insert(at, _step("docs", "pickup_docs", ["document", "shipper_name", "shipper_signature"],
                           ["pickup_docs_missing"]))
    return {**spec, "steps": steps, "pickup_docs": list(required)}


def with_instructions(spec: dict[str, Any], must_ack: bool) -> dict[str, Any]:
    """Must-read instructions appear as the first card of the step and block until acknowledged."""
    if not must_ack:
        return spec
    return {**spec, "steps": [_step("instr", "instructions", ["ack"], ["instruction_not_acknowledged"]), *spec["steps"]]}

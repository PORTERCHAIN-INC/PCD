"""Doc 80 §1–§2 pure rules: CVOR threshold, DVIR, HOS (O. Reg. 555/06), payload/weight block."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable

CVOR_KG = 4500
DRIVER_KG = 90
DVIR_VALID = timedelta(hours=24)
DVIR_RETAIN = timedelta(days=183)
HOS_WARN = {"driving": 12.0, "on_duty": 13.0, "elapsed": 15.0}
HOS_BLOCK = {"driving": 13.0, "on_duty": 14.0, "elapsed": 16.0}
HOS_RESET_OFF_H = 8.0
DAILY_OFF_MIN_H = 10.0
RADIUS_KM = 160
STATUSES = ("on_duty", "driving", "off_duty")

# Schedule 1 (O. Reg. 199/07) items for trucks; major = cannot drive.
SCHEDULE_1 = (
    "air_brake_system", "cab", "cargo_securement", "coupling_devices", "dangerous_goods", "driver_controls",
    "driver_seat", "electric_brake_system", "emergency_equipment", "exhaust_system", "frame_and_cargo_body",
    "fuel_system", "general", "glass_and_mirrors", "heater_defroster", "horn", "hydraulic_brake_system",
    "lamps_and_reflectors", "steering", "suspension_system", "tires", "wheels_hubs_fasteners", "windshield_wiper_washer",
)
WALKAROUND = ("front", "rear", "left", "right", "interior")


def cvor_required(rgw_kg: int | None) -> bool:
    return (rgw_kg or 0) > CVOR_KG


def payload_kg(gvwr_kg: int | None, curb_kg: int | None) -> int | None:
    if gvwr_kg is None or curb_kg is None:
        return None
    return max(0, gvwr_kg - curb_kg)


def check_weight(declared_kg: int, *, rgw_kg: int, gvwr_kg: int | None, curb_kg: int | None) -> None:
    """Σ declared kg + driver 90 kg ≤ payload; gross ≤ RGW. Raises ValueError('vehicle_overweight')."""
    load = int(declared_kg) + DRIVER_KG
    pay = payload_kg(gvwr_kg, curb_kg)
    if pay is not None and load > pay:
        raise ValueError("vehicle_overweight")
    if curb_kg is not None and curb_kg + load > rgw_kg:
        raise ValueError("vehicle_overweight")


def eld_required(*, is_rental: bool, rental_days: int | None, radius_ok: bool) -> bool:
    if radius_ok:
        return False
    return not (is_rental and (rental_days or 0) <= 30)


def validate_dvir(d: dict[str, Any], *, heavy: bool) -> dict[str, Any]:
    """Returns {'major_defect': bool, 'defects': [...]} or raises ValueError(code)."""
    for f in ("plate", "operator_name", "location", "inspector_name"):
        if not str(d.get(f) or "").strip():
            raise ValueError(f"dvir_missing_{f}")
    if d.get("odometer_km") is None:
        raise ValueError("dvir_missing_odometer_km")
    if not d.get("signed_statement"):
        raise ValueError("dvir_not_signed")
    items: dict[str, str] = d.get("items") or {}
    needed = SCHEDULE_1 if heavy else WALKAROUND
    missing = [i for i in needed if i not in items]
    if missing:
        raise ValueError(f"dvir_incomplete:{','.join(missing[:3])}")
    bad = {v for v in items.values()} - {"ok", "minor", "major"}
    if bad:
        raise ValueError("dvir_bad_item_value")
    defects = [{"item": k, "severity": v} for k, v in items.items() if v != "ok"]
    return {"defects": defects, "major_defect": any(x["severity"] == "major" for x in defects)}


def dvir_valid(inspected_at: datetime | None, major_defect: bool, now: datetime) -> bool:
    return inspected_at is not None and not major_defect and now - inspected_at <= DVIR_VALID


def hos_summary(events: Iterable[Any], now: datetime) -> dict[str, Any]:
    """Events: objects/dicts with status + at, sorted or not. Window starts after the last ≥ 8 h off."""
    ev = sorted(({"status": _g(e, "status"), "at": _g(e, "at")} for e in events), key=lambda x: x["at"])
    # Find window start: end of the last off-duty stretch ≥ 8 h.
    start_idx = 0
    for i, e in enumerate(ev):
        nxt = ev[i + 1]["at"] if i + 1 < len(ev) else now
        if e["status"] == "off_duty" and (nxt - e["at"]).total_seconds() / 3600 >= HOS_RESET_OFF_H:
            start_idx = i + 1
    window = ev[start_idx:]
    driving = on_duty = 0.0
    for i, e in enumerate(window):
        nxt = window[i + 1]["at"] if i + 1 < len(window) else now
        h = max(0.0, (nxt - e["at"]).total_seconds() / 3600)
        if e["status"] == "driving":
            driving += h
            on_duty += h
        elif e["status"] == "on_duty":
            on_duty += h
    first_work = next((e["at"] for e in window if e["status"] != "off_duty"), None)
    elapsed = (now - first_work).total_seconds() / 3600 if first_work else 0.0
    vals = {"driving": driving, "on_duty": on_duty, "elapsed": elapsed}
    warnings = [k for k, v in vals.items() if v >= HOS_WARN[k]]
    blocks = [k for k, v in vals.items() if v >= HOS_BLOCK[k]]
    return {**{f"{k}_h": round(v, 2) for k, v in vals.items()}, "warnings": warnings, "blocked": blocks,
            "can_take_offers": not blocks}


def _g(e: Any, k: str) -> Any:
    return e[k] if isinstance(e, dict) else getattr(e, k)

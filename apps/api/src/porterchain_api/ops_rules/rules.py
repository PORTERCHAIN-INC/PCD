"""Pure rules for the doc 84 §7 P0 gaps. Open questions in doc 84 §8 are NOT decided here:
- Q6 label printers: unlabelled parcels get a hand-written short code + photo only.
- Q8 claim SLA numbers: no reporting window enforced unless configured.
- Q10 overnight holds: only the doc 70 pharmacy rule (never overnight) is enforced; others unchanged.
- Q4 two-person carry: not offered; items over the one-person limit are refused."""
from __future__ import annotations

import hashlib
import math
import re
import secrets
from datetime import datetime
from typing import Any

# --- SC-094 distracted driving: lock interactive UI above 10 km/h
UI_LOCK_KMH = 10.0


def ui_locked(speed_kmh: float | None) -> bool:
    return speed_kmh is not None and speed_kmh > UI_LOCK_KMH


# --- SC-015 duplicate order: soft-warn on upload, require confirm
def dup_key(address: str, reference: str | None) -> str:
    norm = re.sub(r"[^a-z0-9]", "", (address or "").lower())
    return hashlib.sha256(f"{norm}|{(reference or '').strip().lower()}".encode()).hexdigest()[:24]


def duplicate_warnings(rows: list[dict[str, Any]], existing: set[str] | None = None) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    out = []
    for r in rows:
        if not (r.get("reference") or "").strip():
            continue  # many parcels to one building without a reference are normal
        k = dup_key(r.get("address", ""), r.get("reference"))
        if k in seen:
            out.append({"code": "duplicate_in_file", "row_no": r.get("row_no"), "same_as_row": seen[k]})
        elif existing and k in existing:
            out.append({"code": "duplicate_of_existing", "row_no": r.get("row_no")})
        seen.setdefault(k, r.get("row_no"))
    return out


# --- SC-017 mid-route address / time change
REROUTE_RADIUS_KM = 5.0
LOCKED_STATES = {"OUT_FOR_DELIVERY", "DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED",
                 "FAILED", "RETURN_TO_SENDER"}


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def change_decision(state: str, old: tuple[float, float] | None, new: tuple[float, float] | None,
                    *, time_change: bool = False) -> dict[str, Any]:
    """Allowed until out-for-delivery. Within the radius: re-route live. Further: merchant/admin choose
    fee or next day (no fee amount set here — pricing adjustments carry it)."""
    if state.upper() in LOCKED_STATES:
        return {"allowed": False, "reason": "out_for_delivery"}
    if new is None or old is None:
        return {"allowed": True, "action": "resequence" if time_change else "none", "banner": time_change}
    d = _km(old, new)
    if d <= REROUTE_RADIUS_KM:
        return {"allowed": True, "action": "reroute_live", "distance_km": round(d, 2), "banner": True}
    return {"allowed": True, "action": "fee_or_next_day", "distance_km": round(d, 2), "ask": ["merchant", "admin"],
            "banner": True}


# --- SC-025 unlabelled parcel (doc 84 Q6: no printer in P0)
_ALPH = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L


def short_code(n: int = 6) -> str:
    return "PC-" + "".join(secrets.choice(_ALPH) for _ in range(n))


def unlabelled_requirements() -> list[str]:
    return ["write_short_code_on_parcel", "photo_of_written_code", "photo_of_parcel"]


# --- SC-043 equipment matching
EQUIPMENT = ("dolly", "straps", "blanket", "insulated_bag", "lockbox", "pallet_jack", "tote")
HANDLING_EQUIPMENT = {"cold": ["insulated_bag"], "pharmacy": ["lockbox"], "pallet": ["pallet_jack"],
                      "heavy": ["dolly"], "dolly": ["dolly"], "fragile": ["blanket"]}


def required_equipment(handling: list[str], extra: list[str] | None = None) -> list[str]:
    req = {e for h in handling for e in HANDLING_EQUIPMENT.get(h, [])} | set(extra or [])
    bad = req - set(EQUIPMENT)
    if bad:
        raise ValueError(f"unknown_equipment:{sorted(bad)[0]}")
    return sorted(req)


def equipment_gap(required: list[str], driver_tags: list[str]) -> list[str]:
    return sorted(set(required) - set(driver_tags))


def eligible_drivers(required: list[str], drivers: list[dict[str, Any]]) -> list[str]:
    return [d["id"] for d in drivers if not equipment_gap(required, d.get("equipment") or [])]


# --- Q4: no two-person carry in P0
ONE_PERSON_KG = 32.0  # above this a dolly is required (assumed; doc 84 SC-032)
DOLLY_MAX_KG = 70.0   # one driver with a modular dolly, safe limit (assumed, for Ravi to confirm)


def carry_check(weight_kg: float) -> dict[str, Any]:
    """Ravi 2026-10-29: no two-person or white-glove service. One driver handles heavy parcels
    alone with a modular transport dolly, within safe limits."""
    if weight_kg > DOLLY_MAX_KG:
        return {"ok": False, "code": "oversize_for_vehicle", "reason": "over_dolly_safe_limit"}
    if weight_kg > ONE_PERSON_KG:
        return {"ok": True, "dolly": True, "equipment": ["dolly"]}
    return {"ok": True, "dolly": False}


# --- SC-051: no overnight holding (Ravi 2026-10-29). Nothing stays in a vehicle or depot overnight.
def end_of_shift(parcels_aboard: list[dict[str, Any]]) -> dict[str, Any]:
    rx = [p["barcode"] for p in parcels_aboard if "pharmacy" in (p.get("handling") or [])]
    others = [p["barcode"] for p in parcels_aboard if p["barcode"] not in set(rx)]
    out: dict[str, Any] = {"can_end_shift": not parcels_aboard, "others": others}
    if parcels_aboard:
        out.update(code="overnight_hold_blocked", must_return_to_sender_same_day=others,
                   must_return_to_pharmacy=rx, requires=["signed_back_in"])
    return out


# --- SC-034 / SC-068 / SC-107 safety stops
SAFETY = {
    "suspicious_parcel": {"stop": True, "do_not_deliver": True, "isolate": True, "requires": ["photo"],
                          "notify": ["admin", "merchant"], "then": "return"},
    "unsafe_location": {"stop": True, "abort_allowed": True, "requires": [], "flag_location": True,
                        "notify": ["admin"], "then": "reattempt_or_return"},
    "theft_from_vehicle": {"stop": True, "requires": ["parcels"], "police_report": True,
                           "notify": ["admin", "merchant"], "then": "claim"},
}


def safety_requirements(code: str) -> dict[str, Any]:
    if code not in SAFETY:
        raise ValueError("unknown_safety_code")
    return SAFETY[code]


# --- SC-085 concealed damage (doc 84 Q8: window numbers are Ravi's call)
#: Claim and dispute deadlines as proposed in doc 84 and approved by Ravi on 2026-10-29.
CLAIM_DEADLINES = {
    "loss_ack_days": 3,                 # SC-083 acknowledge a loss claim
    "damage_decision_business_days": 10,  # SC-084
    "concealed_damage_report_days": 5,  # SC-085 customer reports within 5 days with photos
    "billing_dispute_sla_business_days": 5,  # SC-078
    "reweigh_dispute_days": 14,         # SC-077
}


def concealed_damage_check(delivered_at: datetime, reported_at: datetime, photos: list[str],
                           window_days: int | None = CLAIM_DEADLINES["concealed_damage_report_days"]) -> dict[str, Any]:
    days = (reported_at - delivered_at).total_seconds() / 86400
    if days < 0:
        raise ValueError("reported_before_delivery")
    if not photos:
        raise ValueError("photos_required")
    late = window_days is not None and days > window_days
    return {"days_after_delivery": round(days, 2), "late": late, "status": "review" if late else "open"}


# --- Alcohol is refused at booking (Ravi 2026-10-29) -----------------------------------------
ALCOHOL_WORDS = ("alcohol", "beer", "wine", "liquor", "spirits", "vodka", "whisky", "whiskey", "rum",
                 "gin", "tequila", "cider", "sake", "champagne", "lcbo")


def alcohol_problem(*, contains_alcohol: bool = False, text: str | None = None) -> str | None:
    t = (text or "").lower()
    if contains_alcohol or any(re.search(rf"\b{w}\b", t) for w in ALCOHOL_WORDS):
        return "alcohol_not_carried"
    return None


# --- TDG limited-quantity dangerous goods (Ravi 2026-10-29: perfume and aerosols only) ---------
# Sources (checked 2026-10-29):
#  - TDG Regulations s. 1.17 (current to 2026-09-30): outer package <= 30 kg gross; inner quantity
#    <= Schedule 1 col. 6(a); square-on-point mark, sides >= 100 mm (>= 50 mm if the package is small).
#    https://laws-lois.justice.gc.ca/eng/regulations/SOR-2001-286/section-1.17.html
#  - Schedule 1 (Transport Canada open data): UN1266 PERFUMERY PRODUCTS, class 3, PG II and III: 5 L.
#    UN1950 AEROSOLS flammable (2.1) / non-flammable (2.2): 1 L; with class 6.1 substances or
#    compressed oxygen: 0.125 L; some class 8 PG II variants are forbidden on passenger vehicles.
#    https://opendatatc.tc.canada.ca/TDGR_SCHEDULE1_ENG.csv
# We accept only plain consumer aerosols (no 6.1 / class 8 / oxygen) and perfumery products.
LQ_CLASSES = {
    "perfume": {"un": "UN1266", "class": "3", "inner_max_l": 5.0},
    "aerosol": {"un": "UN1950", "class": "2.1/2.2", "inner_max_l": 1.0},
}
LQ_AEROSOL_EXCLUDED = ("6.1", "8", "oxygen")
LQ_PACKAGE_MAX_KG = 30.0
LQ_MARK_MIN_MM = 100
LQ_MARK_SMALL_MIN_MM = 50
#: s. 1.17 note: over 500 kg of LQ from one consignor to one destination, Part 8 reporting applies.
LQ_REPORTING_KG = 500.0


def lq_check(items: list[dict[str, Any]], *, package_gross_kg: float, lq_mark_photo: str | None,
             mark_side_mm: float | None = None, small_package: bool = False) -> dict[str, Any]:
    """Accept only perfume/plain-aerosol limited quantities (TDG s. 1.17)."""
    problems = []
    for it in items:
        spec = LQ_CLASSES.get(str(it.get("kind")))
        if not spec:
            problems.append(f"dg_not_accepted:{it.get('kind')}")
            continue
        if it.get("kind") == "aerosol" and set(map(str, it.get("contains") or [])) & set(LQ_AEROSOL_EXCLUDED):
            problems.append("aerosol_with_toxic_corrosive_or_oxygen")
        elif float(it.get("inner_l") or 0) > spec["inner_max_l"]:
            problems.append(f"inner_over_limit:{it.get('kind')}")
    if package_gross_kg > LQ_PACKAGE_MAX_KG:
        problems.append("package_over_30kg")
    if not lq_mark_photo:
        problems.append("lq_mark_missing")
    if mark_side_mm is not None and mark_side_mm < (LQ_MARK_SMALL_MIN_MM if small_package else LQ_MARK_MIN_MM):
        problems.append("lq_mark_too_small")
    return {"ok": not problems, "problems": problems,
            "un_numbers": sorted({LQ_CLASSES[i["kind"]]["un"] for i in items if i.get("kind") in LQ_CLASSES})}

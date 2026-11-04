"""F11: the single exception-code list. Every exception (order, batch, safety, claim) uses one of these.
Internal codes only; kept mappable for a later EDI 214/854 export (doc 84 Q7 — export not built)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Code:
    code: str
    label: str
    severity: str  # critical | high | medium | low
    group: str  # pickup | transit | delivery | safety | document | claim | system
    blocks: bool = False  # stops the job until ops resolves


CODES: tuple[Code, ...] = (
    # pickup
    Code("count_short", "Fewer parcels than manifest", "high", "pickup"),
    Code("count_extra", "More parcels than manifest", "medium", "pickup"),
    Code("parcel_damaged", "Parcel damaged", "critical", "pickup"),
    Code("unknown_label", "Label not on manifest", "medium", "pickup"),
    Code("duplicate_scan", "Same label scanned twice", "low", "pickup"),
    Code("unlabelled_parcel", "Parcel has no label", "medium", "pickup"),
    Code("partial_pickup", "Not all parcels ready", "medium", "pickup"),
    Code("pickup_document_missing", "Required pickup document missing", "high", "document", True),
    Code("equipment_missing", "Driver lacks required equipment", "high", "pickup", True),
    Code("oversize_for_vehicle", "Item too heavy or big for vehicle", "high", "pickup", True),
    # transit
    Code("driver_unavailable", "Driver unavailable mid-route", "high", "transit"),
    Code("vehicle_breakdown", "Vehicle breakdown", "critical", "transit"),
    Code("time_window_clash", "Time windows cannot all be met", "medium", "transit"),
    Code("address_changed", "Address or time changed mid-route", "medium", "transit"),
    Code("overnight_hold_blocked", "Parcel may not stay in vehicle overnight", "critical", "transit", True),
    Code("parcel_lost", "Parcel lost", "critical", "transit"),
    Code("package_missing", "Package missing", "high", "transit"),
    Code("package_short_at_drop", "Package short at drop", "high", "delivery"),
    # delivery
    Code("failed_delivery", "Delivery failed", "high", "delivery"),
    Code("customer_unavailable", "Recipient unavailable", "high", "delivery"),
    Code("wrong_address", "Wrong address", "high", "delivery"),
    Code("refused", "Recipient refused", "medium", "delivery"),
    # safety (safety stop: driver stops, ops called)
    Code("suspicious_parcel", "Leaking or suspicious parcel", "critical", "safety", True),
    Code("unsafe_location", "Unsafe location (dog, threat)", "critical", "safety", True),
    Code("theft_from_vehicle", "Theft from vehicle", "critical", "safety", True),
    # claims
    Code("concealed_damage", "Damage found after delivery", "medium", "claim"),
    # system
    Code("driver_timeout", "Driver did not respond", "high", "system"),
    Code("driver_reject", "Driver rejected the job", "high", "system"),
)
BY_CODE = {c.code: c for c in CODES}
#: Legacy spellings still written by older flows -> canonical code.
ALIASES = {
    "short": "count_short", "extra": "count_extra", "damaged": "parcel_damaged", "PARCEL_DAMAGED": "parcel_damaged",
    "PARCEL_LOST": "parcel_lost", "VEHICLE_BREAKDOWN": "vehicle_breakdown", "DRIVER_TIMEOUT": "driver_timeout",
    "DRIVER_REJECT": "driver_reject", "FAILED_DELIVERY": "failed_delivery",
    "CUSTOMER_UNAVAILABLE": "customer_unavailable", "WRONG_ADDRESS": "wrong_address",
    "document_missing": "pickup_document_missing", "partial_pickup_unscheduled": "partial_pickup",
}


def canonical(code: str) -> str:
    c = ALIASES.get(code, code)
    if c not in BY_CODE:
        raise ValueError(f"unknown_exception_code:{code}")
    return c


def severity(code: str) -> str:
    return BY_CODE[canonical(code)].severity


def severity_map() -> dict[str, str]:
    out = {c.code: c.severity for c in CODES}
    out.update({a: BY_CODE[c].severity for a, c in ALIASES.items()})
    return out

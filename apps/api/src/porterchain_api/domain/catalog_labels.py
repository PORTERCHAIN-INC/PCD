"""English words merchants see. Capacity class IDs are snake (SoT1); aliases accepted."""

from __future__ import annotations

ORDER_STATE_LABELS: dict[str, str] = {
    "BOOKED": "Booked",
    "DISPATCH_READY": "Ready for pickup",
    "DRIVER_ASSIGNED": "Driver assigned",
    "DRIVER_ACCEPTED": "Driver accepted",
    "DRIVER_EN_ROUTE": "Driver on the way",
    "AT_PICKUP": "At pickup",
    "PICKED_UP": "Picked up",
    "IN_TRANSIT": "In transit",
    "AT_DESTINATION": "At destination",
    "DELIVERED": "Delivered",
    "POD_COMPLETED": "Proof of delivery",
    "INVOICED": "Invoiced",
    "CLOSED": "Closed",
    "CANCELLED": "Cancelled",
    "FAILED": "Failed",
    "RETURN_TO_SENDER": "Returning to sender",
    "DAMAGED": "Damaged",
    "LOST": "Lost",
    "CLAIM_OPEN": "Claim open",
    "REFUNDED": "Refunded",
}

VEHICLE_LABELS: dict[str, str] = {
    "sedan": "Sedan / SUV",
    "suv": "Sedan / SUV",
    "sedan_suv": "Sedan / SUV",
    "sedanSuv": "Sedan / SUV",
    "pickup": "Pickup",
    "cargoVan": "Cargo van",
    "cargo_van": "Cargo van",
    "highRoof": "Sprinter / high-roof",
    "sprinter_van": "Sprinter / high-roof",
    "box_truck": "16 ft box",
    "boxTruck": "16 ft box",
    "box16": "16 ft box",
    "box_16": "16 ft box",
    "box20": "20 ft box",
    "box_20": "20 ft box",
}

PACKAGE_LABELS: dict[str, str] = {
    "looseParcel": "Loose parcel",
    "documents": "Documents",
    "medical": "Medical",
    "furniture": "Furniture",
    "foodBeverage": "Food and beverage",
    "ltlPallet": "Pallet",
    "ftlLoad": "Full load",
}

INVOICE_STATUS_LABELS: dict[str, str] = {
    "none": "Not invoiced",
    "generated": "Invoiced",
    "draft": "Draft",
    "pending": "Pending",
    "sent": "Sent",
    "paid": "Paid",
    "overdue": "Overdue",
    "void": "Void",
    "partial": "Partially paid",
}

CLAIM_STATUS_LABELS: dict[str, str] = {
    "open": "Open",
    "pending": "Pending",
    "under_review": "Under review",
    "approved": "Approved",
    "denied": "Denied",
    "closed": "Closed",
    "resolved": "Resolved",
}

CLAIM_TYPE_LABELS: dict[str, str] = {
    "merchant_complaint": "Complaint",
    "damaged_parcel": "Damaged parcel",
    "lost_parcel": "Lost parcel",
    "late_delivery": "Late delivery",
}

PAYMENT_STATUS_LABELS: dict[str, str] = {
    "pending": "Pending",
    "succeeded": "Paid",
    "paid": "Paid",
    "failed": "Failed",
    "refunded": "Refunded",
}

SLA_STATUS_LABELS: dict[str, str] = {
    "ok": "On time",
    "at_risk": "At risk",
    "breached": "Late",
}

TICKET_STATUS_LABELS: dict[str, str] = {
    "open": "Open",
    "pending": "Pending",
    "waiting": "Waiting",
    "closed": "Closed",
    "resolved": "Resolved",
}

# Company / seat / onboarding — same words on portal, wait screen, and admin.
MERCHANT_STATUS_LABELS: dict[str, str] = {
    "PENDING": "Pending",
    "ONBOARDING": "Onboarding",
    "ACTIVE": "Active",
    "SUSPENDED": "Suspended",
    "CLOSED": "Closed",
}

ONBOARDING_PHASE_LABELS: dict[str, str] = {
    "ready": "Portal ready",
    "needs_invite": "Needs invite",
    "awaiting_clerk": "Awaiting sign-in",
    "needs_activation": "User inactive",
    "needs_approval": "Needs approval",
    "onboarding": "Onboarding",
}

SEAT_STATUS_LABELS: dict[str, str] = {
    "pending": "Pending",
    "active": "Active",
    "off": "Off",
}

ONBOARDING_STEP_STATUS_LABELS: dict[str, str] = {
    "complete": "Complete",
    "pending": "Pending",
    "onboarding": "Onboarding",
    "suspended": "Suspended",
    "closed": "Closed",
    "inactive": "Off",
    "pending_review": "Pending review",
    "waiting": "Waiting",
}

INVITE_STATUS_LABELS: dict[str, str] = {
    "accepted": "Accepted",
    "invite_pending": "Invite pending",
    "not_invited": "Not invited",
    "invite_failed": "Invite failed",
    "revoked": "Revoked",
}


def _pretty(key: str) -> str:
    text = (key or "").replace("_", " ").strip()
    if not text:
        return "—"
    if text.isupper() and " " in text:
        return text.title()
    if text[:1].islower():
        return text[0].upper() + text[1:]
    return text


def _lookup(mapping: dict[str, str], key: str | None) -> str:
    if key is None:
        return "—"
    raw = str(key).strip()
    if not raw:
        return "—"
    return mapping.get(raw) or mapping.get(raw.lower()) or _pretty(raw)


def order_state_label(state: str | None) -> str:
    return _lookup(ORDER_STATE_LABELS, state)


def vehicle_label(code: str | None) -> str:
    mapped = _lookup(VEHICLE_LABELS, code)
    if mapped != "—" and code:
        raw = str(code).strip()
        if raw in VEHICLE_LABELS or raw.lower() in VEHICLE_LABELS:
            return mapped
        from porterchain_api.domain.customer_goods import canonical_vehicle_id

        canon = canonical_vehicle_id(raw)
        return VEHICLE_LABELS.get(canon) or mapped
    return mapped


def package_label(code: str | None) -> str:
    return _lookup(PACKAGE_LABELS, code)


def invoice_status_label(status: str | None) -> str:
    return _lookup(INVOICE_STATUS_LABELS, status)


def claim_status_label(status: str | None) -> str:
    return _lookup(CLAIM_STATUS_LABELS, status)


def claim_type_label(claim_type: str | None) -> str:
    return _lookup(CLAIM_TYPE_LABELS, claim_type)


def payment_status_label(status: str | None) -> str:
    return _lookup(PAYMENT_STATUS_LABELS, status)


def sla_status_label(status: str | None) -> str:
    return _lookup(SLA_STATUS_LABELS, status)


def ticket_status_label(status: str | None) -> str:
    return _lookup(TICKET_STATUS_LABELS, status)


def merchant_status_label(status: str | None) -> str:
    key = (status or "").strip()
    if not key:
        return "Unknown"
    return (
        MERCHANT_STATUS_LABELS.get(key)
        or MERCHANT_STATUS_LABELS.get(key.upper())
        or _pretty(key)
    )


def onboarding_phase_label(phase: str | None) -> str:
    return _lookup(ONBOARDING_PHASE_LABELS, phase)


def seat_status_label(status: str | None) -> str:
    return _lookup(SEAT_STATUS_LABELS, status)


def onboarding_step_status_label(status: str | None, *, complete: bool = False) -> str:
    if complete or (status or "").strip().lower() == "complete":
        return "Complete"
    return _lookup(ONBOARDING_STEP_STATUS_LABELS, status)


def invite_status_label(status: str | None) -> str:
    return _lookup(INVITE_STATUS_LABELS, status)


ORDER_SOURCE_LABELS: dict[str, str] = {
    "WEBSITE": "Customer",
    "MERCHANT": "Merchant",
    "API": "API",
    "CSV": "CSV",
    "ADMIN": "Admin",
    "PHONE": "Phone",
    "PARTNER": "Partner",
    "SHOPIFY": "Shopify",
}


def order_source_label(source: str | None) -> str:
    return _lookup(ORDER_SOURCE_LABELS, source)


# Quote line items — same English words on book, route, bulk, Order 360, admin.
QUOTE_LINE_LABELS: dict[str, str] = {
    "base": "Distance",
    "extra_km": "Extra distance",
    "fsa_rate": "FSA rate",
    "flat_rate": "Flat rate",
    "lane": "Lane",
    "zone": "Zone",
    "stop_fees": "Extra stops",
    "contract_vehicle": "Vehicle",
    "size_tier": "Size",
    "overweight": "Weight",
    "oversize": "Oversize",
    "declared_value": "Declared value coverage",
    "downtown": "Downtown surcharge",
    "upper_zone": "Upper zone surcharge",
    "liftgate": "Liftgate",
    "fuel": "Fuel",
    "promo": "Promo",
    "credit": "Credit",
    "merchant_discount": "Merchant discount",
    "campaign": "Campaign discount",
    "volume_discount": "Volume discount",
    "custom_rule": "Custom rule",
}

QUOTE_LINE_ORDER: tuple[str, ...] = (
    "fsa_rate",
    "base",
    "extra_km",
    "flat_rate",
    "lane",
    "zone",
    "contract_vehicle",
    "stop_fees",
    "size_tier",
    "overweight",
    "oversize",
    "declared_value",
    "downtown",
    "upper_zone",
    "fuel",
    "liftgate",
    "promo",
    "credit",
    "merchant_discount",
    "campaign",
    "volume_discount",
    "custom_rule",
)


def quote_line_label(code: str | None, label: str | None = None) -> str:
    text = str(label or "").strip()
    key = str(code or "").strip()
    if text and text.lower() != key.lower():
        return text
    mapped = QUOTE_LINE_LABELS.get(key) or QUOTE_LINE_LABELS.get(key.lower())
    if mapped:
        return mapped
    return _pretty(key) if key else "Charge"

"""Shared claims domain helpers — identifiers and type vocabulary."""

from __future__ import annotations

CLAIM_TYPES = frozenset({
    "lost_parcel",
    "damaged_parcel",
    "missing_items",
    "wrong_delivery",
    "late_delivery",
    "pickup_failed",
    "delivery_failed",
    "customer_complaint",
    "merchant_complaint",
    "driver_complaint",
    "vehicle_damage",
    "insurance_claim",
    "payment_dispute",
    "chargeback",
    "fraud_investigation",
    "internal_investigation",
    "compliance_issue",
    "other",
    "damage",
    "loss",
    "general",
})


def claim_number(claim_id: str) -> str:
    return f"PCC-{claim_id[:8].upper()}"

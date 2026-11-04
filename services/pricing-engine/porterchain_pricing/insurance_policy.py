"""PorterChain's insurance on file (CSIO certificate dated 2026-11-04, Ravi 2026-11-04) — pure, no I/O.

The single source for limits used by claims, declared-value cover and copy. Amounts are CAD cents.
Every coverage line on the certificate carries a $2,500 deductible. The certificate shows NO automobile
liability, NO non-owned or hired automobile cover and NO excess/umbrella; drivers' own vehicles must
carry their own commercial-use auto insurance.

Limits may have been reduced by paid claims (certificate wording), and cover is subject to the policy's
terms, exclusions and conditions. The certificate itself confers no rights on third parties.
"""
from __future__ import annotations

from datetime import date
from typing import Any

INSURER = "Lloyd's Underwriters"
POLICY_REF = "B5000191409"  # internal/admin only; publish the insurer and limits, give the COI on request
BROKER = "Able Insurance Brokers Ltd."
EFFECTIVE = date(2026, 11, 5)
EXPIRES = date(2027, 11, 5)
DEDUCTIBLE_CENTS = 250_000
CANCELLATION_NOTICE_DAYS = 30
#: Ontario Uniform Conditions of Carriage (O. Reg. 643/05 Sch. 1): written notice of loss or damage within
#: 60 days of delivery (9 months from shipment if never delivered). Our 5-business-day ask is a request.
STATUTORY_NOTICE_DAYS = 60
NON_DELIVERY_NOTICE_MONTHS = 9

CGL: dict[str, int] = {
    "each_occurrence_cents": 200_000_000,
    "general_aggregate_cents": 200_000_000,
    "personal_and_advertising_injury_cents": 100_000_000,
    "tenants_legal_liability_cents": 25_000_000,
    "medical_payments_cents": 1_500_000,
}
CARGO: dict[str, int] = {
    "motor_truck_cargo_cents": 5_000_000,  # most the policy pays for one shipment/load
    "target_commodities_cents": 2_500_000,  # sub-limit when the load contains target commodities
    "towing_storage_debris_removal_cents": 1_000_000,
}

#: High-theft goods that most Canadian motor truck cargo policies sub-limit as "target commodities".
#: The certificate gives only the $25,000 sub-limit, not the list: confirm it against the policy wording.
#: Cannabis is not here because it is prohibited outright (``contract_terms`` declarations).
TARGET_COMMODITIES = ["alcohol", "tobacco", "electronics", "pharmaceuticals", "cosmetics"]
TARGET_ALIASES = {
    "alcohol": "alcohol", "liquor": "alcohol", "wine": "alcohol", "beer": "alcohol", "spirits": "alcohol",
    "tobacco": "tobacco", "cigarettes": "tobacco", "vape": "tobacco", "vaping": "tobacco",
    "electronics": "electronics", "computers": "electronics", "phones": "electronics",
    "cell_phones": "electronics", "laptops": "electronics",
    "pharmaceuticals": "pharmaceuticals", "pharmaceutical": "pharmaceuticals",
    "cosmetics": "cosmetics", "fragrance": "cosmetics", "fragrances": "cosmetics", "perfume": "cosmetics",
}


def in_force(on: date | None = None) -> bool:
    d = on or date.today()
    return EFFECTIVE <= d < EXPIRES


def target_group(category: str | None) -> str | None:
    c = (category or "").strip().lower().replace(" ", "_").replace("-", "_")
    return TARGET_ALIASES.get(c)


def shipment_limit_cents(categories: list[str | None] | None = None) -> int:
    """Most PorterChain pays for one shipment: the cargo limit, or the target-commodity sub-limit."""
    if any(target_group(c) for c in (categories or [])):
        return CARGO["target_commodities_cents"]
    return CARGO["motor_truck_cargo_cents"]


def insurer_recoverable_cents(settled_cents: int) -> int:
    """Part of a settled cargo claim the insurer may reimburse (after the $2,500 deductible)."""
    return max(int(settled_cents or 0) - DEDUCTIBLE_CENTS, 0)


def summary() -> dict[str, Any]:
    return {
        "insurer": INSURER, "policy_ref": POLICY_REF, "broker": BROKER,
        "effective": EFFECTIVE.isoformat(), "expires": EXPIRES.isoformat(), "in_force": in_force(),
        "deductible_cents": DEDUCTIBLE_CENTS, "cgl": dict(CGL), "cargo": dict(CARGO),
        "target_commodities": list(TARGET_COMMODITIES),
        "auto_liability": False, "non_owned_auto": False, "umbrella": False,
    }

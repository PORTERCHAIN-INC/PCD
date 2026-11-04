"""Claims under PorterChain's insurance and the Ontario Uniform Conditions of Carriage (Ravi 2026-11-04).

Pure functions. Inputs are plain values so the admin screen, tests and templates share one answer.
* Liability: $4.41/kg (O. Reg. 643/05 Sch. 1) or the declared value when cover was bought (max $2,500/parcel).
* Per shipment never more than the cargo limit: $50,000, or $25,000 with target commodities.
* The $2,500 insurance deductible is PorterChain's cost and is never charged to a merchant or customer.
* Notice: written notice within 60 days of delivery; 9 months from shipment if never delivered.
* Evidence: written notice, photos, proof of value, proof of delivery.
* Nothing here admits liability: amounts are ceilings, decided only after investigation.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from porterchain_pricing import declared_value as DV
from porterchain_pricing import insurance_policy as POLICY

#: Claim types about goods (cargo). Only these get caps, deadlines and the cargo payout guard.
LOSS_TYPES = frozenset({"lost_parcel", "damaged_parcel", "missing_items", "wrong_delivery", "insurance_claim",
                        "damage", "loss"})
NON_DELIVERY_TYPES = frozenset({"lost_parcel", "loss"})
REQUIRED_EVIDENCE = ("written_notice", "damage_photos", "proof_of_value", "proof_of_delivery")
EVIDENCE_LABELS = {
    "written_notice": "Written notice of the claim",
    "damage_photos": "Photos of the goods and packaging",
    "proof_of_value": "Invoice or other proof of value",
    "proof_of_delivery": "Proof of delivery (or record of non-delivery)",
}
EVIDENCE_ALIASES = {
    "written_notice": "written_notice", "notice": "written_notice", "claim_form": "written_notice",
    "email": "written_notice", "letter": "written_notice",
    "photo": "damage_photos", "photos": "damage_photos", "damage_photo": "damage_photos",
    "damage_photos": "damage_photos", "image": "damage_photos",
    "invoice": "proof_of_value", "receipt": "proof_of_value", "proof_of_value": "proof_of_value",
    "value_proof": "proof_of_value",
    "pod": "proof_of_delivery", "proof_of_delivery": "proof_of_delivery", "pod_documentation": "proof_of_delivery",
    "non_delivery_record": "proof_of_delivery",
}
DENIAL_REASONS = {
    "notice_out_of_time": "Written notice was not received within the time the Ontario Uniform Conditions of "
    "Carriage (O. Reg. 643/05, Sch. 1) allow: 60 days after delivery, or 9 months after shipment for goods "
    "never delivered.",
    "evidence_missing": "We did not receive the information needed to assess the claim (written notice, photos, "
    "proof of value and proof of delivery) after our requests.",
    "excluded_goods": "The goods are of a kind our Terms of Service exclude from declared-value cover (cash, "
    "jewellery, medicines or perishables); standard liability of $4.41 per kg applies instead.",
    "prohibited_goods": "The shipment contained goods our Terms of Service do not allow us to carry.",
    "packing_or_inherent_vice": "Our investigation found the loss or damage was caused by the packing or the "
    "inherent nature of the goods, for which a carrier is not liable under the Uniform Conditions of Carriage.",
    "no_loss_found": "Our investigation, including proof of delivery, did not establish loss or damage while "
    "the goods were in our care.",
    "act_of_god_or_shipper": "Our investigation found the loss was caused by an act of God, the act or default "
    "of the shipper or owner, or another cause for which a carrier is not liable under the Uniform Conditions.",
}


def _d(v: Any) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return date(y, m, min(d.day, last[m - 1]))


def notice_window(*, claim_type: str, shipped_on: Any, delivered_on: Any, notice_on: Any) -> dict[str, Any]:
    shipped, delivered, notice = _d(shipped_on), _d(delivered_on), _d(notice_on)
    non_delivery = claim_type in NON_DELIVERY_TYPES or delivered is None
    if non_delivery:
        base = shipped
        deadline = add_months(base, POLICY.NON_DELIVERY_NOTICE_MONTHS) if base else None
        rule = "9 months from shipment (goods not delivered)"
    else:
        base = delivered
        deadline = date.fromordinal(base.toordinal() + POLICY.STATUTORY_NOTICE_DAYS) if base else None
        rule = "60 days after delivery"
    within = None if (deadline is None or notice is None) else notice <= deadline
    return {"rule": rule, "deadline": deadline.isoformat() if deadline else None,
            "notice_received_on": notice.isoformat() if notice else None, "within_time": within,
            "source": "O. Reg. 643/05, Sch. 1 (Uniform Conditions of Carriage)"}


def evidence_status(files: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    have: set[str] = set()
    for f in files or []:
        for key in (f.get("type"), (f.get("meta") or {}).get("kind")):
            k = EVIDENCE_ALIASES.get(str(key or "").strip().lower())
            if k:
                have.add(k)
    for k, v in (extra or {}).items():
        if v and k in REQUIRED_EVIDENCE:
            have.add(k)
    missing = [k for k in REQUIRED_EVIDENCE if k not in have]
    return {"items": [{"key": k, "label": EVIDENCE_LABELS[k], "received": k in have} for k in REQUIRED_EVIDENCE],
            "missing": missing, "complete": not missing}


def liability_ceiling(parcels: list[dict[str, Any]]) -> dict[str, Any]:
    """Each parcel: weight_kg, covered, declared_value_cents, proof_of_value, category."""
    caps, cats, lines = [], [], []
    for p in parcels or []:
        c = DV.claim_cap_cents(float(p.get("weight_kg") or 0), covered=bool(p.get("covered")),
                               declared_value_cents=p.get("declared_value_cents"),
                               proof_of_value=bool(p.get("proof_of_value")), category=p.get("category"))
        caps.append(c["cap_cents"])
        cats.append(p.get("category"))
        lines.append({**c, "weight_kg": p.get("weight_kg"), "category": p.get("category")})
    ship = DV.shipment_claim_cap_cents(caps, cats)
    return {"parcels": lines, "parcel_total_cents": sum(caps), **ship}


def insurer_step(claimed_cents: int | None, ceiling_cents: int) -> dict[str, Any]:
    """Whether to tell the broker: the claim (bounded by our ceiling) may exceed the deductible."""
    exposure = min(max(int(claimed_cents or 0), 0), int(ceiling_cents or 0)) if claimed_cents else 0
    may_exceed = max(int(claimed_cents or 0), 0) > POLICY.DEDUCTIBLE_CENTS
    return {"deductible_cents": POLICY.DEDUCTIBLE_CENTS, "exposure_cents": exposure,
            "notify_broker": may_exceed, "deductible_borne_by": "PorterChain",
            "recoverable_after_deductible_cents": POLICY.insurer_recoverable_cents(exposure)}


def check_compensation(amount_cents: int, ceiling_cents: int, *, goodwill_reason: str | None = None,
                       merchant_liability_cents: int | None = None, merchant_fault_reason: str | None = None,
                       investigated: bool) -> None:
    """Raise ValueError when a payout would break the policy or the terms."""
    if not investigated:
        raise ValueError("investigation_required_before_decision")
    if amount_cents > POLICY.CARGO["motor_truck_cargo_cents"]:
        raise ValueError("compensation_exceeds_cargo_insurance_limit")
    if amount_cents > ceiling_cents and not (goodwill_reason or "").strip():
        raise ValueError("compensation_exceeds_liability_cap_needs_goodwill_reason")
    if merchant_liability_cents and not (merchant_fault_reason or "").strip():
        raise ValueError("merchant_charge_needs_fault_reason_deductible_never_charged")

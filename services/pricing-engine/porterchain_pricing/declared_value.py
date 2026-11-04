"""Declared-value cover (Ravi 2026-10-29; doc 72 §8, doc 84) — pure, no I/O. The single source for every channel.

* Optional add-on: 1.5% of the declared value, $3 minimum, per parcel.
* Declared value at most $2,500 per parcel. Above that: no cover, contact us.
* Excluded goods (never covered): cash, jewellery, medicines, perishables.
* Proof of value (invoice/receipt) is needed to claim.
* HST applies to the cover fee (Ravi 2026-10-29): it is taxed with the delivery subtotal.
* Without cover our liability is the Ontario default: $4.41 per kg (O. Reg. 643/05 Sch. 1, s. 9).
* OFF until cargo insurance is confirmed (doc 84 open item G-INS): while off, nobody can buy it.
  Policy on file from 2026-11-05: Lloyd's motor truck cargo, $50,000 per shipment, $25,000 when the load has
  target commodities, $2,500 deductible (``insurance_policy``). A super admin still flips ``cargo_insurance``.
* Per shipment, all parcel caps together never exceed the cargo limit (``shipment_claim_cap_cents``).
"""
from __future__ import annotations

from typing import Any

from porterchain_pricing import insurance_policy as POLICY

RULES: dict[str, Any] = {
    "enabled": False,  # G-INS: flip only after the cargo insurer confirms
    "rate_bps": 150,
    "min_cents": 300,
    "max_value_cents": 250_000,
    "per": "parcel",
    "excluded_categories": ["cash", "jewellery", "medicines", "perishables"],
    "proof_of_value_required": True,
    "default_liability_cents_per_kg": 441,
    "flag": "G-INS",
}
#: Settings key for the G-INS gate. Only a super admin can set it (apps/api pricing_version.SUPER_ADMIN_SETTING_KEYS).
INSURANCE_KEY = "cargo_insurance"


def default_cargo_insurance() -> dict[str, Any]:
    return {"confirmed": False, "insurer": None, "policy_ref": None, "confirmed_at": None}


def normalize_cargo_insurance(raw: Any) -> dict[str, Any]:
    """``confirmed`` needs the insurer and the policy reference; otherwise it is rejected."""
    src = raw if isinstance(raw, dict) else {}
    out = default_cargo_insurance()
    for k in ("insurer", "policy_ref", "confirmed_at"):
        v = src.get(k)
        out[k] = str(v).strip()[:200] if v not in (None, "") else None
    if src.get("confirmed") is True:
        if not out["insurer"] or not out["policy_ref"]:
            raise ValueError("cargo_insurance_needs_insurer_and_policy_ref")
        out["confirmed"] = True
    return out


def insurance_confirmed(raw: Any) -> bool:
    try:
        return normalize_cargo_insurance(raw)["confirmed"]
    except ValueError:
        return False


#: Spellings we treat as the excluded groups (booking forms and Shopify product types vary).
EXCLUDED_ALIASES = {
    "cash": "cash", "money": "cash", "currency": "cash", "gift_card": "cash", "gift_cards": "cash",
    "jewellery": "jewellery", "jewelry": "jewellery", "watches": "jewellery",
    "medicine": "medicines", "medicines": "medicines", "medical": "medicines", "pharmacy": "medicines",
    "rx": "medicines", "prescription": "medicines",
    "perishable": "perishables", "perishables": "perishables", "food": "perishables", "grocery": "perishables",
    "groceries": "perishables", "flowers": "perishables", "cold": "perishables",
}


class Effective(dict):
    """Rules already gated by G-INS. Only ``rules()`` makes these; JSON from settings/contracts never is one,
    so a stored ``insurance_confirmed: true`` can't bypass the gate."""


def rules(raw: dict[str, Any] | None = None, insurance: Any = None) -> dict[str, Any]:
    """Effective rules. G-INS: ``enabled`` is only true when the setting/contract asks for it AND
    ``cargo_insurance`` is confirmed. No setting or contract override can switch it on by itself.
    Pass ``insurance=True`` only from code that has already checked the confirmed setting."""
    if isinstance(raw, Effective) and insurance is None:
        return Effective(raw, excluded_categories=list(raw["excluded_categories"]))
    out = {**RULES, "excluded_categories": list(RULES["excluded_categories"])}
    for k, v in (raw or {}).items():
        if k in out and v is not None and k != "flag":
            out[k] = v
    ok = insurance is True or insurance_confirmed(insurance)
    out["insurance_confirmed"] = ok
    out["enabled"] = bool(out["enabled"]) and ok
    return Effective(out)


def excluded_group(category: str | None, r: dict[str, Any] | None = None) -> str | None:
    c = (category or "").strip().lower().replace(" ", "_").replace("-", "_")
    g = EXCLUDED_ALIASES.get(c, c)
    return g if g in rules(r)["excluded_categories"] else None


def cover_cents(value_cents: int, r: dict[str, Any] | None = None) -> int:
    """Charge for one parcel. Half-up rounding to the cent."""
    x = rules(r)
    v = max(int(value_cents or 0), 0)
    return max(int(x["min_cents"]), (v * int(x["rate_bps"]) + 5_000) // 10_000)


def default_liability_cents(weight_kg: float, r: dict[str, Any] | None = None) -> int:
    return int(round(max(float(weight_kg or 0), 0) * int(rules(r)["default_liability_cents_per_kg"])))


def problems(value_cents: int | None, category: str | None = None, r: dict[str, Any] | None = None) -> list[str]:
    """Why cover can't be bought for this parcel ([] = it can)."""
    x = rules(r)
    out = []
    if not x["enabled"]:
        out.append("declared_value_cover_unavailable")
    if not value_cents or int(value_cents) <= 0:
        out.append("declared_value_required")
    elif int(value_cents) > int(x["max_value_cents"]):
        out.append("declared_value_over_max")
    if excluded_group(category, x):
        out.append("declared_value_excluded_goods")
    return out


def quote_parcels(values_cents: list[int], categories: list[str | None] | None = None,
                  r: dict[str, Any] | None = None) -> dict[str, Any]:
    """Cover for several parcels. Raises ValueError(first problem) if any parcel can't be covered."""
    cats = list(categories or []) + [None] * (len(values_cents) - len(categories or []))
    lines = []
    for i, (v, c) in enumerate(zip(values_cents, cats)):
        bad = problems(v, c, r)
        if bad:
            raise ValueError(bad[0])
        lines.append({"parcel": i + 1, "declared_value_cents": int(v), "cents": cover_cents(v, r)})
    return {"lines": lines, "cents": sum(line["cents"] for line in lines),
            "proof_of_value_required": bool(rules(r)["proof_of_value_required"])}


def claim_cap_cents(weight_kg: float, *, covered: bool, declared_value_cents: int | None = None,
                    proof_of_value: bool = False, category: str | None = None,
                    r: dict[str, Any] | None = None) -> dict[str, Any]:
    """Most we pay on a loss/damage claim for one parcel."""
    base = default_liability_cents(weight_kg, r)
    if not covered:
        return {"cap_cents": base, "basis": "default_liability_per_kg"}
    if excluded_group(category, r):
        return {"cap_cents": base, "basis": "excluded_goods"}
    if not proof_of_value:
        return {"cap_cents": base, "basis": "proof_of_value_missing"}
    v = min(max(int(declared_value_cents or 0), 0), int(rules(r)["max_value_cents"]))
    return {"cap_cents": max(v, base), "basis": "declared_value_cover"}


def shipment_claim_cap_cents(parcel_caps_cents: list[int], categories: list[str | None] | None = None) -> dict[str, Any]:
    """Most we pay for one shipment: the parcel caps added up, never above the cargo policy limit
    ($50,000; $25,000 when any parcel is a target commodity)."""
    total = sum(max(int(c or 0), 0) for c in parcel_caps_cents)
    limit = POLICY.shipment_limit_cents(categories)
    return {"cap_cents": min(total, limit), "limit_cents": limit, "capped": total > limit,
            "target_commodity": limit == POLICY.CARGO["target_commodities_cents"]}

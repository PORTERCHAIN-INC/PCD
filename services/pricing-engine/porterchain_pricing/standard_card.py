"""PorterChain Standard rate card v1 + the one quote function (doc 72 §2, §8, §9.2).

Price = zone band price + add-ons (+ route minimum top-up for B2B) + HST on its own line.
Integer cents throughout. Every mandatory charge is inside the headline price (drip rule).
Card "lines" are plain JSON so versions can be stored, edited, diffed and published.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from porterchain_pricing.declared_value import RULES as _DV_RULES
from porterchain_pricing.declared_value import quote_parcels as _dv_quote
from porterchain_pricing.declared_value import rules as _dv_rules

ZONES = ("Z1", "Z2", "Z3")
ZONE_LABELS = {"Z1": "Toronto", "Z2": "Near GTA", "Z3": "Regional"}
BAND_ORDER = ("XS", "S", "M", "L", "XL")

STANDARD_V1_LINES: dict[str, Any] = {
    "currency": "cad",
    "hst_rate": 0.13,
    "dim_factor_cm3_per_kg": 5000,
    "zone_adder_cents": {"Z1": 0, "Z2": 1500, "Z3": 3000},
    "bands": {
        "XS": {"label": "Envelope / small", "max_kg": 2, "max_side_cm": 40, "z1_cents": 1700},
        "S": {"label": "Parcel", "max_kg": 10, "max_side_cm": 60, "z1_cents": 1800},
        "M": {"label": "Large parcel", "max_kg": 25, "max_side_cm": 100, "z1_cents": 2600},
        "L": {"label": "Bulky", "max_kg": 50, "max_side_cm": 180, "z1_cents": 4900},
        "XL": {"label": "Furniture", "max_kg": 120, "max_side_cm": 250, "z1_cents": 12900},
        "P": {"label": "Pallet", "max_kg": 500, "max_side_cm": 120, "z1_cents": 9500},
    },
    "furniture_classes": {
        "F1": {"label": "Small item", "z1_cents": 4900},
        "F2": {"label": "Medium item", "z1_cents": 8900},
        "F3": {"label": "Large item", "z1_cents": 12900},
        "F4": {"label": "Oversize (dolly included)", "z1_cents": 22900, "two_person_included": True},
    },
    "furniture_extra_item_pct": 50,
    "add_ons": {
        # Ravi 2026-10-29: no two-person or white-glove service. The dolly add-on replaces two-person.
        # Ravi 2026-10-29: dolly add-on fixed at $20.
        "dolly": {"label": "Dolly handling (heavy parcel, one driver)", "cents": 2000},
        "two_person": {"label": "2-person delivery", "cents": 6000, "retired": True, "alias_of": "dolly"},
        "stairs_floor": {"label": "Stairs, per floor without elevator", "cents": 1000},
        "assembly_simple": {"label": "Assembly (simple)", "cents": 3500},
        "assembly_standard": {"label": "Assembly (standard)", "cents": 6500},
        "white_glove": {"label": "White-glove unpack", "cents": 2500, "retired": True},
        "window_2h": {"label": "2-hour time window", "cents": 1500},
        "same_day": {"label": "Same-day rush", "cents": 2000},
        "signature": {"label": "Signature / ID check", "cents": 300},
        "food_handling": {"label": "Food / upright handling", "cents": 0},
        "waiting_15min": {"label": "Waiting, per 15 min", "cents": 750, "b2b_only": True},
    },
    "b2b": {
        "band_discount_pct": {"S": 10, "M": 10},
        "route_minimum_cents": {"Z1": 6000, "Z2": 9000, "Z3": 12000},
        "cancellation": {
            "before_cutoff_pct": 0,
            "after_dispatch_pct": 25,
            "after_dispatch_min_cents": 1500,
            "at_pickup_pct": 50,
        },
    },
    "guardrails": {"min_pct": -30, "max_pct": 50},
    # Ravi 2026-10-29: optional declared-value cover, 1.5% of value, $3 min, $2,500 max per parcel; excluded goods;
    # proof of value to claim; default liability $4.41/kg. Off until cargo insurance is confirmed (G-INS).
    "declared_value": copy.deepcopy(_DV_RULES),
}

STANDARD_CODE = "porterchain-standard"


def standard_v1() -> dict[str, Any]:
    return copy.deepcopy(STANDARD_V1_LINES)


class ManualQuoteRequired(ValueError):
    """Outside the card (over 120 kg per item, piano/safe, outside 150 km)."""


@dataclass
class Item:
    kind: str = "parcel"  # parcel | pallet | furniture
    weight_kg: float = 0.0
    length_cm: float = 0.0
    width_cm: float = 0.0
    height_cm: float = 0.0
    furniture_class: str | None = None
    qty: int = 1


@dataclass
class OrgPricing:
    """Custom mode presets (doc 72 §9.2). Standard mode = all empty."""

    mode: str = "standard"
    preset_pct: float | None = None
    preset_per_stop_cents: int | None = None
    # Flat price per parcel, any size (Ravi 2026-11-03, e.g. Wintergreen $9). Replaces the $6/$9 + handling.
    flat_parcel_cents: int | None = None
    band_overrides: dict[str, int] = field(default_factory=dict)  # "S:Z1" -> cents
    guardrail_min_pct: float | None = None
    guardrail_max_pct: float | None = None


def inches_to_cm(value: float) -> float:
    return round(value * 2.54, 1)


def billable_kg(item: Item, dim_factor: int = 5000) -> float:
    dim = (item.length_cm * item.width_cm * item.height_cm) / dim_factor
    return round(max(item.weight_kg, dim), 2)


def band_for(item: Item, lines: dict[str, Any]) -> str:
    if item.kind == "pallet":
        if item.weight_kg > lines["bands"]["P"]["max_kg"]:
            raise ManualQuoteRequired("pallet_over_weight")
        return "P"
    kg = billable_kg(item, lines["dim_factor_cm3_per_kg"])
    longest = max(item.length_cm, item.width_cm, item.height_cm)
    for code in BAND_ORDER:
        b = lines["bands"][code]
        if kg <= b["max_kg"] and longest <= b["max_side_cm"]:
            return code
    raise ManualQuoteRequired("over_card_limits")


def margin_colour(price_cents: int, cost_cents: int) -> str:
    """Staff-only colour (never blocks): green ≥ 50 %, yellow 35–50 %, red < 35 %."""
    if price_cents <= 0:
        return "red"
    m = (price_cents - cost_cents) / price_cents
    if m >= 0.5:
        return "green"
    if m >= 0.35:
        return "yellow"
    return "red"


def _zone_price(z1_cents: int, zone: str, lines: dict[str, Any]) -> int:
    if zone not in ZONES:
        raise ManualQuoteRequired("outside_service_area")
    return int(z1_cents) + int(lines["zone_adder_cents"][zone])


def _hst(cents: int, rate: float) -> int:
    return int((cents * rate * 100 + 50) // 100)


def quote(
    items: list[Item],
    zone: str,
    *,
    add_ons: dict[str, int] | None = None,
    audience: str = "retail",
    lines: dict[str, Any] | None = None,
    org: OrgPricing | None = None,
    stops: int = 1,
    apply_minimum: bool = True,
    declared_values: list[int] | None = None,
    declared_categories: list[str | None] | None = None,
    cargo_insurance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The single Standard-card price. Returns explainer lines + subtotal/HST/total.
    ``declared_values`` (cents, one per parcel) buys declared-value cover; raises ValueError while it is off (G-INS)
    or for a parcel that can't be covered (over $2,500, excluded goods)."""
    lines = lines or STANDARD_V1_LINES
    add_ons = {k: int(v) for k, v in (add_ons or {}).items() if int(v) > 0}
    b2b = audience == "b2b"
    out: list[dict[str, Any]] = []
    two_person_included = False

    furniture_seen = 0
    for it in items:
        for n in range(max(1, int(it.qty))):
            if it.kind == "furniture":
                cls = lines["furniture_classes"].get(it.furniture_class or "")
                if not cls:
                    raise ManualQuoteRequired("unknown_furniture_class")
                if it.weight_kg > 120:
                    raise ManualQuoteRequired("item_over_120kg")
                price = _zone_price(cls["z1_cents"], zone, lines)
                if furniture_seen > 0:
                    price = price * int(lines["furniture_extra_item_pct"]) // 100
                furniture_seen += 1
                two_person_included |= bool(cls.get("two_person_included"))
                out.append({"key": f"{it.furniture_class}:{zone}", "label": cls["label"], "cents": price})
                continue
            band = band_for(it, lines)
            price = _zone_price(lines["bands"][band]["z1_cents"], zone, lines)
            if b2b:
                pct = int(lines["b2b"]["band_discount_pct"].get(band, 0))
                price = price * (100 - pct) // 100
            out.append(
                {
                    "key": f"{band}:{zone}",
                    "label": f"{band} {lines['bands'][band]['label']}",
                    "billable_kg": billable_kg(it, lines["dim_factor_cm3_per_kg"]) if band != "P" else None,
                    "cents": price,
                }
            )

    for key, qty in sorted(add_ons.items()):
        a = lines["add_ons"].get(key)
        if a is None:
            raise ValueError(f"unknown_add_on:{key}")
        if a.get("alias_of"):
            key, a = a["alias_of"], lines["add_ons"][a["alias_of"]]
        if a.get("retired"):
            raise ValueError(f"retired_add_on:{key}")
        if a.get("b2b_only") and not b2b:
            continue
        if key == "dolly" and two_person_included:
            continue
        out.append({"key": f"addon:{key}", "label": a["label"], "qty": qty, "cents": int(a["cents"]) * qty})

    standard = [dict(line) for line in out]
    if org and org.mode == "custom":
        _apply_org(out, org, lines, stops)

    cover = None
    if declared_values:
        # G-INS: the card's ``enabled`` is only a request; cargo_insurance must be confirmed too.
        cover = _dv_quote(list(declared_values), declared_categories,
                          _dv_rules(lines.get("declared_value") or _DV_RULES, cargo_insurance))
        out.append({"key": "addon:declared_value", "label": "Declared-value cover (1.5%, min $3 per parcel)",
                    "qty": len(cover["lines"]), "cents": cover["cents"]})
    subtotal = sum(line["cents"] for line in out)
    if b2b and apply_minimum:
        minimum = int(lines["b2b"]["route_minimum_cents"][zone])
        if subtotal < minimum:
            out.append({"key": "route_minimum", "label": "Minimum charge", "cents": minimum - subtotal})
            subtotal = minimum
    hst = _hst(subtotal, float(lines["hst_rate"]))
    return {
        "zone": zone,
        "zone_label": ZONE_LABELS[zone],
        "audience": audience,
        "lines": out,
        "standard_subtotal_cents": sum(line["cents"] for line in standard),
        "subtotal_cents": subtotal,
        "hst_cents": hst,
        "total_cents": subtotal + hst,
        "currency": lines["currency"],
        "declared_value": cover,
    }


def _apply_org(out: list[dict[str, Any]], org: OrgPricing, lines: dict[str, Any], stops: int) -> None:
    g = lines.get("guardrails", {})
    lo = org.guardrail_min_pct if org.guardrail_min_pct is not None else g.get("min_pct", -30)
    hi = org.guardrail_max_pct if org.guardrail_max_pct is not None else g.get("max_pct", 50)
    priced = [line for line in out if line["cents"] > 0]
    for line in out:
        std = line["cents"]
        new = std
        if line["key"] in org.band_overrides:
            new = int(org.band_overrides[line["key"]])
        if org.preset_pct:
            new = int(round(new * (100 + float(org.preset_pct)) / 100))
        if std > 0:
            pct = (new - std) * 100 / std
            if pct < lo or pct > hi:
                raise ValueError(f"guardrail:{line['key']}")
        line["standard_cents"] = std
        line["cents"] = new
    if org.preset_per_stop_cents and priced:
        delta = int(org.preset_per_stop_cents) * max(1, stops)
        out.append({"key": "preset_per_stop", "label": "Per-stop adjustment", "cents": delta})


def sample_basket_preview(lines: dict[str, Any], org: OrgPricing | None = None) -> list[dict[str, Any]]:
    """Live preview basket (doc 72 §9.2): one order per band in Z1 plus a 12-stop route."""
    samples = {
        "XS": Item(weight_kg=1, length_cm=30, width_cm=20, height_cm=2),
        "S": Item(weight_kg=4, length_cm=40, width_cm=30, height_cm=20),
        "M": Item(weight_kg=20, length_cm=70, width_cm=45, height_cm=12),
        "L": Item(weight_kg=35, length_cm=150, width_cm=50, height_cm=20),
        "XL": Item(kind="furniture", furniture_class="F3", weight_kg=60),
        "P": Item(kind="pallet", weight_kg=380, length_cm=120, width_cm=100, height_cm=150),
    }
    rows = []
    for band, item in samples.items():
        std = quote([item], "Z1", audience="b2b", lines=lines, apply_minimum=False)
        cus = quote([item], "Z1", audience="b2b", lines=lines, org=org, apply_minimum=False)
        rows.append({"sample": band, "standard_cents": std["subtotal_cents"], "custom_cents": cus["subtotal_cents"], "hst_cents": cus["hst_cents"]})
    route = [samples["S"]] * 12
    std = quote(route, "Z1", audience="b2b", lines=lines, stops=12)
    cus = quote(route, "Z1", audience="b2b", lines=lines, org=org, stops=12)
    rows.append({"sample": "route_12_stops", "standard_cents": std["subtotal_cents"], "custom_cents": cus["subtotal_cents"], "hst_cents": cus["hst_cents"]})
    return rows


def diff_lines(old: dict[str, Any], new: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flat field diff for the pricing audit row."""
    out: dict[str, Any] = {}
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k), new.get(k)
        path = f"{prefix}{k}"
        if isinstance(a, dict) and isinstance(b, dict):
            out.update(diff_lines(a, b, path + "."))
        elif a != b:
            out[path] = {"from": a, "to": b}
    return out

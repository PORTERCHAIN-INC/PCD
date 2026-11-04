"""Live pricing on the Standard rate card (doc 72): one price for every channel.

Checkout (Shopify carrier rates), public quotes, merchant booking, CSV import and the
admin order builder all reach ``PricingService.calculate*``; the hook in
``smart_apply.SmartAwarePricingService`` sends them here when
``pricing_standard_card_live`` is on. Merchants on Custom pricing get their org
presets / band overrides (within guardrails). Anything outside the card returns a
0-cent breakdown flagged ``manual_quote`` so checkout shows the flat-rate fallback
and staff send a quote instead.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_pricing.components.size_weight import parse_dimensions_cm
from porterchain_pricing.standard_card import Item, ManualQuoteRequired, OrgPricing, quote
from porterchain_pricing.types import PriceBreakdown, PriceLineItem, PricingRequest

_POSTAL = re.compile(r"\b([A-Z]\d[A-Z])\s?\d[A-Z]\d\b")
#: Near-GTA FSAs (Durham, York, Peel, Halton) -> Z2. Other L/N within reach -> Z3.
_Z2_PREFIX = ("L1", "L3", "L4", "L5", "L6")
_Z2_FSA = {"L7A", "L7C", "L7E", "L7L", "L7M", "L7N", "L7P", "L7R", "L7S", "L7T"}
_Z3_PREFIX = ("L0", "L2", "L7", "L8", "L9", "N0", "N1", "N2", "N3")


def fsa_of(point: Any) -> str:
    raw = (getattr(point, "postal", "") or "").upper().replace(" ", "")
    if len(raw) >= 3 and _POSTAL.match(raw[:3] + "0A0"):
        return raw[:3]
    m = _POSTAL.search((getattr(point, "formatted", "") or "").upper())
    return m.group(1) if m else ""


def zone_for_fsa(fsa: str) -> str:
    fsa = (fsa or "").upper()
    if not fsa:
        raise ManualQuoteRequired("no_postal_code")
    if fsa.startswith("M"):
        return "Z1"
    if fsa in _Z2_FSA or fsa.startswith(_Z2_PREFIX):
        return "Z2"
    if fsa.startswith(_Z3_PREFIX):
        return "Z3"
    raise ManualQuoteRequired("outside_service_area")


def org_id_for_merchant(db: Session, merchant_id: str | None) -> str | None:
    if not merchant_id:
        return None
    from porterchain_api.org_engine.models import Organisation

    org = db.scalar(select(Organisation).where(Organisation.merchant_id == merchant_id))
    return org.id if org else merchant_id


def org_pricing(db: Session, org_id: str | None) -> OrgPricing | None:
    if not org_id:
        return None
    from porterchain_api.pricing_engine.models import PricingOrgPricing

    row = db.get(PricingOrgPricing, org_id)
    if row is None or row.mode != "custom":
        return None
    if row.expires_at and row.expires_at.replace(tzinfo=row.expires_at.tzinfo or UTC) < datetime.now(UTC):
        return None
    return OrgPricing(mode="custom", preset_pct=row.preset_pct, preset_per_stop_cents=row.preset_per_stop_cents,
                      flat_parcel_cents=getattr(row, "flat_parcel_cents", None),
                      band_overrides=dict(row.band_overrides or {}))


def published_lines(db: Session) -> tuple[dict[str, Any], int]:
    from porterchain_api.pricing_engine.models import PricingRateCard, PricingRateCardVersion
    from porterchain_pricing.standard_card import STANDARD_CODE, standard_v1

    card = db.scalar(select(PricingRateCard).where(PricingRateCard.code == STANDARD_CODE))
    if card is not None:
        v = db.scalar(
            select(PricingRateCardVersion)
            .where(PricingRateCardVersion.rate_card_id == card.id, PricingRateCardVersion.status == "published")
            .order_by(PricingRateCardVersion.version.desc())
        )
        if v is not None:
            return v.lines, v.version
    return standard_v1(), 1


def _item(weight: float | None, dims: Any) -> Item:
    length, width, height = parse_dimensions_cm(dims)
    return Item(weight_kg=float(weight or 0), length_cm=length or 0, width_cm=width or 0, height_cm=height or 0)


def items_from_request(request: PricingRequest) -> list[Item]:
    if request.parcels:
        return [_item(p.weight_kg, p.dimensions) for p in request.parcels]
    n = max(1, int(request.parcel_count or 1))
    per = (request.weight_kg or 0) / n
    return [Item(**{**_item(per, request.dimensions).__dict__, "qty": n})]


def add_ons_from_request(request: PricingRequest) -> dict[str, int]:
    add: dict[str, int] = {}
    if request.wait_minutes and request.channel == "merchant":
        add["waiting_15min"] = int(-(-float(request.wait_minutes) // 15))
    if request.delivery_point == "past_designated_point":
        add["dolly"] = 1
    return add


def standard_breakdown(db: Session, request: PricingRequest) -> PriceBreakdown | None:
    """None when the drop has no postal code, or for a whole-vehicle booking (doc 72: the
    Vehicle row stays on the gta_rate card), so the caller keeps the previous engine."""
    if getattr(request, "booking_mode", "parcels") == "vehicle" or not fsa_of(request.dropoff):
        return None
    lines, version = published_lines(db)
    audience = "b2b" if request.channel == "merchant" else "retail"
    org_id = org_id_for_merchant(db, request.merchant_id)
    meta: dict[str, Any] = {"pricing": "standard_card", "card_version": version, "audience": audience, "org_id": org_id}
    try:
        zone = zone_for_fsa(fsa_of(request.dropoff))
        stops = 1 + len(request.additional_stops or [])
        q = quote(items_from_request(request), zone, add_ons=add_ons_from_request(request), audience=audience,
                  lines=lines, org=org_pricing(db, org_id), stops=stops,
                  apply_minimum=audience == "b2b" and stops > 1)
    except ManualQuoteRequired as exc:
        return PriceBreakdown(metadata={
            **meta, "manual_quote": True, "manual_reason": str(exc),
            # Same contract as an FSA refusal: every booking path refuses a $0 price.
            "fsa_refused": True, "custom_quote": True, "custom_quote_reason": str(exc),
        })
    except ValueError as exc:  # guardrail breach on a stale custom row -> standard price
        meta["custom_ignored"] = str(exc)
        q = quote(items_from_request(request), zone, add_ons=add_ons_from_request(request), audience=audience,
                  lines=lines, stops=1 + len(request.additional_stops or []), apply_minimum=False)
    bd = PriceBreakdown(
        items=[PriceLineItem(code=line["key"], label=line["label"], amount_cents=int(line["cents"])) for line in q["lines"]],
        zone_code=q["zone"], currency=q["currency"],
        metadata={**meta, "zone_label": q["zone_label"], "standard_subtotal_cents": q["standard_subtotal_cents"]},
    )
    bd.base_cents = q["subtotal_cents"]
    bd.subtotal_cents = q["subtotal_cents"]
    bd.tax_cents = q["hst_cents"]
    bd.final_cents = q["total_cents"]
    return bd

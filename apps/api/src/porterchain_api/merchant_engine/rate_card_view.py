"""Merchant-facing rate card — same engine as admin, no driver payout internals."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import PricingFsaRate
from porterchain_api.merchant_models import Merchant
from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_api.domain.catalog_labels import VEHICLE_LABELS
from porterchain_pricing.policy import (
    MODEL_DISTANCE,
    MODEL_FSA,
    MerchantPricingPolicy,
    policy_from_config,
)
from porterchain_pricing.types import GeoPoint, PricingRequest

_WHAT_WINS = {
    MODEL_FSA: "This account is priced on Ontario FSA flat rates.",
    MODEL_DISTANCE: "This account is priced by distance and vehicle class.",
}


def _policy_for_merchant(merchant: Merchant) -> MerchantPricingPolicy:
    policy = policy_from_config(merchant.pricing_config or {})
    model = getattr(merchant, "pricing_model", None) or MODEL_DISTANCE
    policy.pricing_model = model if model in (MODEL_FSA, MODEL_DISTANCE) else MODEL_DISTANCE
    return policy


def _cad_to_cents(value: float | int | None) -> int:
    return int(round(float(value or 0) * 100))


def fsa_rate_counts(db: Session, merchant_id: str) -> tuple[int, int]:
    rows = (
        db.query(PricingFsaRate.merchant_id)
        .filter(
            PricingFsaRate.is_active.is_(True),
            or_(
                PricingFsaRate.merchant_id.is_(None),
                PricingFsaRate.merchant_id == merchant_id,
            ),
        )
        .all()
    )
    own = sum(1 for (owner,) in rows if owner == merchant_id)
    return own, len(rows) - own


def merchant_rate_card(db: Session, merchant: Merchant) -> dict[str, Any]:
    """Read-only card: model, GTA vehicles, size/weight, surcharges, tax, FSA counts."""
    request = PricingRequest(
        pickup=GeoPoint(lat=43.65, lng=-79.38, postal="M5V 1A1"),
        dropoff=GeoPoint(lat=43.70, lng=-79.40, postal="M2N 1A1"),
        vehicle_class="cargo_van",
        channel="merchant",
        merchant_id=merchant.id,
    )
    ctx = SqlAlchemyPricingRepository(db).load_context(request)
    policy = ctx.merchant_policy or _policy_for_merchant(merchant)
    gta = ctx.gta_rate
    card = ctx.rate_card
    tax = ctx.tax
    fuel = ctx.fuel
    own, platform = fsa_rate_counts(db, merchant.id)

    vehicles: list[dict[str, Any]] = []
    included_km = float(gta.base_km_limit) if gta else 20.0
    if gta:
        for vehicle_id, rates in gta.vehicles.items():
            vehicles.append(
                {
                    "id": vehicle_id,
                    "label": VEHICLE_LABELS.get(vehicle_id, vehicle_id.replace("_", " ").title()),
                    "base_cents": _cad_to_cents(rates.get("base_price")),
                    "extra_km_cents": _cad_to_cents(rates.get("extra_km_rate")),
                    "extra_pickup_cents": _cad_to_cents(rates.get("extra_pick_fee")),
                    "extra_drop_cents": _cad_to_cents(rates.get("extra_drop_fee")),
                }
            )

    model = policy.pricing_model
    downtown_cents = _cad_to_cents(gta.downtown_fee_cad) if gta else 0
    upper_cents = _cad_to_cents(gta.upper_zone_fee_cad) if gta else 0
    schedule = policy.schedule
    if schedule.fuel_surcharge_percent is not None:
        effective_fuel = float(schedule.fuel_surcharge_percent)
    else:
        effective_fuel = float(fuel.surcharge_percent) if fuel else 0.0
    return {
        "pricing_model": model,
        "what_wins": _WHAT_WINS.get(model, _WHAT_WINS[MODEL_DISTANCE]),
        "vehicles": vehicles,
        "included_km": included_km,
        "size_tiers": [t.to_dict() for t in policy.size_tiers],
        "surcharges": {
            "downtown": policy.charge_downtown,
            "upper_zone": policy.charge_upper_zone,
            "downtown_cents": downtown_cents,
            "upper_zone_cents": upper_cents,
        },
        "liftgate_cents": int(card.liftgate_cents) if card else 0,
        "fuel_surcharge_percent": effective_fuel,
        "schedule": schedule.to_dict(),
        "tax": {
            "hst_percent": float(tax.hst_percent) if tax else 0.0,
            "tax_included": bool(tax.tax_included) if tax else False,
        },
        "weight": {
            "threshold_kg": float(card.weight_threshold_kg) if card else 0.0,
            "cents_per_kg": int(card.weight_cents_per_kg) if card else 0,
        },
        "fsa_rate_count": own,
        "platform_fsa_rate_count": platform,
        "currency": "cad",
    }


def admin_pricing_view(db: Session, merchant: Merchant) -> dict[str, Any]:
    """Admin Pricing tab: policy controls + the same card the merchant GET uses."""
    policy = _policy_for_merchant(merchant)
    own, platform = fsa_rate_counts(db, merchant.id)
    cfg = dict(merchant.pricing_config or {})
    gta_overlay = cfg.get("gta_rate") if isinstance(cfg.get("gta_rate"), dict) else None
    system_gta = SqlAlchemyPricingRepository(db)._load_gta_rate_config()
    return {
        "merchant_id": merchant.id,
        "pricing_model": policy.pricing_model,
        "surcharges": {
            "downtown": policy.charge_downtown,
            "upper_zone": policy.charge_upper_zone,
        },
        "size_tiers": [t.to_dict() for t in policy.size_tiers],
        "gta_rate": gta_overlay,
        "rate_card": dict(cfg.get("rate_card") or {}) or None,
        "schedule": policy.schedule.to_dict(),
        "has_custom_gta": bool(gta_overlay),
        "platform_gta_rate": system_gta.to_dict() if system_gta else None,
        "fsa_rate_count": own,
        "platform_fsa_rate_count": platform,
        "card": merchant_rate_card(db, merchant),
    }

"""
Independently callable pricing components.

Each endpoint prices exactly one element of a delivery — distance, extra stops,
location surcharges, size and weight, or an FSA flat rate — so a caller can
compose only the elements a route needs instead of asking for a whole quote.
The same service objects back `PricingEngine`, so a component priced here always
agrees with that component inside a full quote.

Admin-scoped: these expose raw rate configuration. Customer- and merchant-facing
prices still come from `/v1/quotes` and `/v1/merchant/booking/preview`.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.admin_engine.fsa_admin_service import FsaAdminService
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_api.schemas_pricing import (
    ComponentResponse,
    DistanceRequest,
    FsaQuoteRequest,
    FsaRateBody,
    FsaRateBulkBody,
    FsaRateOut,
    LocationRequest,
    SizeWeightRequest,
    StopsRequest,
)
from porterchain_pricing.components import (
    DistanceRateService,
    FsaRateService,
    LocationSurchargeService,
    SizeWeightService,
    StopFeeService,
)
from porterchain_pricing.components.size_weight import config_from_rate_card
from porterchain_pricing.gta_rate import gta_rate_config_from_dict

router = APIRouter(prefix="/v1/pricing/components", tags=["pricing-components"])

_distance = DistanceRateService()
_stops = StopFeeService()
_location = LocationSurchargeService()
_size_weight = SizeWeightService()
_fsa = FsaRateService()
_fsa_admin = FsaAdminService()
_merchants = AdminMerchantService()

AdminDep = Annotated[AdminContext, Depends(get_admin_context)]
DbDep = Annotated[Session, Depends(get_db)]


def _gta_config(db: Session, overrides: dict[str, Any] | None):
    """Live GTA config, with any caller overrides layered on for what-if pricing."""
    stored = SqlAlchemyPricingRepository(db)._load_gta_rate_config()
    if not overrides:
        return stored
    merged = {**stored.to_dict(), **overrides} if hasattr(stored, "to_dict") else overrides
    try:
        return gta_rate_config_from_dict(merged)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid_rate_override: {exc}") from exc


# ---------------------------------------------------------------- distance


@router.post("/distance", response_model=ComponentResponse)
def quote_distance(body: DistanceRequest, _: AdminDep, db: DbDep) -> ComponentResponse:
    """Base fare covering the first N km, plus the per-km rate beyond it."""
    quote = _distance.quote(
        vehicle_type=body.vehicle_type,
        total_km=body.total_km,
        config=_gta_config(db, body.config_overrides),
    )
    return ComponentResponse(**quote.to_dict())


# ------------------------------------------------------------------- stops


@router.post("/stops", response_model=ComponentResponse)
def quote_stops(body: StopsRequest, _: AdminDep, db: DbDep) -> ComponentResponse:
    """Fees for pickups and drops beyond the first of each."""
    quote = _stops.quote(
        vehicle_type=body.vehicle_type,
        total_pickups=body.total_pickups,
        total_drops=body.total_drops,
        config=_gta_config(db, body.config_overrides),
    )
    return ComponentResponse(**quote.to_dict())


# ---------------------------------------------------------------- location


@router.post("/location", response_model=ComponentResponse)
def quote_location(body: LocationRequest, _: AdminDep, db: DbDep) -> ComponentResponse:
    """Downtown Toronto and Markham / North York surcharges, each at most once."""
    quote = _location.quote(
        pickup=body.pickup.to_geo() if body.pickup else None,
        dropoff=body.dropoff.to_geo() if body.dropoff else None,
        additional_stops=[s.to_geo() for s in body.additional_stops],
        is_downtown=body.is_downtown,
        is_upper_zone=body.is_upper_zone,
        config=_gta_config(db, body.config_overrides),
    )
    return ComponentResponse(**quote.to_dict())


# ------------------------------------------------------------- size /weight


@router.post("/size-weight", response_model=ComponentResponse)
def quote_size_weight(body: SizeWeightRequest, _: AdminDep, db: DbDep) -> ComponentResponse:
    """Same size/weight charge the engine uses for this merchant (tiers or rate card)."""
    repo = SqlAlchemyPricingRepository(db)
    card = repo._load_rate_card()
    if body.merchant_id:
        from porterchain_pricing.policy import policy_from_config
        from porterchain_pricing.rate_card import merge_merchant_overlay

        merchant = _merchants.get_merchant(db, body.merchant_id)
        if merchant:
            config = dict(merchant.pricing_config or {})
            policy = policy_from_config(config)
            if policy.size_tiers:
                quote = _size_weight.quote_tiers(
                    policy.size_tiers,
                    weight_kg=body.weight_kg,
                    dimensions=body.dimensions,
                )
                return ComponentResponse(**quote.to_dict())
            card = merge_merchant_overlay(card, config)

    quote = _size_weight.quote(
        weight_kg=body.weight_kg,
        dimensions=body.dimensions,
        declared_value_cents=body.declared_value_cents,
        config=config_from_rate_card(card),
    )
    return ComponentResponse(**quote.to_dict())


# --------------------------------------------------------------------- FSA


@router.post("/fsa", response_model=ComponentResponse)
def quote_fsa(body: FsaQuoteRequest, _: AdminDep, db: DbDep) -> ComponentResponse:
    """
    Flat rate for a destination FSA, if one is configured.

    `metadata.matched` is false when no rate covers the destination — the caller
    should then fall back to the distance component.
    """
    rates = SqlAlchemyPricingRepository(db)._load_fsa_rates(body.merchant_id)
    quote = _fsa.quote(
        rates,
        pickup=body.pickup.to_geo() if body.pickup else None,
        dropoff=body.dropoff.to_geo() if body.dropoff else None,
        dest_fsa=body.dest_fsa or "",
        origin_fsa=body.origin_fsa or "",
        merchant_id=body.merchant_id,
        vehicle_class=body.vehicle_class,
    )
    return ComponentResponse(**quote.to_dict())


# ------------------------------------------------------- FSA rate management


@router.get("/fsa/rates", response_model=list[FsaRateOut])
def list_fsa_rates(
    _: AdminDep,
    db: DbDep,
    merchant_id: str | None = None,
    dest_fsa: str | None = None,
) -> list[FsaRateOut]:
    return _fsa_admin.list_rates(db, merchant_id=merchant_id, dest_fsa=dest_fsa)


@router.get("/fsa/coverage-gap")
def fsa_coverage_gap(
    _: AdminDep,
    db: DbDep,
    merchant_id: str | None = None,
) -> dict:
    """GTA150 tile checklist: how many in-tile FSAs lack a priced row."""
    return _fsa_admin.coverage_gap(db, merchant_id=merchant_id)


@router.post("/fsa/rates", response_model=FsaRateOut, status_code=201)
def create_fsa_rate(body: FsaRateBody, _: AdminDep, db: DbDep) -> FsaRateOut:
    try:
        return _fsa_admin.create_rate(db, body)
    except ValueError as exc:
        detail = str(exc)
        code = 409 if detail == "fsa_rate_already_exists" else 422
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/fsa/rates/bulk")
def bulk_fsa_rates(body: FsaRateBulkBody, _: AdminDep, db: DbDep) -> dict:
    """Bulk upsert FSA flats against GTA150 registry (rejects out-of-tile)."""
    try:
        return _fsa_admin.bulk_upsert(db, body.rates, merchant_id=body.merchant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/fsa/rates/{rate_id}", response_model=FsaRateOut)
def update_fsa_rate(rate_id: str, body: FsaRateBody, _: AdminDep, db: DbDep) -> FsaRateOut:
    try:
        return _fsa_admin.update_rate(db, rate_id, body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/fsa/rates/{rate_id}", status_code=204)
def delete_fsa_rate(rate_id: str, _: AdminDep, db: DbDep) -> None:
    try:
        _fsa_admin.delete_rate(db, rate_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

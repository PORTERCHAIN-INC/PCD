"""Admin full-quote simulator — Pricing Center."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas_pricing import PointInput, SimulateQuoteRequest, SimulateQuoteResponse
from porterchain_api.pricing_engine.margin_settings import load_margin_estimates
from porterchain_pricing.margin import distance_outlier, margin_check
from porterchain_pricing.suggest import suggest_liftgate
from porterchain_pricing.types import PricingRequest

router = APIRouter(prefix="/v1/pricing", tags=["pricing"])

AdminDep = Annotated[AdminContext, Depends(get_admin_context)]
DbDep = Annotated[Session, Depends(get_db)]

_DEFAULT_PICKUP = PointInput(lat=43.65, lng=-79.38, formatted="Toronto, ON", postal="M5V 1A1")
_DEFAULT_DROPOFF = PointInput(lat=43.70, lng=-79.40, formatted="North York, ON", postal="M2N 1A1")


def _geocoded(point: PointInput) -> PointInput:
    """Any typed address or postal code works: geocode when coordinates are missing."""
    if point.lat is not None and point.lng is not None:
        return point
    from porterchain_api.merchant_engine.import_geocode import geocode_stop

    geo = geocode_stop(
        address=point.formatted or "", postal=point.postal, lat=None, lng=None
    )
    if geo.lat is None or geo.lng is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="address_not_found")
    return point.model_copy(
        update={
            "lat": geo.lat,
            "lng": geo.lng,
            "formatted": geo.formatted or point.formatted,
        }
    )


def _what_won(meta: dict) -> str:
    model = str(meta.get("pricing_model") or "")
    if model == "fsa_flat_rate":
        return "FSA flat rate set the base"
    if model == "contract_tariff":
        return "Merchant-scoped tariff / contract set the base"
    if model == "gta_delivery_rate":
        if meta.get("fsa_fallback"):
            return "Distance (GTA) — FSA miss, fell back"
        return "Distance (GTA) matrix set the base"
    if model:
        return f"Base from {model.replace('_', ' ')}"
    return "No base layer recorded"


@router.post("/simulate", response_model=SimulateQuoteResponse)
def simulate_quote(body: SimulateQuoteRequest, _: AdminDep, db: DbDep) -> SimulateQuoteResponse:
    """Preview a full quote with live merchant overlays (no persistence)."""
    pickup = _geocoded(body.pickup or _DEFAULT_PICKUP).to_geo()
    dropoff = _geocoded(body.dropoff or _DEFAULT_DROPOFF).to_geo()
    distance_meters = body.distance_meters
    route_seconds = None
    if not body.use_typed_distance and pickup.lat is not None and dropoff.lat is not None:
        from porterchain_api.services.routing import resolve_route_distance

        routed, _seconds, _source = resolve_route_distance(pickup, dropoff)
        if routed is not None:
            distance_meters = routed
            route_seconds = _seconds
    channel = "merchant" if body.merchant_id else (body.channel or "retail")
    request = PricingRequest(
        pickup=pickup,
        dropoff=dropoff,
        vehicle_class=body.vehicle_class,
        channel=channel,
        merchant_id=body.merchant_id,
        distance_meters=distance_meters,
        total_pickups=body.total_pickups,
        total_drops=body.total_drops,
        weight_kg=body.weight_kg,
        dimensions=body.dimensions,
        parcel_count=body.parcel_count,
        requires_liftgate=body.requires_liftgate,
        is_downtown=body.is_downtown,
        is_upper_zone=body.is_upper_zone,
        declared_value_cents=body.declared_value_cents,
        coverage_upgrade=body.coverage_upgrade,
        item_category=body.item_category,
    )
    service = get_pricing_service(db)
    estimates = load_margin_estimates(db)
    overrides = {}
    if body.gta_rate_override:
        overrides["gta_rate"] = body.gta_rate_override
    breakdown = service.simulator.simulate(request, overrides=overrides or None)
    api = service.to_api_breakdown(breakdown)
    meta = dict(api.get("metadata") or {})
    return SimulateQuoteResponse(
        final_cents=int(api["final_cents"]),
        subtotal_cents=int(api["subtotal_cents"]),
        tax_cents=int(api["tax_cents"]),
        base_cents=int(api["base_cents"]),
        currency=str(api.get("currency") or "cad"),
        pricing_model=meta.get("pricing_model"),
        pricing_model_requested=meta.get("pricing_model_requested"),
        items=list(api.get("items") or []),
        metadata=meta,
        what_won=_what_won(meta),
        coverage=meta.get("coverage"),
        liftgate_suggestion=None
        if body.requires_liftgate
        else suggest_liftgate(
            weight_kg=body.weight_kg,
            threshold_kg=float(estimates.get("liftgate_weight_kg") or 70),
        ),
        margin=margin_check(
            int(api["subtotal_cents"]),
            distance_meters,
            duration_seconds=route_seconds,
            pickups=body.total_pickups or 1,
            drops=body.total_drops or 1,
            vehicle_class=body.vehicle_class,
            overrides=estimates,
        ).as_dict(),
        distance_flag=distance_outlier(
            distance_meters,
            (pickup.lat, pickup.lng) if pickup.lat is not None else None,
            (dropoff.lat, dropoff.lng) if dropoff.lat is not None else None,
        ),
    )

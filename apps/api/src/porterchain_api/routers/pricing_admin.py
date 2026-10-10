"""Admin full-quote simulator — Pricing Center."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from porterchain_pricing.types import PricingRequest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas_pricing import (
    PointInput,
    SimulateQuoteRequest,
    SimulateQuoteResponse,
)

router = APIRouter(prefix="/v1/pricing", tags=["pricing"])

AdminDep = Annotated[AdminContext, Depends(get_admin_context)]
DbDep = Annotated[Session, Depends(get_db)]

_DEFAULT_PICKUP = PointInput(lat=43.65, lng=-79.38, formatted="Toronto, ON", postal="M5V 1A1")
_DEFAULT_DROPOFF = PointInput(lat=43.70, lng=-79.40, formatted="North York, ON", postal="M2N 1A1")


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
    pickup = (body.pickup or _DEFAULT_PICKUP).to_geo()
    dropoff = (body.dropoff or _DEFAULT_DROPOFF).to_geo()
    distance_meters = body.distance_meters
    if not body.use_typed_distance and pickup.lat is not None and dropoff.lat is not None:
        from porterchain_api.services.routing import resolve_route_distance

        routed, _seconds, _source = resolve_route_distance(pickup, dropoff)
        if routed is not None:
            distance_meters = routed
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
    )
    service = get_pricing_service(db)
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
    )

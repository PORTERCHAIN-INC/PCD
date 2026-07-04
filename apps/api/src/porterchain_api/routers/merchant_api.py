"""Programmatic merchant API — /v1/merchant-api/* (API-key auth)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant_api import MerchantApiKeyContext, get_merchant_api_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.routers.merchant import _order_response
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest, MerchantOrderResponse, OrderTrackingResponse

router = APIRouter(prefix="/v1/merchant-api", tags=["merchant-api"])

_booking = MerchantBookingService()
_orders = MerchantOrdersService()
_tracking = MerchantTrackingService()


def _handle_scope(exc: PermissionError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/bookings", response_model=MerchantOrderResponse)
def api_create_booking(
    body: MerchantBookDeliveryRequest,
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        api_ctx.require_scope("shipments:write")
        ctx = api_ctx.to_service_context(db)
        order = _booking.create_shipment(db, settings, ctx, body)
        return _order_response(order)
    except PermissionError as exc:
        _handle_scope(exc)


@router.get("/orders", response_model=list[MerchantOrderResponse])
def api_list_orders(
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    search: str | None = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[MerchantOrderResponse]:
    try:
        api_ctx.require_scope("shipments:read")
        ctx = api_ctx.to_service_context(db)
        orders = _orders.list_orders(db, ctx, state=state, search=search, limit=limit, offset=offset)
        return [_order_response(o) for o in orders]
    except PermissionError as exc:
        _handle_scope(exc)


@router.get("/orders/{order_id}", response_model=MerchantOrderResponse)
def api_get_order(
    order_id: str,
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
) -> MerchantOrderResponse:
    try:
        api_ctx.require_scope("shipments:read")
        ctx = api_ctx.to_service_context(db)
        order = _orders.get_order(db, ctx, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        return _order_response(order)
    except PermissionError as exc:
        _handle_scope(exc)


@router.get("/track/{tracking_number}", response_model=OrderTrackingResponse)
def api_track_by_number(
    tracking_number: str,
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderTrackingResponse:
    try:
        api_ctx.require_scope("shipments:read")
        ctx = api_ctx.to_service_context(db)
        order = _orders.get_by_tracking(db, ctx, tracking_number)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        live = _tracking.track_by_number(db, settings, ctx, tracking_number)
        timeline = live.get("timeline") or live.get("tracking_history") or _orders.get_tracking_timeline(
            db, ctx, order.id
        )
        return OrderTrackingResponse(
            order=_order_response(order),
            timeline=timeline,
            live_tracking=live,
        )
    except PermissionError as exc:
        _handle_scope(exc)


@router.post("/orders/{order_id}/cancel", response_model=MerchantOrderResponse)
def api_cancel_order(
    order_id: str,
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        api_ctx.require_scope("shipments:write")
        ctx = api_ctx.to_service_context(db)
        order = _orders.get_order(db, ctx, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        order = _booking.cancel_order(db, ctx, order, settings)
        return _order_response(order)
    except PermissionError as exc:
        _handle_scope(exc)

"""Programmatic merchant API — /v1/merchant-api/* (API-key auth)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.auth.merchant_api import MerchantApiKeyContext, get_merchant_api_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.states import OrderSource
from porterchain_api.gateway_engine.merchant_api import CHANNEL_ORDER_SOURCES
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.booking_flow_service import MerchantBookingFlowService
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.rate_card_view import merchant_rate_card
from porterchain_api.merchant_engine.service_area import assert_ontario_booking, merchant_coverage_fsas
from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService
from porterchain_api.routers.merchant._deps import _order_response
from porterchain_api.schemas_merchant import (
    MerchantBookDeliveryRequest,
    MerchantBookingPreviewResponse,
    MerchantOrderResponse,
    MerchantRateCardResponse,
    OrderTrackingResponse,
)

router = APIRouter(prefix="/v1/merchant-api", tags=["merchant-api"])

_booking = MerchantBookingService()
_orders = MerchantOrdersService()
_tracking = MerchantTrackingService()
_flow = MerchantBookingFlowService()


def _handle_scope(exc: PermissionError) -> None:
    raise HTTPException(status_code=403, detail=str(exc)) from exc


def _resolve_order_source(channel: str | None) -> str:
    return CHANNEL_ORDER_SOURCES.get((channel or "").strip().lower(), OrderSource.API.value)


@router.post("/bookings", response_model=MerchantOrderResponse)
def api_create_booking(
    body: MerchantBookDeliveryRequest,
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    channel: Annotated[str | None, Header(alias="X-Porterchain-Channel")] = None,
) -> MerchantOrderResponse:
    """
    Create an order from an integration.

    Callers that may retry — Shopify redelivers `orders/create` aggressively —
    should send `Idempotency-Key`. A replay returns the original order instead of
    booking a second van.
    """
    try:
        api_ctx.require_scope("shipments:write")
        ctx = api_ctx.to_service_context(db)

        key = (idempotency_key or "").strip() or None
        sandbox = (api_ctx.api_key.environment or "").lower() == "sandbox"
        if key:
            if len(key) > 128:
                raise HTTPException(status_code=400, detail="idempotency_key_too_long")
            existing = _booking.find_by_idempotency_key(db, ctx, key, is_sandbox=sandbox)
            if existing:
                return _order_response(existing)

        assert_ontario_booking(body, extra_fsas=merchant_coverage_fsas(db, ctx.merchant))

        try:
            order = _booking.create_shipment(
                db,
                settings,
                ctx,
                body,
                order_source=_resolve_order_source(channel),
                idempotency_key=key,
                sandbox=sandbox,
            )
        except IntegrityError:
            # Concurrent replay won the unique index — return the winner's order.
            db.rollback()
            existing = _booking.find_by_idempotency_key(db, ctx, key, is_sandbox=sandbox) if key else None
            if not existing:
                raise
            return _order_response(existing)
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
    except ValueError as exc:
        from porterchain_api.merchant_engine.cancel_policy import cancel_error_message

        raise HTTPException(status_code=400, detail=cancel_error_message(str(exc))) from None


@router.get("/rate-card", response_model=MerchantRateCardResponse)
def api_rate_card(
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
) -> MerchantRateCardResponse:
    try:
        api_ctx.require_scope("shipments:read")
        return MerchantRateCardResponse(**merchant_rate_card(db, api_ctx.merchant))
    except PermissionError as exc:
        _handle_scope(exc)


@router.post("/quotes", response_model=MerchantBookingPreviewResponse)
def api_quote(
    body: MerchantBookDeliveryRequest,
    api_ctx: Annotated[MerchantApiKeyContext, Depends(get_merchant_api_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantBookingPreviewResponse:
    try:
        api_ctx.require_scope("shipments:read")
        ctx = api_ctx.to_service_context(db)
        return MerchantBookingPreviewResponse(**_flow.preview(db, settings, ctx, body))
    except PermissionError as exc:
        _handle_scope(exc)

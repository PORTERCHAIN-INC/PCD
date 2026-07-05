"""merchant routes — orders_tracking."""

from porterchain_api.routers.merchant._deps import *  # noqa: F403

@router.get("/orders/dashboard", response_model=MerchantOrdersDashboardResponse)
def merchant_orders_dashboard(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantOrdersDashboardResponse:
    require_module(ctx, "orders")
    return MerchantOrdersDashboardResponse(**_orders.orders_dashboard(db, ctx))


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    payment_status: str | None = None,
    invoice_status: str | None = None,
    driver_id: str | None = None,
    priority: str | None = None,
    service_type: str | None = None,
    city: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    limit: int = Query(500, le=500),
    offset: int = Query(0, ge=0),
) -> list[OrderListItem]:
    from datetime import datetime

    require_module(ctx, "orders")
    filters = MerchantOrderFilters(
        state=state,
        payment_status=payment_status,
        invoice_status=invoice_status,
        driver_id=driver_id,
        priority=priority,
        service_type=service_type,
        city=city,
        search=search,
        date_from=datetime.fromisoformat(date_from) if date_from else None,
        date_to=datetime.fromisoformat(date_to) if date_to else None,
        amount_min_cents=amount_min_cents,
        amount_max_cents=amount_max_cents,
        limit=limit,
        offset=offset,
    )
    return [OrderListItem(**row) for row in _orders.list_enriched(db, ctx, filters)]


@router.post("/orders/bulk")
def merchant_orders_bulk(
    body: MerchantOrderBulkRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_write")
    results = _orders.bulk_action(db, settings, ctx, body.order_ids, body.action)
    return {"results": results}


@router.get("/orders/{order_id}", response_model=MerchantOrderResponse)
def get_order(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantOrderResponse:
    require_module(ctx, "orders")
    order = _orders.get_order(db, ctx, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    return _order_response(order)


@router.get("/orders/{order_id}/360", response_model=MerchantOrder360Response)
def merchant_order_360(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrder360Response:
    require_module(ctx, "orders")
    try:
        detail = _orders.get_detail_360(db, settings, ctx, order_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None
    return MerchantOrder360Response(**detail)


@router.get("/orders/{order_id}/tracking", response_model=MerchantLiveTrackingResponse)
def merchant_order_tracking(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantLiveTrackingResponse:
    require_module(ctx, "tracking")
    try:
        return MerchantLiveTrackingResponse(**_tracking.live_tracking(db, settings, ctx, order_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/tracking/dashboard", response_model=MerchantTrackingDashboardResponse)
def merchant_tracking_dashboard(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantTrackingDashboardResponse:
    require_module(ctx, "tracking")
    return MerchantTrackingDashboardResponse(**_tracking.dashboard(db, settings, ctx))


@router.get("/tracking/orders/{order_id}", response_model=MerchantLiveTrackingResponse)
def merchant_tracking_detail(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantLiveTrackingResponse:
    require_module(ctx, "tracking")
    try:
        return MerchantLiveTrackingResponse(**_tracking.live_tracking(db, settings, ctx, order_id))
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.get("/track/{tracking_number}", response_model=OrderTrackingResponse)
def track_by_number(
    tracking_number: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderTrackingResponse:
    require_module(ctx, "tracking")
    try:
        live = _tracking.track_by_number(db, settings, ctx, tracking_number)
        order = _orders.get_by_tracking(db, ctx, tracking_number)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        timeline = live.get("timeline") or live.get("tracking_history") or []
        return OrderTrackingResponse(
            order=_order_response(order),
            timeline=timeline,
            live_tracking=live,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="order_not_found") from None


@router.post("/orders/{order_id}/cancel", response_model=MerchantOrderResponse)
def cancel_order(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        require_module(ctx, "orders_write")
        order = _orders.get_order(db, ctx, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        order = _booking.cancel_order(db, ctx, order, settings)
        return _order_response(order)
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/orders/{order_id}/duplicate", response_model=MerchantOrderResponse)
def duplicate_order(
    order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MerchantOrderResponse:
    try:
        require_module(ctx, "orders_write")
        order = _orders.get_order(db, ctx, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="order_not_found")
        new_order = _booking.duplicate_order(db, settings, ctx, order)
        return _order_response(new_order)
    except PermissionError as exc:
        _handle_permission(exc)



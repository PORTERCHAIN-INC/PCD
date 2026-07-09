"""admin routes — orders."""

from datetime import datetime

from porterchain_api.routers.admin._deps import (
    AdminContext,
    AdminOrderFilters,
    Annotated,
    Depends,
    HTTPException,
    OrderBulkRequest,
    OrderDashboardResponse,
    OrderDetail360Response,
    OrderListItem,
    Session,
    Settings,
    _orders,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


@router.get("/orders/dashboard", response_model=OrderDashboardResponse)
def orders_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> OrderDashboardResponse:
    require_module(ctx, "orders_read")
    return OrderDashboardResponse(**_orders.dashboard(db))


@router.get("/orders/reports")
def orders_reports(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "orders_read")
    return _orders.reports(db)


@router.get("/orders", response_model=list[OrderListItem])
def list_orders(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    state: str | None = None,
    payment_status: str | None = None,
    invoice_status: str | None = None,
    merchant_id: str | None = None,
    driver_id: str | None = None,
    priority: str | None = None,
    service_type: str | None = None,
    city: str | None = None,
    search: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    amount_min_cents: int | None = None,
    amount_max_cents: int | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[OrderListItem]:
    require_module(ctx, "orders_read")
    filters = AdminOrderFilters(
        state=state,
        payment_status=payment_status,
        invoice_status=invoice_status,
        merchant_id=merchant_id,
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
    return [OrderListItem(**row) for row in _orders.list_enriched(db, filters)]


@router.post("/orders/bulk")
def orders_bulk(
    body: OrderBulkRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_write")
    results = _orders.bulk_action(
        db,
        settings,
        ctx,
        body.order_ids,
        body.action,
        driver_id=body.driver_id,
    )
    return {"results": results}


@router.get("/orders/{order_id}", response_model=OrderDetail360Response)
def get_order_detail(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderDetail360Response:
    require_module(ctx, "orders_read")
    detail = _orders.get_detail_360(db, settings, order_id)
    if not detail:
        raise HTTPException(status_code=404, detail="order_not_found")
    return OrderDetail360Response(**detail)


@router.get("/orders/{order_id}/tracking")
def get_order_tracking(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    require_module(ctx, "orders_read")
    tracking = _orders.order_tracking(db, settings, order_id)
    if not tracking:
        raise HTTPException(status_code=404, detail="order_not_found")
    return tracking


@router.get("/orders/{order_id}/timeline")
def order_timeline(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "orders_read")
    events = _orders.order_timeline(db, order_id)
    return [
        {
            "event_type": e.event_type,
            "from_state": e.from_state,
            "to_state": e.to_state,
            "occurred_at": e.occurred_at.isoformat(),
            "payload": e.payload,
        }
        for e in events
    ]

"""admin routes — data moat benchmarks (§8.2)."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    HTTPException,
    Session,
    Settings,
    _data_moat,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


@router.get("/data-moat/network")
def data_moat_network(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    window_days: int = 30,
):
    require_module(ctx, "finance")
    return _data_moat.network_benchmarks(db, window_days=window_days)


@router.get("/data-moat/merchants/{merchant_id}")
def data_moat_merchant(
    merchant_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    window_days: int = 30,
):
    require_module(ctx, "finance")
    return _data_moat.merchant_benchmarks(db, merchant_id, window_days=window_days)


@router.get("/data-moat/orders/{order_id}/own-ping-eta")
def data_moat_own_ping_eta(
    order_id: str,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "orders_read")
    payload = _data_moat.own_ping_eta(db, settings, order_id)
    if not payload:
        raise HTTPException(status_code=404, detail="order_not_found")
    return payload

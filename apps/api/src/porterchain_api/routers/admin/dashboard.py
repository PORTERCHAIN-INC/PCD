"""admin routes — dashboard."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    AdminDashboardResponse,
    Annotated,
    AssignDriverRequest,
    Depends,
    HTTPException,
    OrderAdminItem,
    Query,
    Session,
    Settings,
    _dashboard,
    _ops,
    _order_item,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    require_module(ctx, "dashboard")
    return AdminDashboardResponse(**_dashboard.get_dashboard(db))


@router.get("/dashboard/center")
def dashboard_center(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "dashboard")
    return _dashboard.get_center(db, settings, role=ctx.role.value)


@router.get("/dashboard/search")
def dashboard_search(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    q: str = Query(min_length=2),
):
    require_module(ctx, "dashboard")
    return _dashboard.global_search(db, q)


@router.post("/dispatch/orders/{order_id}/assign", response_model=OrderAdminItem)
def assign_driver(
    order_id: str,
    body: AssignDriverRequest,
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderAdminItem:
    require_module(ctx, "dispatch")
    try:
        o = _ops.assign_driver(db, settings, ctx, order_id, body.driver_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _order_item(o)


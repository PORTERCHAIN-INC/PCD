"""admin routes — dashboard."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    AdminDashboardResponse,
    Annotated,
    Depends,
    Query,
    Session,
    Settings,
    _dashboard,
    get_admin_context,
    get_db,
    get_settings,
    require_module,
    router,
)


@router.get("/dashboard", response_model=AdminDashboardResponse, response_model_exclude_none=True)
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


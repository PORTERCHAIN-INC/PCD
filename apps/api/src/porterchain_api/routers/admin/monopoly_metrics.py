"""admin routes — monopoly metrics (§9.2)."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    Session,
    _monopoly_metrics,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/monopoly-metrics")
def monopoly_metrics(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    window_days: int = 30,
):
    require_module(ctx, "dashboard")
    return _monopoly_metrics.snapshot(db, window_days=window_days)

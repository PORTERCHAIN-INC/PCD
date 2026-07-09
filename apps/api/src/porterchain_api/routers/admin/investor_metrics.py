"""admin routes — investor metrics (§10.1)."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    Session,
    _investor_metrics,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/investor-metrics")
def investor_metrics(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "finance")
    return _investor_metrics.snapshot(db)

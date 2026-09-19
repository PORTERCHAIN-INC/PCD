"""admin routes — platform adoption metrics (§7.3)."""

from porterchain_api.routers.admin._deps import (
    AdminContext,
    Annotated,
    Depends,
    Session,
    _platform_metrics,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/platform-metrics")
def admin_platform_metrics(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
):
    """§7.3 — API keys, webhooks, OAuth apps, partner logos, API GMV % vs targets."""
    require_module(ctx, "dashboard")
    return _platform_metrics.snapshot(db)

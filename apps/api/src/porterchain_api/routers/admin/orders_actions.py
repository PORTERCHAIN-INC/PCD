"""admin routes — order draft preview (L128) and return pickup (L105); split from orders (§0.3.9)."""

from porterchain_api.routers.admin._deps import (
    AdminCreateOrderRequest,
    Depends,
    Session,
    Settings,
    _orders,
    get_db,
    get_settings,
    router,
)
from porterchain_api.routers.admin.orders import Ctx, _invoke


@router.post("/orders/preview")
def preview_order(
    body: AdminCreateOrderRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """L128: price the New order draft (same engine as create) without saving anything."""
    from porterchain_api.admin_engine.order_builder_service import OrderBuilderService

    out = _invoke(ctx, "orders_write", OrderBuilderService().create, db, settings, ctx, body, dry_run=True)
    db.rollback()
    return out


@router.post("/orders/{order_id}/return")
def create_order_return(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    """L105: book a return pickup for a delivered order (customer -> merchant)."""
    return _invoke(
        ctx, "orders_write", _orders.create_return_committed, db, settings, order_id,
        actor_id=getattr(ctx.user, "id", None),
    )


@router.post("/orders/{order_id}/repeat")
def repeat_order(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> dict:
    """Clone an order for today at the same locked price (admin Repeat order)."""
    return _invoke(
        ctx,
        "orders_write",
        _orders.create_repeat_committed,
        db,
        settings,
        order_id,
        actor_id=getattr(ctx.user, "id", None),
    )


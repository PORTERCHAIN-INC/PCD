"""Accept or decline an assigned order."""

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    AcceptRejectRequest,
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    Session,
    Settings,
    get_db,
    get_driver_context,
    get_settings,
    require_approved_driver,
    router,
    svc,
)

_NOT_WAITING = "This job is no longer waiting to be accepted."


@router.post("/orders/{order_id}/accept")
def accept_order(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    try:
        with db_transaction(db):
            return svc.platform.availability.accept_assignment(
                db, ctx.driver, order_id, fleetbase_bridge=bridge
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=_NOT_WAITING) from exc


@router.post("/orders/{order_id}/reject")
def reject_order(
    order_id: str,
    body: AcceptRejectRequest,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_approved_driver(ctx)
    bridge = svc.fleetbase_bridge(settings)
    try:
        with db_transaction(db):
            return svc.platform.availability.reject_assignment(
                db,
                ctx.driver,
                order_id,
                reason=body.reason or "",
                fleetbase_bridge=bridge,
            )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=_NOT_WAITING) from exc

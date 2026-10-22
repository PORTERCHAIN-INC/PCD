"""driver routes — delivery leg (start delivery after pickup)."""

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    Session,
    get_db,
    get_driver_context,
    require_approved_driver,
    router,
    stop_response,
    svc)


@router.post("/routes/{route_id}/stops/{stop_id}/start")
def startdelivery_response(
    route_id: str,
    stop_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    """Start the delivery leg (picked up -> out for delivery). Fires receiver tracking."""
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            stop = svc.platform.stops.start_delivery(db, ctx.driver, stop_id)
        return stop_response(stop)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
    svc)

_NOT_WAITING = "This job is no longer waiting to be accepted."


@router.post("/orders/{order_id}/accept")
def accept_order(
    order_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            return svc.platform.availability.accept_assignment(
                db, ctx.driver, order_id
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
    settings: Settings = Depends(get_settings)):
    require_approved_driver(ctx)
    try:
        with db_transaction(db):
            return svc.platform.availability.reject_assignment(
                db,
                ctx.driver,
                order_id,
                reason=body.reason or "")
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="order_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=_NOT_WAITING) from exc


# ---------- Job offers (expire after the fleet TTL, then pass to the next driver) ----------


def _offers_svc():
    from porterchain_api.admin_engine.job_offers_service import JobOffersService

    return JobOffersService()


@router.get("/offers")
def list_offers(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    require_approved_driver(ctx)
    return {"items": _offers_svc().list_for_driver(db, ctx.driver.id)}


def _respond(db: Session, ctx: DriverContext, offer_id: str, accept: bool) -> dict:
    require_approved_driver(ctx)
    try:
        return _offers_svc().respond(db, offer_id, driver_id=ctx.driver.id, accept=accept)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="offer_not_found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/offers/{offer_id}/accept")
def accept_offer(
    offer_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    return _respond(db, ctx, offer_id, True)


@router.post("/offers/{offer_id}/decline")
def decline_offer(
    offer_id: str,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db)):
    return _respond(db, ctx, offer_id, False)

"""Driver side of bulk batches: pickup (count+photo+handover, spot checks), scan advice, grouped delivery,
driver-to-driver handover and leftover return/re-attempt. Same API for driver web and mobile."""
from typing import Any

from porterchain_api.batch_engine import models as _models  # noqa: F401
from porterchain_api.batch_engine import service as svc
from porterchain_api.batch_engine.listing import driver_incoming_handovers, driver_open_routes
from porterchain_api.db import db_transaction
from porterchain_api.media_store.service import require_own_keys
from porterchain_api.routers.driver._deps import (
    Annotated, Depends, DriverContext, HTTPException, Session, get_db, get_driver_context, router,
)

Ctx = Annotated[DriverContext, Depends(get_driver_context)]


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, svc.LegLocked):
        return HTTPException(status_code=423, detail="leg_locked")
    code = 404 if isinstance(exc, LookupError) else 403 if isinstance(exc, PermissionError) else 409
    return HTTPException(status_code=code, detail=str(exc))


def _keys(body: Any, ctx: DriverContext) -> None:
    try:
        require_own_keys(body, str(ctx.driver.id))
    except (ValueError, PermissionError) as exc:
        raise _http(exc) from exc


def _run(db: Session, fn):
    try:
        with db_transaction(db):
            return fn()
    except (ValueError, LookupError, PermissionError, svc.LegLocked) as exc:
        raise _http(exc) from exc


@router.get("/batches/routes")
def my_routes(ctx: Ctx, db: Session = Depends(get_db)):
    return driver_open_routes(db, str(ctx.driver.id))


@router.get("/batches/routes/{route_id}/pickup")
def pickup(route_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    return _run(db, lambda: svc.pickup_view(db, route_id, str(ctx.driver.id)))


@router.post("/batches/routes/{route_id}/pickup/confirm")
def pickup_confirm(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    _keys(body, ctx)
    return _run(db, lambda: svc.confirm_pickup(db, route_id, str(ctx.driver.id), body))


@router.post("/batches/routes/{route_id}/scan")
def scan(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    return _run(db, lambda: svc.scan(db, route_id, str(ctx.driver.id), str(body.get("code") or ""),
                                     phase=body.get("phase", "delivery"), scanned=body.get("scanned")))


@router.get("/batches/routes/{route_id}/stops")
def stops(route_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    return {"stops": _run(db, lambda: svc.delivery_stops(db, route_id, str(ctx.driver.id)))}


@router.post("/batches/routes/{route_id}/deliver")
def deliver(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    _keys(body, ctx)
    return _run(db, lambda: svc.deliver(db, route_id, str(ctx.driver.id), list(body.get("codes") or []), body,
                                        building_key=body.get("building_key")))


@router.post("/batches/routes/{route_id}/close")
def close(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    _keys(body, ctx)
    return _run(db, lambda: svc.close_route(db, route_id, str(ctx.driver.id), dict(body.get("dispositions") or {}), body))


@router.get("/batches/routes/{route_id}/lookup")
def lookup(route_id: str, q: str, ctx: Ctx, db: Session = Depends(get_db)):
    def go():
        r = svc._route(db, route_id, str(ctx.driver.id))
        return {"items": svc.lookup(db, r.batch_id, q)}
    return _run(db, go)


@router.post("/batches/routes/{route_id}/link-label")
def link_label(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    def go():
        r = svc._route(db, route_id, str(ctx.driver.id))
        p = svc.link_label(db, r.batch_id, str(body.get("parcel_id")), str(body.get("code") or ""))
        return {"parcel_id": p.id, "client_labels": p.client_labels}
    return _run(db, go)


@router.post("/batches/routes/{route_id}/handovers")
def handover(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    _keys(body, ctx)
    def go():
        h = svc.start_handover(db, route_id, str(ctx.driver.id), str(body.get("to_driver_id") or ""),
                               list(body.get("codes") or []), body)
        return {"handover_id": h.id, "status": h.status, "parcels": len(h.parcel_ids)}
    return _run(db, go)


@router.get("/batches/handovers/incoming")
def incoming(ctx: Ctx, db: Session = Depends(get_db)):
    return driver_incoming_handovers(db, str(ctx.driver.id))


@router.post("/batches/handovers/{handover_id}/accept")
def accept(handover_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    _keys(body, ctx)
    return _run(db, lambda: svc.accept_handover(db, handover_id, str(ctx.driver.id), body))


@router.get("/batches/routes/{route_id}")
def summary(route_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    return _run(db, lambda: svc.route_summary(db, route_id, str(ctx.driver.id)))


@router.post("/batches/routes/{route_id}/pickup/fail")
def pickup_fail(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    _keys(body, ctx)
    return _run(db, lambda: svc.fail_pickup(db, route_id, str(ctx.driver.id), str(body.get("reason") or "")))


@router.post("/batches/routes/{route_id}/reoptimise")
def reoptimise(route_id: str, body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)):
    return _run(db, lambda: svc.live_reoptimise(db, route_id, str(ctx.driver.id), body))

"""Doc 80 driver routes: vehicle record per trip, DVIR, phone HOS log."""

from typing import Any

from porterchain_api.compliance_engine import models as _models  # noqa: F401  (register tables)
from porterchain_api.compliance_engine import service as comp
from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    Annotated,
    Depends,
    DriverContext,
    HTTPException,
    Session,
    get_db,
    get_driver_context,
    router,
)


def _err(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=422, detail=str(exc))


@router.post("/compliance/trips")
def create_trip(body: dict[str, Any], ctx: Annotated[DriverContext, Depends(get_driver_context)],
                db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            return comp.trip_out(comp.create_trip(db, str(ctx.driver.id), body))
    except ValueError as exc:
        raise _err(exc) from exc


@router.post("/compliance/trips/{trip_id}/start")
def start_trip(trip_id: str, ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            return comp.trip_out(comp.start_trip(db, str(ctx.driver.id), trip_id))
    except (ValueError, LookupError) as exc:
        raise _err(exc) from exc


@router.post("/compliance/dvir")
def submit_dvir(body: dict[str, Any], ctx: Annotated[DriverContext, Depends(get_driver_context)],
                db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            return comp.dvir_out(comp.submit_dvir(db, str(ctx.driver.id), body))
    except ValueError as exc:
        raise _err(exc) from exc


@router.post("/compliance/hos/events")
def hos_event(body: dict[str, Any], ctx: Annotated[DriverContext, Depends(get_driver_context)],
              db: Session = Depends(get_db)):
    try:
        with db_transaction(db):
            comp.record_hos(db, str(ctx.driver.id), body)
        return comp.hos_today(db, str(ctx.driver.id))
    except ValueError as exc:
        raise _err(exc) from exc


@router.get("/compliance/hos/today")
def hos_today(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)):
    return comp.hos_today(db, str(ctx.driver.id))

"""driver routes — timesheets and weekly availability schedule."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.db import db_transaction, get_db
from porterchain_api.routers.driver._deps import DriverContext, get_driver_context, router
from porterchain_driver import timesheets as ts


@router.get("/timesheets")
def get_timesheets(
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
    weeks: int = Query(4, ge=1, le=ts.MAX_WEEKS),
):
    return ts.load_timesheet(db, ctx.driver.id, weeks=weeks)


@router.get("/availability/schedule")
def get_schedule(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    schedule = ts.read_schedule(ctx.driver)
    return {"schedule": schedule, "weekly_hours": ts.weekly_hours(schedule), "timezone": "America/Toronto"}


@router.put("/availability/schedule")
def put_schedule(
    body: dict,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    raw = body.get("schedule") if isinstance(body.get("schedule"), dict) else body
    try:
        with db_transaction(db):
            schedule = ts.save_schedule(db, ctx.driver, raw)
    except ts.ScheduleError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "code": exc.code}) from exc
    return {"schedule": schedule, "weekly_hours": ts.weekly_hours(schedule), "timezone": "America/Toronto"}

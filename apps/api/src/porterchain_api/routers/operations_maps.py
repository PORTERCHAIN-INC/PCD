"""Self-hosted map routes on the operations router (kept out of operations.py's LOC cap)."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from porterchain_api.db import get_db
from porterchain_api.routers.operations import Ctx, _invoke, router


@router.get("/drivers/{driver_id}/track")
def driver_track(driver_id: str, ctx: Ctx, db: Session = Depends(get_db), minutes: int = 60) -> dict:
    """Map-matched breadcrumb trail (Valhalla trace_route → OSRM match → raw)."""
    from porterchain_api.admin_engine.maps_extras import driver_track as _track

    return _invoke(ctx, "dispatch_read", _track, db, driver_id, minutes)


@router.get("/service-area")
def service_area(ctx: Ctx, minutes: str = "30,60,90") -> dict:
    """Drive-time isochrone rings from the Milton hub (Valhalla), cached 24 h."""
    from porterchain_api.admin_engine.maps_extras import service_area as _area

    mins = [int(m) for m in minutes.split(",") if m.strip().isdigit()]
    return _invoke(ctx, "dispatch_read", _area, mins)

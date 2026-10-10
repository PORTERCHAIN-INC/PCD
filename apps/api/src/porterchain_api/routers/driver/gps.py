"""Driver location-sharing status and consent (PIPEDA)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from porterchain_api.db import db_transaction
from porterchain_api.routers.driver._deps import (
    DriverContext,
    get_db,
    get_driver_context,
    router,
)


@router.get("/gps-status")
def gps_status(ctx: Annotated[DriverContext, Depends(get_driver_context)], db: Session = Depends(get_db)) -> dict:
    """Is live location sharing on for me? Plain-language message for the driver."""
    from porterchain_api.platform.gps_policy import driver_gps_status

    return driver_gps_status(str(ctx.driver.id), db, ctx.driver)


@router.post("/gps-consent")
def gps_consent(
    body: dict,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
) -> dict:
    """Driver accepts (or withdraws) location-sharing consent; timestamped on the driver record."""
    from porterchain_api.platform.gps_policy import driver_gps_status, forget_positions, record_consent

    accepted = bool(body.get("accepted"))
    with db_transaction(db):
        record_consent(ctx.driver, accepted=accepted, source=str(body.get("source") or "app")[:16])
    if not accepted:
        forget_positions([str(ctx.driver.id)])
    return driver_gps_status(str(ctx.driver.id), db, ctx.driver)

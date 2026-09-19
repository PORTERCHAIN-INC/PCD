"""Local/dev-only driver email login (CLERK_DEV_BYPASS). Real path remains Clerk invite."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.driver_engine.auth_service import DriverAuthService
from porterchain_api.routers.driver._deps import router
from porterchain_api.schemas_driver import (
    DriverDevListItem,
    DriverDevLoginRequest,
    DriverDevLoginResponse,
)

_auth = DriverAuthService()


@router.post("/auth/dev-login", response_model=DriverDevLoginResponse)
def driver_dev_login(
    body: DriverDevLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DriverDevLoginResponse:
    """Email → approved driver id. Only when CLERK_DEV_BYPASS is enabled (local)."""
    if not allow_auth_dev_bypass(settings):
        raise HTTPException(status_code=404, detail="not_found")
    payload = _auth.approved_dev_login(db, body.email)
    if not payload:
        raise HTTPException(status_code=404, detail="driver_not_found")
    return DriverDevLoginResponse(**payload)


@router.get("/auth/dev-drivers", response_model=list[DriverDevListItem])
def driver_dev_list(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    limit: int = Query(50, ge=1, le=100),
) -> list[DriverDevListItem]:
    """List approved drivers for the local email picker."""
    if not allow_auth_dev_bypass(settings):
        raise HTTPException(status_code=404, detail="not_found")
    return [DriverDevListItem(**row) for row in _auth.list_approved_dev_drivers(db, limit=limit)]

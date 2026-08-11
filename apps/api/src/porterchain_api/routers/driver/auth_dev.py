"""Local/dev-only driver email login (CLERK_DEV_BYPASS). Real path remains Clerk invite."""

from __future__ import annotations

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.routers.driver._deps import router


class DriverDevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class DriverDevLoginResponse(BaseModel):
    driver_id: str
    email: str
    full_name: str
    status: str


class DriverDevListItem(BaseModel):
    driver_id: str
    email: str
    full_name: str


@router.post("/auth/dev-login", response_model=DriverDevLoginResponse)
def driver_dev_login(
    body: DriverDevLoginRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> DriverDevLoginResponse:
    """Email → approved driver id. Only when CLERK_DEV_BYPASS is enabled (local)."""
    if not allow_auth_dev_bypass(settings):
        raise HTTPException(status_code=404, detail="not_found")

    email = body.email.lower().strip()
    driver = (
        db.query(Driver)
        .filter(Driver.email == email, Driver.status == DriverStatus.APPROVED.value)
        .first()
    )
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    return DriverDevLoginResponse(
        driver_id=driver.id,
        email=driver.email,
        full_name=driver.full_name,
        status=driver.status,
    )


@router.get("/auth/dev-drivers", response_model=list[DriverDevListItem])
def driver_dev_list(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[DriverDevListItem]:
    """List approved drivers for the local email picker."""
    if not allow_auth_dev_bypass(settings):
        raise HTTPException(status_code=404, detail="not_found")
    rows = (
        db.query(Driver)
        .filter(Driver.status == DriverStatus.APPROVED.value)
        .order_by(Driver.full_name.asc())
        .limit(50)
        .all()
    )
    return [
        DriverDevListItem(driver_id=d.id, email=d.email, full_name=d.full_name) for d in rows
    ]

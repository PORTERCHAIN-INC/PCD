"""Resolve driver context from Porterchain JWT or dev headers."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.rbac import DriverContext

_bearer = HTTPBearer(auto_error=False)


def get_driver_context(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_driver_id: Annotated[str | None, Header()] = None,
) -> DriverContext:
    driver_id: str | None = None

    if credentials and credentials.credentials:
        driver_id = _driver_id_from_token(credentials.credentials, settings)
    elif settings.clerk_dev_bypass and x_driver_id:
        driver_id = x_driver_id
    elif settings.clerk_dev_bypass:
        driver = db.query(Driver).filter(Driver.status == DriverStatus.APPROVED.value).first()
        if driver:
            return DriverContext(driver=driver)

    if not driver_id:
        raise HTTPException(status_code=401, detail="driver_auth_required")

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    if driver.status == DriverStatus.SUSPENDED.value:
        raise HTTPException(status_code=403, detail="driver_suspended")
    return DriverContext(driver=driver)


def _driver_id_from_token(token: str, settings: Settings) -> str:
    from porterchain_driver.auth_tokens import decode_driver_token

    try:
        payload = decode_driver_token(token, secret=settings.jwt_secret, token_type="access")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid_driver_token") from exc
    return str(payload["driver_id"])

"""Resolve driver context from Clerk bearer (or local X-Driver-Id bypass)."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.auth.dev import allow_auth_dev_bypass, resolve_dev_bypass_driver
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.rbac import DriverContext

_bearer = HTTPBearer(auto_error=False)


async def get_driver_context(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_driver_id: Annotated[str | None, Header()] = None,
) -> DriverContext:
    driver_id: str | None = None

    token = credentials.credentials if credentials and credentials.credentials else None
    if token == "dev" and allow_auth_dev_bypass(settings):
        driver = resolve_dev_bypass_driver(db)
        if driver:
            return DriverContext(driver=driver)
    elif token:
        from porterchain_api.auth.impersonation_session import (
            IMP_BEARER_PREFIX,
            resolve_from_bearer,
        )

        if token.startswith(IMP_BEARER_PREFIX):
            session = resolve_from_bearer(token)
            if not session or session.target_type != "driver":
                raise HTTPException(status_code=401, detail="impersonation_expired")
            driver = db.query(Driver).filter(Driver.id == session.target_id).first()
            if not driver:
                raise HTTPException(status_code=404, detail="driver_not_found")
            if driver.status == DriverStatus.SUSPENDED.value:
                raise HTTPException(status_code=403, detail="driver_suspended")
            return DriverContext(driver=driver)
        driver_id = await _clerk_driver_id(db, token, settings)
    elif allow_auth_dev_bypass(settings) and x_driver_id:
        driver_id = x_driver_id
    elif allow_auth_dev_bypass(settings):
        driver = resolve_dev_bypass_driver(db)
        if driver:
            _assert_driver_self_scope(db, driver)
            return DriverContext(driver=driver)

    if not driver_id:
        raise HTTPException(status_code=401, detail="driver_auth_required")

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="driver_not_found")
    if driver.status == DriverStatus.SUSPENDED.value:
        raise HTTPException(status_code=403, detail="driver_suspended")
    _assert_driver_self_scope(db, driver)
    return DriverContext(driver=driver)


def _assert_driver_self_scope(db: Session, driver: Driver) -> None:
    """When self-scoped driver assignments exist, driver.id must match."""
    from porterchain_api.auth.claims import ClerkClaims
    from porterchain_api.auth.dependencies import (
        assert_self_scope,
        resolve_principal_for_claims,
    )

    if not driver.clerk_user_id:
        return
    principal = resolve_principal_for_claims(
        db,
        ClerkClaims(clerk_user_id=driver.clerk_user_id, email=driver.email),
    )
    if not principal:
        raise HTTPException(status_code=403, detail="user_not_provisioned")
    assert_self_scope(principal, driver.id, db)


async def _clerk_driver_id(db: Session, token: str, settings: Settings) -> str:
    from porterchain_api.auth.clerk import verify_clerk_token
    from porterchain_api.auth.persona_bundle import load_persona_bundle
    from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive
    from porterchain_api.auth.prepare import prepare_user_from_claims

    try:
        claims = await verify_clerk_token(token, settings)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid_driver_token") from exc

    # Align with other portals: prepare (UserSync + SpiceDB) once, then exclusive check.
    prepare_user_from_claims(db, claims)
    assert_clerk_id_exclusive(db, claims, portal="driver", settings=settings)
    driver = load_persona_bundle(db, claims.clerk_user_id).driver
    if not driver:
        raise HTTPException(status_code=403, detail="driver_not_found")
    from porterchain_api.auth.email_identity import (
        CLERK_EMAIL_REQUIRED,
        CLERK_EMAIL_UNVERIFIED,
        EMAIL_CLERK_MISMATCH,
        assert_portal_email_identity,
    )

    try:
        assert_portal_email_identity(driver.email, claims.email)
    except PermissionError as exc:
        detail = str(exc)
        if detail in {CLERK_EMAIL_REQUIRED, CLERK_EMAIL_UNVERIFIED, EMAIL_CLERK_MISMATCH}:
            raise HTTPException(status_code=403, detail=detail) from exc
        raise HTTPException(status_code=403, detail=EMAIL_CLERK_MISMATCH) from exc
    return driver.id


def _driver_id_from_token(token: str, settings: Settings) -> str:
    """Legacy sync helper for audit / notification callers (old driver JWT only).

    Portal BFF uses Clerk bearer via get_driver_context. Cookie JWT minting is retired.
    """
    from porterchain_driver.auth_tokens import decode_driver_token

    try:
        payload = decode_driver_token(token, secret=settings.jwt_secret, token_type="access")
        return str(payload["driver_id"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid_driver_token") from exc

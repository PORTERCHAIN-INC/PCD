"""driver routes — personal profile (GET/PATCH /me/profile, POST /me/profile/sync-identity)."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import db_transaction, get_db
from porterchain_api.routers.driver._deps import DriverContext, get_driver_context, router
from porterchain_driver import personal_profile as pp

_bearer = HTTPBearer(auto_error=False)


@router.get("/me/profile")
def get_my_profile(ctx: Annotated[DriverContext, Depends(get_driver_context)]):
    return pp.read_profile(ctx.driver)


@router.patch("/me/profile")
def patch_my_profile(
    body: dict,
    ctx: Annotated[DriverContext, Depends(get_driver_context)],
    db: Session = Depends(get_db),
):
    try:
        with db_transaction(db):
            profile, changed = pp.update_profile(db, ctx.driver, body)
            if changed:
                pp.audit_self_change(db, ctx.driver.id, "driver.profile.update", changed)
    except pp.ProfileValidationError as exc:
        raise HTTPException(status_code=422, detail={"field": exc.field, "code": exc.code}) from exc
    return {"profile": profile, "changed": changed}


@router.post("/me/profile/sync-identity")
async def sync_my_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """After a verified email/phone change in Clerk, copy the new primary values to the driver.

    Uses its own auth (signature-verified Clerk token -> driver by clerk_user_id) because the
    normal driver gate rejects a session whose Clerk email no longer matches the driver row,
    which is exactly the state right after a verified email change.
    """
    from porterchain_api.auth import email_identity
    from porterchain_api.auth.clerk import verify_clerk_token
    from porterchain_api.auth.clerk_registry import fetch_clerk_user

    token = credentials.credentials if credentials else None
    if not token or token == "dev":
        raise HTTPException(status_code=401, detail="driver_auth_required")
    try:
        claims = await verify_clerk_token(token, settings)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid_driver_token") from exc
    driver = pp.driver_for_clerk_user(db, claims.clerk_user_id)
    if not driver:
        raise HTTPException(status_code=403, detail="driver_not_found")
    clerk_user, _ = fetch_clerk_user(settings, claims.clerk_user_id)
    if not clerk_user:
        raise HTTPException(status_code=502, detail="identity_lookup_failed")
    email, _detail = email_identity.verified_primary_email_from_clerk_user(clerk_user)
    phone = pp.verified_primary_phone(clerk_user)
    email_identity._email_cache.pop(claims.clerk_user_id, None)
    with db_transaction(db):
        changed = pp.sync_identity(db, driver, email=email, phone=phone)
        if changed:
            pp.audit_self_change(db, driver.id, "driver.identity.sync", changed)
    return {"profile": pp.read_profile(driver), "changed": changed}

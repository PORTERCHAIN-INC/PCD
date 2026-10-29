"""Admin portal auth — Keycloak ``pc-admin`` access tokens (MFA enforced in the realm flow).

Replaces the separate Staff IdP login. The bearer must be a Keycloak token whose ``azp`` is
``pc-admin``; the staff row is matched by verified email. RBAC stays on ``AdminUser.role`` +
SpiceDB ``platform#portal``. Step-up = a Keycloak login no older than 15 minutes
(``auth_time``) — the admin UI re-authenticates with ``prompt=login``.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims as IdentityClaims
from porterchain_api.config import Settings

ADMIN_CLIENT_ID = "pc-admin"
STEP_UP_MAX_AGE_SECONDS = 15 * 60


def looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2 and not token.startswith(("staff_sess_", "pc_imp_", "imp_"))


async def admin_claims_from_bearer(token: str, settings: Settings) -> IdentityClaims:
    from porterchain_api.auth.keycloak import verify_keycloak_token

    claims = await verify_keycloak_token(token, settings)
    if claims.authorized_party != ADMIN_CLIENT_ID:
        raise HTTPException(status_code=401, detail="admin_token_wrong_client")
    if not claims.email:
        raise HTTPException(status_code=403, detail="admin_email_unverified")
    return claims


def admin_user_for_claims(db: Session, claims: IdentityClaims) -> Any:
    from porterchain_api.admin_engine.staff_lookups import get_admin_by_email

    user = get_admin_by_email(db, claims.email or "")
    if not user:
        raise HTTPException(status_code=403, detail="admin_user_not_found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="admin_user_inactive")
    return user


def assert_recent_login(claims: IdentityClaims | None, *, now: float | None = None) -> None:
    if claims is None or not claims.auth_time:
        raise PermissionError("staff_step_up_required")
    age = (now if now is not None else time.time()) - float(claims.auth_time)
    if age < -60 or age > STEP_UP_MAX_AGE_SECONDS:
        raise PermissionError("staff_step_up_required")

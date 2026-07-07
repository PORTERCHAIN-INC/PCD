"""Driver authentication — Clerk-verified login (masterrule §3, §15)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import verify_clerk_token
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive, require_clerk_app_for_portal
from porterchain_api.auth.user_sync_service import UserSyncService, _is_pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_driver.auth_tokens import SessionTokens, issue_driver_session


class DriverAuthService:
    async def login(
        self,
        db: Session,
        settings: Settings,
        *,
        email: str,
        clerk_bearer_token: str | None = None,
    ) -> tuple[Driver, SessionTokens]:
        driver = db.query(Driver).filter(Driver.email == email).first()
        if not driver:
            raise LookupError("driver_not_found")
        if driver.status not in (DriverStatus.APPROVED.value, DriverStatus.PENDING.value):
            raise PermissionError("driver_not_active")

        allow_email_only = allow_auth_dev_bypass(settings)
        claims: ClerkClaims
        if not allow_email_only:
            if not clerk_bearer_token:
                raise PermissionError("clerk_token_required")
            claims = await verify_clerk_token(clerk_bearer_token, settings)
            require_clerk_app_for_portal(claims, settings, "driver")
            assert_clerk_id_exclusive(db, claims, portal="driver", settings=settings)
            if driver.clerk_user_id and driver.clerk_user_id != claims.clerk_user_id:
                raise PermissionError("driver_clerk_mismatch")
            if _is_pending_clerk_id(driver.clerk_user_id):
                driver.clerk_user_id = claims.clerk_user_id
                db.commit()
                db.refresh(driver)
            if claims.email and claims.email.lower() != email.lower():
                raise PermissionError("email_clerk_mismatch")
        else:
            claims = ClerkClaims(
                clerk_user_id=driver.clerk_user_id or "dev_clerk_user",
                email=email,
                phone=driver.phone,
            )

        UserSyncService().sync(db, claims)

        tokens = issue_driver_session(driver.id, secret=settings.jwt_secret, email=driver.email)
        return driver, tokens

    def refresh(
        self,
        db: Session,
        settings: Settings,
        *,
        refresh_token: str,
    ) -> tuple[Driver, SessionTokens]:
        from porterchain_driver.auth_tokens import decode_driver_token

        try:
            payload = decode_driver_token(refresh_token, secret=settings.jwt_secret, token_type="refresh")
        except Exception as exc:
            raise PermissionError("invalid_refresh_token") from exc

        driver = db.query(Driver).filter(Driver.id == payload.get("driver_id")).first()
        if not driver:
            raise LookupError("driver_not_found")
        if driver.status not in (DriverStatus.APPROVED.value, DriverStatus.PENDING.value):
            raise PermissionError("driver_not_active")

        tokens = issue_driver_session(driver.id, secret=settings.jwt_secret, email=driver.email)
        return driver, tokens

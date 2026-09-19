"""Driver authentication — Clerk session only (no Porterchain cookie JWT)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk import verify_clerk_token
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.driver_identity import bind_clerk_user_id
from porterchain_api.auth.email_identity import assert_portal_email_identity
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive
from porterchain_api.auth.prepare import prepare_user_from_claims, resolve_principal_cached
from porterchain_api.auth.user_sync_service import _is_pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.platform.driver_reads import (
    get_approved_driver_by_email,
    get_driver_by_email,
    list_approved_drivers,
)


class DriverAuthService:
    async def link_clerk(
        self,
        db: Session,
        settings: Settings,
        *,
        email: str,
        clerk_bearer_token: str | None = None,
    ) -> Any:
        """Verify Clerk + sync identity. Does not mint Porterchain JWTs."""
        driver = get_driver_by_email(db, email)
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
            assert_clerk_id_exclusive(db, claims, portal="driver", settings=settings)
            if driver.clerk_user_id and driver.clerk_user_id != claims.clerk_user_id:
                raise PermissionError("driver_clerk_mismatch")
            if _is_pending_clerk_id(driver.clerk_user_id):
                bind_clerk_user_id(db, driver, claims.clerk_user_id)
            assert_portal_email_identity(email, claims.email)
        else:
            claims = ClerkClaims(
                clerk_user_id=driver.clerk_user_id or "dev_clerk_user",
                email=email,
                phone=driver.phone,
            )

        prepare_user_from_claims(db, claims)

        if claims.clerk_user_id and claims.clerk_user_id != "dev_clerk_user":
            from porterchain_api.auth.identity import AuthenticatedIdentity
            from porterchain_api.auth.unified_catalog import UnifiedPermission

            try:
                principal = resolve_principal_cached(
                    db,
                    AuthenticatedIdentity(
                        provider="clerk",
                        subject=claims.clerk_user_id,
                        email=claims.email,
                        email_verified=True,
                        session_id=claims.session_id,
                        issuer=claims.issuer,
                    ),
                )
            except Exception as exc:
                raise PermissionError("driver_not_provisioned") from exc
            if not principal.has_permission(UnifiedPermission.DRIVER_PORTAL_ACCESS):
                raise PermissionError("driver_portal_access_denied")
            if principal.role_assignments and not principal.has_self_scope(driver.id):
                if any(a.scope_type == "self" for a in principal.role_assignments):
                    raise PermissionError("self_scope_denied")

        return driver


    def approved_dev_login(self, db: Session, email: str) -> dict | None:
        driver = get_approved_driver_by_email(db, email.lower().strip())
        if not driver:
            return None
        return {
            "driver_id": driver.id,
            "email": driver.email,
            "full_name": driver.full_name,
            "status": driver.status,
        }

    def list_approved_dev_drivers(self, db: Session, *, limit: int) -> list[dict]:
        return [
            {"driver_id": d.id, "email": d.email, "full_name": d.full_name}
            for d in list_approved_drivers(db, limit=limit)
        ]

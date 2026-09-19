"""SSO — Porterchain JWT for Fleetbase trust (Clerk or staff IdP)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_engine.staff_lookups import get_admin_user
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.fleetbase_roles import (
    can_access_fleetbase_console,
    fleetbase_permissions_for_admin,
)
from porterchain_api.auth.identity_links import (
    require_porterchain_user_id,
    stamp_fleetbase_user_uuid,
    upsert_sso_link,
)
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.auth.persona_principal import resolve_persona_principal
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import PlatformRole
from porterchain_shared.types.user_types import UserType

logger = logging.getLogger(__name__)

SSO_AUDIENCE_FLEETBASE = "fleetbase"
SSO_ISSUER = "porterchain"

_ADMIN_PLATFORM: dict[AdminRole, PlatformRole] = {
    AdminRole.SUPER_ADMIN: PlatformRole.SUPER_ADMIN,
    AdminRole.ADMIN: PlatformRole.ADMIN,
    AdminRole.DISPATCHER: PlatformRole.DISPATCHER,
    AdminRole.SUPPORT: PlatformRole.SUPPORT,
    AdminRole.SUPPORT_LEAD: PlatformRole.SUPPORT,
    AdminRole.FINANCE: PlatformRole.FINANCE,
    AdminRole.FLEET_MANAGER: PlatformRole.OPERATIONS,
    AdminRole.SALES: PlatformRole.OPERATIONS,
    AdminRole.SALES_MANAGER: PlatformRole.OPERATIONS,
    AdminRole.MARKETING: PlatformRole.OPERATIONS,
    AdminRole.COMPLIANCE: PlatformRole.OPERATIONS,
    AdminRole.DEVELOPER: PlatformRole.OPERATIONS,
    AdminRole.READ_ONLY: PlatformRole.OPERATIONS,
}


class SsoService:
    def resolve_principal(
        self, db: Session, claims: ClerkClaims, settings: Settings | None = None
    ) -> AuthPrincipal | None:
        """Legacy Clerk path — prefer ``auth_principal_from_current`` for staff IdP."""
        return resolve_persona_principal(db, claims, settings=settings)

    def auth_principal_from_current(
        self, db: Session, current: CurrentPrincipal
    ) -> AuthPrincipal | None:
        """Build Fleetbase AuthPrincipal from session CurrentPrincipal (staff or Clerk)."""
        admin_id = current.legacy_profile_ids.get("admin_user_id")
        admin = get_admin_user(db, admin_id) if admin_id else None
        if not admin and current.auth_subject:
            bundle = load_persona_bundle(db, current.auth_subject)
            admin = bundle.admin
        if not admin or not admin.is_active:
            return None

        admin_role = parse_admin_role(admin.role)
        if admin_role == AdminRole.DISPATCHER:
            user_type = UserType.DISPATCHER
        elif admin_role in (AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD):
            user_type = UserType.SUPPORT
        else:
            user_type = UserType.ADMIN

        return AuthPrincipal(
            user_id=admin.id,
            user_type=user_type,
            roles=frozenset({_ADMIN_PLATFORM.get(admin_role, PlatformRole.ADMIN)}),
            org_id=None,
            email=admin.email or current.email,
            session_id=current.session_id,
        )

    def issue_sso_token(
        self,
        settings: Settings,
        principal: AuthPrincipal,
        *,
        audience: str,
        subject: str,
    ) -> str:
        secret = settings.sso_jwt_secret or settings.jwt_secret
        if not secret:
            raise ValueError("sso_jwt_secret_not_configured")

        now = datetime.now(UTC)
        payload = {
            "iss": SSO_ISSUER,
            "aud": audience,
            "sub": principal.user_id,
            "clerk_user_id": subject,  # IdP subject (staff:{id} or Clerk user_*)
            "auth_subject": subject,
            "user_type": principal.user_type.value,
            "org_id": principal.org_id,
            "email": principal.email,
            "roles": sorted(r.value for r in principal.roles),
            "permissions": sorted(p.value for p in principal.permissions()),
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=settings.sso_token_ttl_seconds)).timestamp()),
        }
        return jwt.encode(payload, secret, algorithm="HS256")

    def _upsert_identity_link(
        self,
        db: Session,
        *,
        subject: str,
        email: str | None,
        principal: AuthPrincipal,
        provider: str,
        issuer: str | None,
        porterchain_user_id: str | None,
    ):
        pc_id = require_porterchain_user_id(db, subject, porterchain_user_id)

        fleetbase_perms: list[str] | None = None
        fleetbase_roles: list[str] | None = None
        if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
            admin = get_admin_user(db, principal.user_id)
            if admin:
                admin_role = parse_admin_role(admin.role)
                fleetbase_perms = fleetbase_permissions_for_admin(admin_role)
                fleetbase_roles = [admin.role]

        return upsert_sso_link(
            db,
            subject=subject,
            email=email or principal.email,
            user_type=principal.user_type.value,
            platform_user_id=pc_id,
            platform_org_id=principal.org_id,
            provider=provider,
            issuer=issuer,
            fleetbase_permissions=fleetbase_perms,
            fleetbase_roles=fleetbase_roles,
        )

    def exchange_fleetbase_session_for_principal(
        self,
        db: Session,
        settings: Settings,
        current: CurrentPrincipal,
    ) -> dict:
        """Issue Porterchain SSO JWT from staff IdP or Clerk session context."""
        if not settings.fleetbase_sso_enabled:
            raise ValueError("fleetbase_sso_disabled")
        principal = self.auth_principal_from_current(db, current)
        if not principal:
            raise PermissionError("fleetbase_console_forbidden")
        if principal.user_type not in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
            raise PermissionError("fleetbase_console_forbidden")

        admin = get_admin_user(db, principal.user_id)
        if admin:
            admin_role = parse_admin_role(admin.role)
            if not can_access_fleetbase_console(admin_role):
                raise PermissionError("fleetbase_console_forbidden")

        subject = (
            current.auth_subject
            or (admin.clerk_user_id if admin else None)
            or f"staff:{principal.user_id}"
        )
        link = self._upsert_identity_link(
            db,
            subject=subject,
            email=current.email or principal.email,
            principal=principal,
            provider=current.auth_provider or "staff_idp",
            issuer=current.auth_issuer,
            porterchain_user_id=current.user_id,
        )
        sso_token = self.issue_sso_token(
            settings, principal, audience=SSO_AUDIENCE_FLEETBASE, subject=subject
        )

        fleetbase_session: dict | None = None
        try:
            from porterchain_fleetbase_adapter.auth import FleetbaseSsoClient
            from porterchain_fleetbase_adapter.config import FleetbaseSettings

            fb = FleetbaseSsoClient(
                FleetbaseSettings(
                    api_url=settings.fleetbase_api_url,
                    api_key=settings.fleetbase_api_key,
                    company_uuid=settings.fleetbase_default_company_uuid,
                    dispatch_bridge=settings.fleetbase_dispatch_bridge,
                    webhook_secret=settings.fleetbase_webhook_secret,
                ),
                sso_jwt_secret=settings.sso_jwt_secret or settings.jwt_secret,
            )
            fleetbase_session = fb.exchange_sso_token(
                sso_token,
                email=current.email or principal.email,
                clerk_user_id=subject,
                fleetbase_permissions=link.fleetbase_permissions or [],
                fleetbase_roles=link.fleetbase_roles or [],
            )
            if fleetbase_session and fleetbase_session.get("fleetbase_user_uuid"):
                stamp_fleetbase_user_uuid(link, fleetbase_session["fleetbase_user_uuid"])
                if admin and fleetbase_session.get("fleetbase_user_uuid"):
                    admin.fleetbase_user_uuid = fleetbase_session["fleetbase_user_uuid"]
                db.commit()
        except Exception as exc:
            logger.warning("Fleetbase SSO exchange unavailable: %s", exc)

        console_base = (settings.fleetbase_console_url or "").strip().rstrip("/")
        console_url = f"{console_base}/porterchain/sso?token={sso_token}" if console_base else ""

        return {
            "sso_token": sso_token,
            "expires_in": settings.sso_token_ttl_seconds,
            "console_url": console_url,
            "fleetbase_user_uuid": link.fleetbase_user_uuid,
            "fleetbase_session": fleetbase_session,
            "permissions": sorted(p.value for p in principal.permissions()),
            "roles": sorted(r.value for r in principal.roles),
        }

    def session_payload(self, principal: AuthPrincipal) -> dict:
        return {
            "user_id": principal.user_id,
            "user_type": principal.user_type.value,
            "roles": sorted(r.value for r in principal.roles),
            "permissions": sorted(p.value for p in principal.permissions()),
            "org_id": principal.org_id,
            "email": principal.email,
        }

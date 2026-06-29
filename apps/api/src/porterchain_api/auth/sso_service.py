"""SSO — Clerk once, Porterchain JWT, Fleetbase trust."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.fleetbase_roles import (
    can_access_fleetbase_console,
    fleetbase_permissions_for_admin,
)
from porterchain_api.auth.principal_resolver import PrincipalResolver
from porterchain_api.config import Settings
from porterchain_api.identity_models import IdentityLink
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import Permission
from porterchain_shared.types.user_types import UserType

logger = logging.getLogger(__name__)

SSO_AUDIENCE_FLEETBASE = "fleetbase"
SSO_ISSUER = "porterchain"


class SsoService:
    def __init__(self) -> None:
        self._resolver = PrincipalResolver()

    def resolve_principal(self, db: Session, claims: ClerkClaims) -> AuthPrincipal | None:
        return self._resolver.resolve(db, claims)

    def issue_sso_token(
        self,
        settings: Settings,
        principal: AuthPrincipal,
        *,
        audience: str,
        clerk_user_id: str,
    ) -> str:
        secret = settings.sso_jwt_secret or settings.jwt_secret
        if not secret:
            raise ValueError("sso_jwt_secret_not_configured")

        now = datetime.now(UTC)
        payload = {
            "iss": SSO_ISSUER,
            "aud": audience,
            "sub": principal.user_id,
            "clerk_user_id": clerk_user_id,
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

    def upsert_identity_link(self, db: Session, claims: ClerkClaims, principal: AuthPrincipal) -> IdentityLink:
        link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == claims.clerk_user_id).first()
        fleetbase_perms: list[str] | None = None
        fleetbase_roles: list[str] | None = None

        if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
            admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
            if admin:
                admin_role = parse_admin_role(admin.role)
                fleetbase_perms = fleetbase_permissions_for_admin(admin_role)
                fleetbase_roles = [admin.role]

        if not link:
            link = IdentityLink(
                clerk_user_id=claims.clerk_user_id,
                email=claims.email or principal.email,
                user_type=principal.user_type.value,
                platform_user_id=principal.user_id,
                platform_org_id=principal.org_id,
                fleetbase_permissions=fleetbase_perms,
                fleetbase_roles=fleetbase_roles,
            )
            db.add(link)
        else:
            link.email = claims.email or principal.email or link.email
            link.user_type = principal.user_type.value
            link.platform_user_id = principal.user_id
            link.platform_org_id = principal.org_id
            link.fleetbase_permissions = fleetbase_perms
            link.fleetbase_roles = fleetbase_roles

        db.commit()
        db.refresh(link)
        return link

    def exchange_fleetbase_session(
        self,
        db: Session,
        settings: Settings,
        claims: ClerkClaims,
        principal: AuthPrincipal,
    ) -> dict:
        """Issue Porterchain SSO JWT and optionally exchange with Fleetbase bridge."""
        if principal.user_type not in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
            raise PermissionError("fleetbase_console_forbidden")

        admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
        if admin:
            admin_role = parse_admin_role(admin.role)
            if not can_access_fleetbase_console(admin_role):
                raise PermissionError("fleetbase_console_forbidden")

        link = self.upsert_identity_link(db, claims, principal)
        sso_token = self.issue_sso_token(
            settings, principal, audience=SSO_AUDIENCE_FLEETBASE, clerk_user_id=claims.clerk_user_id
        )

        fleetbase_session: dict | None = None
        try:
            from porterchain_fleetbase.sso import FleetbaseSsoClient
            from porterchain_fleetbase.config import FleetbaseSettings

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
                email=claims.email or principal.email,
                clerk_user_id=claims.clerk_user_id,
                fleetbase_permissions=link.fleetbase_permissions or [],
                fleetbase_roles=link.fleetbase_roles or [],
            )
            if fleetbase_session and fleetbase_session.get("fleetbase_user_uuid"):
                link.fleetbase_user_uuid = fleetbase_session["fleetbase_user_uuid"]
                link.last_synced_at = datetime.now(UTC)
                if admin and fleetbase_session.get("fleetbase_user_uuid"):
                    admin.fleetbase_user_uuid = fleetbase_session["fleetbase_user_uuid"]
                db.commit()
        except Exception as exc:
            logger.warning("Fleetbase SSO exchange unavailable: %s", exc)

        console_base = settings.fleetbase_console_url.rstrip("/")
        console_url = f"{console_base}/porterchain/sso?token={sso_token}"

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

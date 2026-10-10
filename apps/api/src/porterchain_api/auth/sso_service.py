"""SSO — Porterchain JWT for portal sessions ."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.staff_lookups import get_admin_user
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.identity_links import (
    require_porterchain_user_id,
    upsert_sso_link,
)
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.domain.admin_states import AdminRole
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import PlatformRole
from porterchain_shared.types.user_types import UserType

logger = logging.getLogger(__name__)


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

    def auth_principal_from_current(
        self, db: Session, current: CurrentPrincipal
    ) -> AuthPrincipal | None:
        """Build AuthPrincipal from session CurrentPrincipal (staff or Clerk)."""
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

        return upsert_sso_link(
            db,
            subject=subject,
            email=email or principal.email,
            user_type=principal.user_type.value,
            platform_user_id=pc_id,
            platform_org_id=principal.org_id,
            provider=provider,
            issuer=issuer,
        )

    def session_payload(self, principal: AuthPrincipal) -> dict:
        return {
            "user_id": principal.user_id,
            "user_type": principal.user_type.value,
            "roles": sorted(r.value for r in principal.roles),
            "permissions": sorted(p.value for p in principal.permissions()),
            "org_id": principal.org_id,
            "email": principal.email,
        }

# Re-exports kept for existing importers (integration).
from porterchain_api.config import Settings  # noqa: E402, F401

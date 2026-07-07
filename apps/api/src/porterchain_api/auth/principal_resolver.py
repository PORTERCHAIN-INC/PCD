"""Resolve Clerk JWT → Porterchain AuthPrincipal (single identity, no duplicate users)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings
from porterchain_api.auth.rbac import (
    admin_role_to_platform_roles,
    merchant_role_to_platform_roles,
)
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import parse_merchant_role
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer
from porterchain_api.admin_models import Driver
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import PlatformRole
from porterchain_shared.types.user_types import UserType


class PrincipalResolver:
    def resolve(
        self,
        db: Session,
        claims: ClerkClaims,
        *,
        settings: Settings | None = None,
    ) -> AuthPrincipal | None:
        admin = (
            db.query(AdminUser)
            .filter(AdminUser.clerk_user_id == claims.clerk_user_id, AdminUser.is_active.is_(True))
            .first()
        )
        if admin:
            admin_role = parse_admin_role(admin.role)
            return AuthPrincipal(
                user_id=admin.id,
                user_type=_admin_user_type(admin_role),
                roles=admin_role_to_platform_roles(admin_role),
                org_id=None,
                email=admin.email or claims.email,
                session_id=claims.session_id,
            )

        merchant_user = (
            db.query(MerchantUser)
            .filter(MerchantUser.clerk_user_id == claims.clerk_user_id)
            .first()
        )
        if merchant_user:
            m_role = parse_merchant_role(merchant_user.role)
            return AuthPrincipal(
                user_id=merchant_user.id,
                user_type=UserType.MERCHANT,
                roles=merchant_role_to_platform_roles(m_role),
                org_id=merchant_user.merchant_id,
                email=merchant_user.email or claims.email,
                session_id=claims.session_id,
            )

        driver = db.query(Driver).filter(Driver.clerk_user_id == claims.clerk_user_id).first()
        if driver:
            return AuthPrincipal(
                user_id=driver.id,
                user_type=UserType.DRIVER,
                roles=frozenset({PlatformRole.DRIVER}),
                org_id=None,
                email=driver.email or claims.email,
                session_id=claims.session_id,
            )

        customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
        if customer:
            return AuthPrincipal(
                user_id=customer.id,
                user_type=UserType.CUSTOMER,
                roles=frozenset({PlatformRole.CUSTOMER}),
                org_id=None,
                email=customer.email or claims.email,
                session_id=claims.session_id,
            )

        # Clerk metadata fallback — local dev only (never in production)
        if settings and allow_auth_dev_bypass(settings):
            meta_role = (claims.metadata_role or claims.org_role or "").lower()
            if meta_role in ("dispatcher", "admin", "super_admin", "support", "sales"):
                return AuthPrincipal(
                    user_id=claims.clerk_user_id,
                    user_type=_metadata_user_type(meta_role),
                    roles=admin_role_to_platform_roles(parse_admin_role(meta_role)),
                    org_id=claims.org_id,
                    email=claims.email,
                    session_id=claims.session_id,
                )
            if meta_role.startswith("merchant"):
                m_role = parse_merchant_role(
                    meta_role if meta_role in {r.value for r in MerchantRole} else "merchant_ops"
                )
                return AuthPrincipal(
                    user_id=claims.clerk_user_id,
                    user_type=UserType.MERCHANT,
                    roles=merchant_role_to_platform_roles(m_role),
                    org_id=None,
                    email=claims.email,
                    session_id=claims.session_id,
                )
            if meta_role == "driver":
                return AuthPrincipal(
                    user_id=claims.clerk_user_id,
                    user_type=UserType.DRIVER,
                    roles=frozenset({PlatformRole.DRIVER}),
                    org_id=claims.org_id,
                    email=claims.email,
                    session_id=claims.session_id,
                )

        return None


def _admin_user_type(role: AdminRole) -> UserType:
    if role == AdminRole.DISPATCHER:
        return UserType.DISPATCHER
    if role in (AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD):
        return UserType.SUPPORT
    if role in (AdminRole.SALES, AdminRole.SALES_MANAGER):
        return UserType.SALES
    return UserType.ADMIN


def _metadata_user_type(meta_role: str) -> UserType:
    if meta_role == "dispatcher":
        return UserType.DISPATCHER
    if meta_role == "support":
        return UserType.SUPPORT
    if meta_role == "sales":
        return UserType.SALES
    return UserType.ADMIN

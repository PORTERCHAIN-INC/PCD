"""Resolve Clerk subject → AuthPrincipal from persona tables (Fleetbase SSO only).

Authorization Checks use SpiceDB via CurrentPrincipal — not this helper.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.email_identity import emails_match
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.merchant_engine.rbac import parse_merchant_role
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import PlatformRole
from porterchain_shared.types.user_types import UserType

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


def resolve_persona_principal(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
) -> AuthPrincipal | None:
    _ = settings

    admin = (
        db.query(AdminUser)
        .filter(AdminUser.clerk_user_id == claims.clerk_user_id, AdminUser.is_active.is_(True))
        .first()
    )
    if admin and _profile_email_ok(admin.email, claims.email):
        admin_role = parse_admin_role(admin.role)
        return AuthPrincipal(
            user_id=admin.id,
            user_type=_admin_user_type(admin_role),
            roles=frozenset({_ADMIN_PLATFORM.get(admin_role, PlatformRole.ADMIN)}),
            org_id=None,
            email=admin.email or claims.email,
            session_id=claims.session_id,
        )

    merchant_user = (
        db.query(MerchantUser).filter(MerchantUser.clerk_user_id == claims.clerk_user_id).first()
    )
    if merchant_user and _profile_email_ok(merchant_user.email, claims.email):
        m_role = parse_merchant_role(merchant_user.role)
        platform = (
            PlatformRole.MERCHANT_ADMIN
            if m_role.value in ("owner", "admin")
            else PlatformRole.MERCHANT
        )
        return AuthPrincipal(
            user_id=merchant_user.id,
            user_type=UserType.MERCHANT,
            roles=frozenset({platform}),
            org_id=merchant_user.merchant_id,
            email=merchant_user.email or claims.email,
            session_id=claims.session_id,
        )

    driver = db.query(Driver).filter(Driver.clerk_user_id == claims.clerk_user_id).first()
    if driver and _profile_email_ok(driver.email, claims.email):
        return AuthPrincipal(
            user_id=driver.id,
            user_type=UserType.DRIVER,
            roles=frozenset({PlatformRole.DRIVER}),
            org_id=None,
            email=driver.email or claims.email,
            session_id=claims.session_id,
        )

    customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
    if customer and _profile_email_ok(customer.email, claims.email):
        return AuthPrincipal(
            user_id=customer.id,
            user_type=UserType.CUSTOMER,
            roles=frozenset({PlatformRole.CUSTOMER}),
            org_id=None,
            email=customer.email or claims.email,
            session_id=claims.session_id,
        )

    return None


def _profile_email_ok(system_email: str | None, clerk_email: str | None) -> bool:
    if not clerk_email:
        return True
    return emails_match(system_email, clerk_email)


def _admin_user_type(role: AdminRole) -> UserType:
    if role == AdminRole.DISPATCHER:
        return UserType.DISPATCHER
    if role in (AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD):
        return UserType.SUPPORT
    if role in (AdminRole.SALES, AdminRole.SALES_MANAGER):
        return UserType.SALES
    return UserType.ADMIN

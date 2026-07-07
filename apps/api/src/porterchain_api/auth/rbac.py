"""Unified RBAC — Porterchain enterprise roles → platform permissions."""

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS as ADMIN_MODULES
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.auth.enterprise_rbac import (
    enterprise_role_for_admin,
    enterprise_role_for_merchant,
)
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS as MERCHANT_MODULES
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role
from porterchain_shared.auth.enterprise_roles import (
    ENTERPRISE_ROLE_PERMISSIONS,
    EnterpriseRole,
    permissions_for_enterprise_role,
)
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import Permission, PlatformRole
from porterchain_shared.types.user_types import UserType

_ENTERPRISE_TO_PLATFORM: dict[EnterpriseRole, PlatformRole] = {
    EnterpriseRole.CUSTOMER: PlatformRole.CUSTOMER,
    EnterpriseRole.MERCHANT: PlatformRole.MERCHANT,
    EnterpriseRole.MERCHANT_ADMIN: PlatformRole.MERCHANT_ADMIN,
    EnterpriseRole.DRIVER: PlatformRole.DRIVER,
    EnterpriseRole.DISPATCHER: PlatformRole.DISPATCHER,
    EnterpriseRole.FINANCE: PlatformRole.FINANCE,
    EnterpriseRole.SUPPORT: PlatformRole.SUPPORT,
    EnterpriseRole.OPERATIONS: PlatformRole.OPERATIONS,
    EnterpriseRole.ADMIN: PlatformRole.ADMIN,
    EnterpriseRole.SUPER_ADMIN: PlatformRole.SUPER_ADMIN,
}


def enterprise_role_to_platform_roles(role: EnterpriseRole) -> frozenset[PlatformRole]:
    return frozenset({_ENTERPRISE_TO_PLATFORM[role]})


def admin_role_to_platform_roles(role: AdminRole) -> frozenset[PlatformRole]:
    return enterprise_role_to_platform_roles(enterprise_role_for_admin(role))


def merchant_role_to_platform_roles(role: MerchantRole) -> frozenset[PlatformRole]:
    return enterprise_role_to_platform_roles(enterprise_role_for_merchant(role))


def enterprise_permissions(role: EnterpriseRole) -> frozenset[Permission]:
    return permissions_for_enterprise_role(role)


def principal_can_admin_module(principal: AuthPrincipal, module: str) -> bool:
    staff_roles = (
        PlatformRole.ADMIN,
        PlatformRole.SUPER_ADMIN,
        PlatformRole.DISPATCHER,
        PlatformRole.SUPPORT,
        PlatformRole.FINANCE,
        PlatformRole.OPERATIONS,
    )
    if not principal.has_any_role(*staff_roles):
        return False
    for admin_role in AdminRole:
        platform_roles = admin_role_to_platform_roles(admin_role)
        if not principal.roles.intersection(platform_roles):
            continue
        allowed = ADMIN_MODULES.get(module, frozenset())
        if admin_role in allowed:
            return True
    return False


def principal_has_permission(principal: AuthPrincipal, permission: Permission) -> bool:
    return principal.can(permission)


def merchant_can_module(ctx: MerchantContext, module: str) -> bool:
    allowed = MERCHANT_MODULES.get(module, frozenset())
    return ctx.role in allowed


def user_type_for_principal(principal: AuthPrincipal) -> UserType:
    return principal.user_type

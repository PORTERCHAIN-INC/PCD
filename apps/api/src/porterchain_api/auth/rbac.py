"""Unified RBAC — Clerk principal → platform permissions."""

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS as ADMIN_MODULES
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS as MERCHANT_MODULES
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import Permission, PlatformRole, ROLE_PERMISSIONS
from porterchain_shared.types.user_types import UserType


def admin_role_to_platform_roles(role: AdminRole) -> frozenset[PlatformRole]:
    mapping: dict[AdminRole, PlatformRole] = {
        AdminRole.SUPER_ADMIN: PlatformRole.SUPER_ADMIN,
        AdminRole.ADMIN: PlatformRole.ADMIN,
        AdminRole.DISPATCHER: PlatformRole.DISPATCHER,
        AdminRole.SUPPORT: PlatformRole.SUPPORT,
        AdminRole.SUPPORT_LEAD: PlatformRole.SUPPORT,
        AdminRole.SALES: PlatformRole.SALES,
        AdminRole.SALES_MANAGER: PlatformRole.SALES,
        AdminRole.FINANCE: PlatformRole.ADMIN,
        AdminRole.FLEET_MANAGER: PlatformRole.FLEET_MANAGER,
    }
    platform = mapping.get(role, PlatformRole.ADMIN)
    roles: set[PlatformRole] = {platform}
    if role == AdminRole.DISPATCHER:
        roles.add(PlatformRole.DISPATCHER)
    if role in (AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD):
        roles.add(PlatformRole.SUPPORT)
    if role in (AdminRole.SALES, AdminRole.SALES_MANAGER):
        roles.add(PlatformRole.SALES)
    return frozenset(roles)


def principal_can_admin_module(principal: AuthPrincipal, module: str) -> bool:
    if not principal.has_any_role(PlatformRole.ADMIN, PlatformRole.SUPER_ADMIN, PlatformRole.DISPATCHER):
        return False
    # Resolve admin role from platform roles for module check
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

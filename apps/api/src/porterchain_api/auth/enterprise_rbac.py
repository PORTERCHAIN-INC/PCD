"""Enterprise RBAC — role resolution and module matrices (Porterchain-owned)."""

from __future__ import annotations

from typing import Any

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS as ADMIN_MODULE_PERMISSIONS
from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS as MERCHANT_MODULE_PERMISSIONS
from porterchain_api.merchant_models import MerchantUser
from porterchain_shared.auth.enterprise_roles import (
    ENTERPRISE_ROLE_LABELS,
    ENTERPRISE_ROLE_PERMISSIONS,
    EnterpriseRole,
    permissions_for_enterprise_role,
)
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import Permission
from porterchain_shared.types.user_types import UserType


def enterprise_role_for_admin(role: AdminRole) -> EnterpriseRole:
    if role == AdminRole.SUPER_ADMIN:
        return EnterpriseRole.SUPER_ADMIN
    if role == AdminRole.ADMIN:
        return EnterpriseRole.ADMIN
    if role == AdminRole.DISPATCHER:
        return EnterpriseRole.DISPATCHER
    if role in (AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD):
        return EnterpriseRole.SUPPORT
    if role == AdminRole.FINANCE:
        return EnterpriseRole.FINANCE
    if role in (
        AdminRole.FLEET_MANAGER,
        AdminRole.SALES,
        AdminRole.SALES_MANAGER,
        AdminRole.MARKETING,
        AdminRole.COMPLIANCE,
        AdminRole.DEVELOPER,
        AdminRole.READ_ONLY,
    ):
        return EnterpriseRole.OPERATIONS
    return EnterpriseRole.ADMIN


def enterprise_role_for_merchant(role: MerchantRole) -> EnterpriseRole:
    if role in (MerchantRole.OWNER, MerchantRole.ADMIN):
        return EnterpriseRole.MERCHANT_ADMIN
    return EnterpriseRole.MERCHANT


def resolve_enterprise_role(
    *,
    admin: AdminUser | None = None,
    merchant_user: MerchantUser | None = None,
    merchant_role: MerchantRole | None = None,
    is_driver: bool = False,
    is_customer: bool = False,
) -> EnterpriseRole | None:
    if admin:
        return enterprise_role_for_admin(AdminRole(admin.role) if admin.role in {r.value for r in AdminRole} else AdminRole.READ_ONLY)
    if merchant_user:
        m_role = merchant_role or MerchantRole(merchant_user.role) if merchant_user.role in {r.value for r in MerchantRole} else MerchantRole.OPS
        return enterprise_role_for_merchant(m_role)
    if is_driver:
        return EnterpriseRole.DRIVER
    if is_customer:
        return EnterpriseRole.CUSTOMER
    return None


def admin_modules_for_enterprise_role(role: EnterpriseRole) -> list[str]:
    modules: list[str] = []
    for module, allowed_admin_roles in ADMIN_MODULE_PERMISSIONS.items():
        enterprise_allowed = {enterprise_role_for_admin(r) for r in allowed_admin_roles}
        if role in enterprise_allowed:
            modules.append(module)
    return sorted(modules)


def merchant_modules_for_enterprise_role(role: EnterpriseRole) -> list[str]:
    if role == EnterpriseRole.MERCHANT_ADMIN:
        merchant_roles = frozenset(MerchantRole)
    elif role == EnterpriseRole.MERCHANT:
        merchant_roles = frozenset(
            {MerchantRole.OPS, MerchantRole.FINANCE, MerchantRole.READONLY}
        )
    else:
        return []
    modules: list[str] = []
    for module, allowed in MERCHANT_MODULE_PERMISSIONS.items():
        if merchant_roles.intersection(allowed):
            modules.append(module)
    return sorted(modules)


def rbac_matrix() -> dict[str, Any]:
    """Full enterprise role × permission × portal module matrix."""
    roles = []
    for role in EnterpriseRole:
        perms = sorted(p.value for p in permissions_for_enterprise_role(role))
        roles.append(
            {
                "role": role.value,
                "label": ENTERPRISE_ROLE_LABELS[role],
                "permissions": perms,
                "admin_modules": admin_modules_for_enterprise_role(role),
                "merchant_modules": merchant_modules_for_enterprise_role(role),
            }
        )

    permission_rows = []
    for perm in Permission:
        holders = sorted(
            r.value for r in EnterpriseRole if perm in ENTERPRISE_ROLE_PERMISSIONS.get(r, frozenset())
        )
        permission_rows.append({"permission": perm.value, "roles": holders})

    admin_modules = {
        module: sorted(enterprise_role_for_admin(r).value for r in allowed)
        for module, allowed in sorted(ADMIN_MODULE_PERMISSIONS.items())
    }
    merchant_modules = {
        module: sorted(enterprise_role_for_merchant(r).value for r in allowed)
        for module, allowed in sorted(MERCHANT_MODULE_PERMISSIONS.items())
    }

    return {
        "roles": roles,
        "permissions": permission_rows,
        "admin_modules": admin_modules,
        "merchant_modules": merchant_modules,
    }


def resolve_enterprise_role_for_principal(
    db,
    principal: AuthPrincipal,
) -> EnterpriseRole | None:
    if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT, UserType.SALES):
        admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
        if admin:
            return enterprise_role_for_admin(parse_admin_role(admin.role))
    if principal.user_type == UserType.MERCHANT:
        mu = db.query(MerchantUser).filter(MerchantUser.id == principal.user_id).first()
        if mu:
            m_role = MerchantRole(mu.role) if mu.role in {r.value for r in MerchantRole} else MerchantRole.OPS
            return enterprise_role_for_merchant(m_role)
    if principal.user_type == UserType.DRIVER:
        return EnterpriseRole.DRIVER
    if principal.user_type == UserType.CUSTOMER:
        return EnterpriseRole.CUSTOMER
    return None


def principal_enterprise_payload(db, principal: AuthPrincipal) -> dict[str, Any]:
    role = resolve_enterprise_role_for_principal(db, principal)
    if not role:
        return {
            "enterprise_role": None,
            "enterprise_permissions": [],
            "admin_modules": [],
            "merchant_modules": [],
        }
    return {
        "enterprise_role": role.value,
        "enterprise_permissions": sorted(p.value for p in permissions_for_enterprise_role(role)),
        "admin_modules": admin_modules_for_enterprise_role(role),
        "merchant_modules": merchant_modules_for_enterprise_role(role),
    }


def enterprise_permissions_matrix() -> dict[str, list[str]]:
    return {
        role.value: sorted(p.value for p in perms)
        for role, perms in ENTERPRISE_ROLE_PERMISSIONS.items()
    }

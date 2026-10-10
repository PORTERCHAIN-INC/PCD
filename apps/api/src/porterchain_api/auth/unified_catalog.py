"""Unified identity role/permission catalog.

Enum labels + invite rules. SpiceDB is the authorization Check SoT.
`permissions_for_roles` remains only as a transitional UX/test helper — not request Check.
"""

from __future__ import annotations

from enum import StrEnum

from porterchain_shared.auth.roles import Permission

from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantRole


class AccountStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OnboardingStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class ScopeType(StrEnum):
    GLOBAL = "global"
    ORGANIZATION = "organization"
    SELF = "self"


class AuthProvider(StrEnum):
    CLERK = "clerk"


class AssignableRole(StrEnum):
    """Roles that may appear on user_role_assignments.role_key.

    Preserves existing AdminRole + MerchantRole vocabulary and adds
    customer / driver persona roles for multi-role users.
    """

    # Platform / staff (map 1:1 from AdminRole)
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DISPATCHER = "dispatcher"
    SUPPORT = "support"
    SUPPORT_LEAD = "support_lead"
    SALES = "sales"
    SALES_MANAGER = "sales_manager"
    FINANCE = "finance"
    COMPLIANCE = "compliance"
    DEVELOPER = "developer"
    MARKETING = "marketing"
    READ_ONLY = "read_only"
    FLEET_MANAGER = "fleet_manager"
    OPERATIONS_MANAGER = "operations_manager"  # alias role; permissions = admin

    # Merchant (map 1:1 from MerchantRole)
    MERCHANT_OWNER = "merchant_owner"
    MERCHANT_ADMIN = "merchant_admin"
    MERCHANT_OPS = "merchant_ops"
    MERCHANT_FINANCE = "merchant_finance"
    MERCHANT_READONLY = "merchant_readonly"

    # Personas
    DRIVER = "driver"
    CUSTOMER = "customer"


class UnifiedPermission(StrEnum):
    """resource.action vocabulary + legacy Permission values for compatibility."""

    # Portal access
    PLATFORM_ADMIN_ACCESS = "platform.admin.access"
    MERCHANT_PORTAL_ACCESS = "merchant_portal.access"
    DRIVER_PORTAL_ACCESS = "driver_portal.access"
    CUSTOMER_PORTAL_ACCESS = "customer_portal.access"

    # Users / audit
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"
    USERS_ASSIGN_ACCESS = "users.assign_access"
    AUDIT_READ = "audit.read"
    SETTINGS_MANAGE = "settings.manage"

    # Ops (align with existing engines)
    OPERATIONS_READ = "operations.read"
    OPERATIONS_MANAGE = "operations.manage"
    DISPATCH_READ = "dispatch.read"
    DISPATCH_MANAGE = "dispatch.manage"
    MERCHANTS_READ = "merchants.read"
    MERCHANTS_MANAGE = "merchants.manage"
    DELIVERIES_CREATE = "deliveries.create"
    DELIVERIES_READ = "deliveries.read"
    DELIVERIES_MANAGE = "deliveries.manage"
    DRIVER_JOBS_READ = "driver_jobs.read"
    DRIVER_JOBS_ACCEPT = "driver_jobs.accept"
    DRIVER_JOBS_UPDATE = "driver_jobs.update"
    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"

    # Legacy coarse permissions (porterchain_shared.auth.roles.Permission)
    QUOTE_READ = "quote:read"
    QUOTE_WRITE = "quote:write"
    ORDER_READ = "order:read"
    ORDER_WRITE = "order:write"
    LEGACY_DISPATCH_MANAGE = "dispatch:manage"
    LEGACY_MERCHANT_MANAGE = "merchant:manage"
    LEGACY_DRIVER_MANAGE = "driver:manage"
    LEGACY_BILLING_MANAGE = "billing:manage"
    LEGACY_CRM_MANAGE = "crm:manage"
    LEGACY_SUPPORT_MANAGE = "support:manage"
    LEGACY_ADMIN_SETTINGS = "admin:settings"
    SYSTEM_ALL = "system:all"


# Roles that must never be granted by public sign-up / email / metadata.
INVITE_ONLY_ROLES: frozenset[AssignableRole] = frozenset(
    {
        AssignableRole.SUPER_ADMIN,
        AssignableRole.ADMIN,
        AssignableRole.OPERATIONS_MANAGER,
        AssignableRole.DISPATCHER,
        AssignableRole.SUPPORT,
        AssignableRole.SUPPORT_LEAD,
        AssignableRole.SALES,
        AssignableRole.SALES_MANAGER,
        AssignableRole.FINANCE,
        AssignableRole.COMPLIANCE,
        AssignableRole.DEVELOPER,
        AssignableRole.MARKETING,
        AssignableRole.READ_ONLY,
        AssignableRole.FLEET_MANAGER,
    }
)

# Only these may be auto-proposed on verified self-registration (policy).
OPEN_SIGNUP_ROLES: frozenset[AssignableRole] = frozenset({AssignableRole.CUSTOMER})

# Driver / merchant require application or invite — not elevated staff.
APPLICATION_OR_INVITE_ROLES: frozenset[AssignableRole] = frozenset(
    {
        AssignableRole.DRIVER,
        AssignableRole.MERCHANT_OWNER,
        AssignableRole.MERCHANT_ADMIN,
        AssignableRole.MERCHANT_OPS,
        AssignableRole.MERCHANT_FINANCE,
        AssignableRole.MERCHANT_READONLY,
    }
)


def admin_role_to_assignable(role: AdminRole) -> AssignableRole:
    if role == AdminRole.SUPER_ADMIN:
        return AssignableRole.SUPER_ADMIN
    return AssignableRole(role.value)


def merchant_role_to_assignable(role: MerchantRole) -> AssignableRole:
    return AssignableRole(role.value)


def assignable_to_admin_role(role: AssignableRole) -> AdminRole | None:
    if role == AssignableRole.OPERATIONS_MANAGER:
        return AdminRole.ADMIN
    try:
        return AdminRole(role.value)
    except ValueError:
        return None


def assignable_to_merchant_role(role: AssignableRole) -> MerchantRole | None:
    try:
        return MerchantRole(role.value)
    except ValueError:
        return None


def is_invite_only(role: AssignableRole | str) -> bool:
    key = AssignableRole(role) if not isinstance(role, AssignableRole) else role
    return key in INVITE_ONLY_ROLES


def may_self_signup(role: AssignableRole | str) -> bool:
    key = AssignableRole(role) if not isinstance(role, AssignableRole) else role
    return key in OPEN_SIGNUP_ROLES


# Coarse unified permission packs (Phase 2 catalog). Module matrices in
# admin_engine/rbac.py and merchant_engine/rbac.py remain the live gate until Phase 3.
ROLE_UNIFIED_PERMISSIONS: dict[AssignableRole, frozenset[UnifiedPermission]] = {
    AssignableRole.SUPER_ADMIN: frozenset(UnifiedPermission),
    AssignableRole.ADMIN: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.USERS_READ,
            UnifiedPermission.USERS_MANAGE,
            UnifiedPermission.USERS_ASSIGN_ACCESS,
            UnifiedPermission.AUDIT_READ,
            UnifiedPermission.SETTINGS_MANAGE,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.OPERATIONS_MANAGE,
            UnifiedPermission.DISPATCH_READ,
            UnifiedPermission.DISPATCH_MANAGE,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.MERCHANTS_MANAGE,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.DELIVERIES_MANAGE,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.BILLING_MANAGE,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.ORDER_WRITE,
            UnifiedPermission.LEGACY_DISPATCH_MANAGE,
            UnifiedPermission.LEGACY_MERCHANT_MANAGE,
            UnifiedPermission.LEGACY_DRIVER_MANAGE,
            UnifiedPermission.LEGACY_BILLING_MANAGE,
            UnifiedPermission.LEGACY_CRM_MANAGE,
            UnifiedPermission.LEGACY_SUPPORT_MANAGE,
            UnifiedPermission.LEGACY_ADMIN_SETTINGS,
        }
    ),
    AssignableRole.OPERATIONS_MANAGER: frozenset(),  # filled below = ADMIN
    AssignableRole.DISPATCHER: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.OPERATIONS_MANAGE,
            UnifiedPermission.DISPATCH_READ,
            UnifiedPermission.DISPATCH_MANAGE,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.DELIVERIES_MANAGE,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.ORDER_WRITE,
            UnifiedPermission.LEGACY_DISPATCH_MANAGE,
            UnifiedPermission.LEGACY_DRIVER_MANAGE,
        }
    ),
    AssignableRole.SUPPORT: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.DISPATCH_READ,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.LEGACY_SUPPORT_MANAGE,
            UnifiedPermission.LEGACY_CRM_MANAGE,
            UnifiedPermission.AUDIT_READ,
        }
    ),
    AssignableRole.SUPPORT_LEAD: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.DISPATCH_READ,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.DELIVERIES_MANAGE,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.ORDER_WRITE,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.LEGACY_SUPPORT_MANAGE,
            UnifiedPermission.LEGACY_CRM_MANAGE,
            UnifiedPermission.LEGACY_BILLING_MANAGE,
            UnifiedPermission.AUDIT_READ,
        }
    ),
    AssignableRole.SALES: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.MERCHANTS_MANAGE,
            UnifiedPermission.QUOTE_READ,
            UnifiedPermission.QUOTE_WRITE,
            UnifiedPermission.LEGACY_CRM_MANAGE,
            UnifiedPermission.LEGACY_MERCHANT_MANAGE,
        }
    ),
    AssignableRole.SALES_MANAGER: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.MERCHANTS_MANAGE,
            UnifiedPermission.USERS_READ,
            UnifiedPermission.QUOTE_READ,
            UnifiedPermission.QUOTE_WRITE,
            UnifiedPermission.LEGACY_CRM_MANAGE,
            UnifiedPermission.LEGACY_MERCHANT_MANAGE,
        }
    ),
    AssignableRole.FINANCE: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.BILLING_MANAGE,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.LEGACY_BILLING_MANAGE,
            UnifiedPermission.AUDIT_READ,
        }
    ),
    AssignableRole.COMPLIANCE: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.AUDIT_READ,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.ORDER_READ,
        }
    ),
    AssignableRole.DEVELOPER: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.SETTINGS_MANAGE,
            UnifiedPermission.AUDIT_READ,
        }
    ),
    AssignableRole.MARKETING: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.LEGACY_CRM_MANAGE,
            UnifiedPermission.MERCHANTS_READ,
        }
    ),
    AssignableRole.READ_ONLY: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.DISPATCH_READ,
            UnifiedPermission.MERCHANTS_READ,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.AUDIT_READ,
        }
    ),
    AssignableRole.FLEET_MANAGER: frozenset(
        {
            UnifiedPermission.PLATFORM_ADMIN_ACCESS,
            UnifiedPermission.DISPATCH_READ,
            UnifiedPermission.DISPATCH_MANAGE,
            UnifiedPermission.OPERATIONS_READ,
            UnifiedPermission.LEGACY_DISPATCH_MANAGE,
            UnifiedPermission.LEGACY_DRIVER_MANAGE,
            UnifiedPermission.ORDER_READ,
        }
    ),
    AssignableRole.MERCHANT_OWNER: frozenset(
        {
            UnifiedPermission.MERCHANT_PORTAL_ACCESS,
            UnifiedPermission.DELIVERIES_CREATE,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.DELIVERIES_MANAGE,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.BILLING_MANAGE,
            UnifiedPermission.USERS_READ,
            UnifiedPermission.USERS_MANAGE,
            UnifiedPermission.QUOTE_READ,
            UnifiedPermission.QUOTE_WRITE,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.ORDER_WRITE,
            UnifiedPermission.LEGACY_MERCHANT_MANAGE,
        }
    ),
    AssignableRole.MERCHANT_ADMIN: frozenset(
        {
            UnifiedPermission.MERCHANT_PORTAL_ACCESS,
            UnifiedPermission.DELIVERIES_CREATE,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.DELIVERIES_MANAGE,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.USERS_READ,
            UnifiedPermission.USERS_MANAGE,
            UnifiedPermission.QUOTE_READ,
            UnifiedPermission.QUOTE_WRITE,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.ORDER_WRITE,
        }
    ),
    AssignableRole.MERCHANT_OPS: frozenset(
        {
            UnifiedPermission.MERCHANT_PORTAL_ACCESS,
            UnifiedPermission.DELIVERIES_CREATE,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.DELIVERIES_MANAGE,
            UnifiedPermission.ORDER_READ,
            UnifiedPermission.ORDER_WRITE,
            UnifiedPermission.QUOTE_READ,
            UnifiedPermission.QUOTE_WRITE,
        }
    ),
    AssignableRole.MERCHANT_FINANCE: frozenset(
        {
            UnifiedPermission.MERCHANT_PORTAL_ACCESS,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.BILLING_MANAGE,
            UnifiedPermission.ORDER_READ,
        }
    ),
    AssignableRole.MERCHANT_READONLY: frozenset(
        {
            UnifiedPermission.MERCHANT_PORTAL_ACCESS,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.BILLING_READ,
            UnifiedPermission.ORDER_READ,
        }
    ),
    AssignableRole.DRIVER: frozenset(
        {
            UnifiedPermission.DRIVER_PORTAL_ACCESS,
            UnifiedPermission.DRIVER_JOBS_READ,
            UnifiedPermission.DRIVER_JOBS_ACCEPT,
            UnifiedPermission.DRIVER_JOBS_UPDATE,
            UnifiedPermission.ORDER_READ,
        }
    ),
    AssignableRole.CUSTOMER: frozenset(
        {
            UnifiedPermission.CUSTOMER_PORTAL_ACCESS,
            UnifiedPermission.DELIVERIES_CREATE,
            UnifiedPermission.DELIVERIES_READ,
            UnifiedPermission.QUOTE_READ,
            UnifiedPermission.QUOTE_WRITE,
            UnifiedPermission.ORDER_READ,
        }
    ),
}

ROLE_UNIFIED_PERMISSIONS[AssignableRole.OPERATIONS_MANAGER] = ROLE_UNIFIED_PERMISSIONS[AssignableRole.ADMIN]


def permissions_for_roles(roles: set[AssignableRole] | set[str]) -> frozenset[UnifiedPermission]:
    """Union of permissions across simultaneous role assignments (deny-by-default empty)."""
    out: set[UnifiedPermission] = set()
    for role in roles:
        key = AssignableRole(role) if not isinstance(role, AssignableRole) else role
        out |= set(ROLE_UNIFIED_PERMISSIONS.get(key, frozenset()))
    return frozenset(out)


def legacy_permissions_for_roles(roles: set[AssignableRole] | set[str]) -> frozenset[Permission]:
    """Project unified packs onto existing shared Permission enum where names overlap."""
    unified = permissions_for_roles(roles)
    legacy: set[Permission] = set()
    for perm in unified:
        try:
            legacy.add(Permission(perm.value))
        except ValueError:
            continue
    return frozenset(legacy)


__all__ = [
    "APPLICATION_OR_INVITE_ROLES",
    "INVITE_ONLY_ROLES",
    "OPEN_SIGNUP_ROLES",
    "ROLE_UNIFIED_PERMISSIONS",
    "AccountStatus",
    "AssignableRole",
    "AuthProvider",
    "OnboardingStatus",
    "ScopeType",
    "UnifiedPermission",
    "admin_role_to_assignable",
    "assignable_to_admin_role",
    "assignable_to_merchant_role",
    "is_invite_only",
    "legacy_permissions_for_roles",
    "may_self_signup",
    "merchant_role_to_assignable",
    "permissions_for_roles",
]

"""Platform RBAC roles — Clerk is the sole identity provider."""

from enum import StrEnum


class PlatformRole(StrEnum):
    VISITOR = "visitor"
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    MERCHANT_ADMIN = "merchant_admin"
    DRIVER = "driver"
    DISPATCHER = "dispatcher"
    SUPPORT = "support"
    SALES = "sales"
    FLEET_MANAGER = "fleet_manager"
    FINANCE = "finance"
    OPERATIONS = "operations"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class Permission(StrEnum):
    QUOTE_READ = "quote:read"
    QUOTE_WRITE = "quote:write"
    ORDER_READ = "order:read"
    ORDER_WRITE = "order:write"
    DISPATCH_MANAGE = "dispatch:manage"
    MERCHANT_MANAGE = "merchant:manage"
    DRIVER_MANAGE = "driver:manage"
    BILLING_MANAGE = "billing:manage"
    CRM_MANAGE = "crm:manage"
    SUPPORT_MANAGE = "support:manage"
    ADMIN_SETTINGS = "admin:settings"
    SYSTEM_ALL = "system:all"


ROLE_PERMISSIONS: dict[PlatformRole, frozenset[Permission]] = {
    PlatformRole.VISITOR: frozenset({Permission.QUOTE_READ, Permission.QUOTE_WRITE}),
    PlatformRole.CUSTOMER: frozenset(
        {Permission.QUOTE_READ, Permission.QUOTE_WRITE, Permission.ORDER_READ}
    ),
    PlatformRole.MERCHANT: frozenset(
        {
            Permission.QUOTE_READ,
            Permission.QUOTE_WRITE,
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
        }
    ),
    PlatformRole.MERCHANT_ADMIN: frozenset(
        {
            Permission.QUOTE_READ,
            Permission.QUOTE_WRITE,
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
            Permission.MERCHANT_MANAGE,
        }
    ),
    PlatformRole.DRIVER: frozenset({Permission.ORDER_READ}),
    PlatformRole.DISPATCHER: frozenset(
        {Permission.ORDER_READ, Permission.ORDER_WRITE, Permission.DISPATCH_MANAGE}
    ),
    PlatformRole.SUPPORT: frozenset(
        {Permission.ORDER_READ, Permission.SUPPORT_MANAGE, Permission.CRM_MANAGE}
    ),
    PlatformRole.SALES: frozenset({Permission.CRM_MANAGE, Permission.MERCHANT_MANAGE}),
    PlatformRole.FLEET_MANAGER: frozenset(
        {Permission.DISPATCH_MANAGE, Permission.DRIVER_MANAGE}
    ),
    PlatformRole.FINANCE: frozenset({Permission.ORDER_READ, Permission.BILLING_MANAGE}),
    PlatformRole.OPERATIONS: frozenset(
        {
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
            Permission.DISPATCH_MANAGE,
            Permission.DRIVER_MANAGE,
            Permission.MERCHANT_MANAGE,
            Permission.CRM_MANAGE,
        }
    ),
    PlatformRole.ADMIN: frozenset(
        {
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
            Permission.DISPATCH_MANAGE,
            Permission.MERCHANT_MANAGE,
            Permission.DRIVER_MANAGE,
            Permission.BILLING_MANAGE,
            Permission.CRM_MANAGE,
            Permission.SUPPORT_MANAGE,
            Permission.ADMIN_SETTINGS,
        }
    ),
    PlatformRole.SUPER_ADMIN: frozenset(Permission),
}

"""Enterprise RBAC — canonical Porterchain roles (never Clerk Organizations)."""

from enum import StrEnum

from porterchain_shared.auth.roles import Permission


class EnterpriseRole(StrEnum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    MERCHANT_ADMIN = "merchant_admin"
    DRIVER = "driver"
    DISPATCHER = "dispatcher"
    FINANCE = "finance"
    SUPPORT = "support"
    OPERATIONS = "operations"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


ENTERPRISE_ROLE_LABELS: dict[EnterpriseRole, str] = {
    EnterpriseRole.CUSTOMER: "Customer",
    EnterpriseRole.MERCHANT: "Merchant",
    EnterpriseRole.MERCHANT_ADMIN: "Merchant Admin",
    EnterpriseRole.DRIVER: "Driver",
    EnterpriseRole.DISPATCHER: "Dispatcher",
    EnterpriseRole.FINANCE: "Finance",
    EnterpriseRole.SUPPORT: "Support",
    EnterpriseRole.OPERATIONS: "Operations",
    EnterpriseRole.ADMIN: "Admin",
    EnterpriseRole.SUPER_ADMIN: "Super Admin",
}


ENTERPRISE_ROLE_PERMISSIONS: dict[EnterpriseRole, frozenset[Permission]] = {
    EnterpriseRole.CUSTOMER: frozenset(
        {Permission.QUOTE_READ, Permission.QUOTE_WRITE, Permission.ORDER_READ}
    ),
    EnterpriseRole.MERCHANT: frozenset(
        {
            Permission.QUOTE_READ,
            Permission.QUOTE_WRITE,
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
        }
    ),
    EnterpriseRole.MERCHANT_ADMIN: frozenset(
        {
            Permission.QUOTE_READ,
            Permission.QUOTE_WRITE,
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
            Permission.MERCHANT_MANAGE,
        }
    ),
    EnterpriseRole.DRIVER: frozenset({Permission.ORDER_READ}),
    EnterpriseRole.DISPATCHER: frozenset(
        {Permission.ORDER_READ, Permission.ORDER_WRITE, Permission.DISPATCH_MANAGE}
    ),
    EnterpriseRole.FINANCE: frozenset(
        {Permission.ORDER_READ, Permission.BILLING_MANAGE}
    ),
    EnterpriseRole.SUPPORT: frozenset(
        {Permission.ORDER_READ, Permission.SUPPORT_MANAGE, Permission.CRM_MANAGE}
    ),
    EnterpriseRole.OPERATIONS: frozenset(
        {
            Permission.ORDER_READ,
            Permission.ORDER_WRITE,
            Permission.DISPATCH_MANAGE,
            Permission.DRIVER_MANAGE,
            Permission.MERCHANT_MANAGE,
            Permission.CRM_MANAGE,
        }
    ),
    EnterpriseRole.ADMIN: frozenset(
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
    EnterpriseRole.SUPER_ADMIN: frozenset(Permission),
}


def permissions_for_enterprise_role(role: EnterpriseRole) -> frozenset[Permission]:
    return ENTERPRISE_ROLE_PERMISSIONS.get(role, frozenset())

"""UX module keys derived from UnifiedPermission packs — not authorization Check SoT.

SpiceDB Check (require_module / require_relation) is authoritative. This map only
feeds session-context `modules` for portal nav hints.
"""

from __future__ import annotations

from porterchain_api.auth.unified_catalog import UnifiedPermission

# Admin module key → permission used for nav projection
ADMIN_MODULE_TO_PERMISSION: dict[str, UnifiedPermission] = {
    "dashboard": UnifiedPermission.PLATFORM_ADMIN_ACCESS,
    "crm": UnifiedPermission.LEGACY_CRM_MANAGE,
    "crm_read": UnifiedPermission.LEGACY_CRM_MANAGE,
    "quotes": UnifiedPermission.QUOTE_WRITE,
    "quotes_read": UnifiedPermission.QUOTE_READ,
    "bookings": UnifiedPermission.ORDER_WRITE,
    "merchants": UnifiedPermission.MERCHANTS_MANAGE,
    "merchants_read": UnifiedPermission.MERCHANTS_READ,
    "drivers": UnifiedPermission.LEGACY_DRIVER_MANAGE,
    "drivers_read": UnifiedPermission.OPERATIONS_READ,
    "dispatch": UnifiedPermission.DISPATCH_MANAGE,
    "dispatch_read": UnifiedPermission.DISPATCH_READ,
    "orders": UnifiedPermission.ORDER_WRITE,
    "orders_read": UnifiedPermission.ORDER_READ,
    "pricing": UnifiedPermission.SETTINGS_MANAGE,
    "pricing_read": UnifiedPermission.OPERATIONS_READ,
    "finance": UnifiedPermission.BILLING_MANAGE,
    "finance_read": UnifiedPermission.BILLING_READ,
    "claims": UnifiedPermission.LEGACY_SUPPORT_MANAGE,
    "claims_read": UnifiedPermission.OPERATIONS_READ,
    "support": UnifiedPermission.LEGACY_SUPPORT_MANAGE,
    "support_read": UnifiedPermission.OPERATIONS_READ,
    "reports": UnifiedPermission.OPERATIONS_READ,
    "settings": UnifiedPermission.SETTINGS_MANAGE,
    "notifications": UnifiedPermission.OPERATIONS_MANAGE,
    "notifications_read": UnifiedPermission.OPERATIONS_READ,
    "developers": UnifiedPermission.SETTINGS_MANAGE,
    "diagnostics": UnifiedPermission.SETTINGS_MANAGE,
    "diagnostics_write": UnifiedPermission.SETTINGS_MANAGE,
    "map": UnifiedPermission.DISPATCH_READ,
    "routes": UnifiedPermission.DISPATCH_MANAGE,
    "routes_read": UnifiedPermission.DISPATCH_READ,
    "routes_dispatch": UnifiedPermission.DISPATCH_MANAGE,
    "content": UnifiedPermission.SETTINGS_MANAGE,
    "content_read": UnifiedPermission.OPERATIONS_READ,
}

MERCHANT_MODULE_TO_PERMISSION: dict[str, UnifiedPermission] = {
    "dashboard": UnifiedPermission.MERCHANT_PORTAL_ACCESS,
    "book": UnifiedPermission.DELIVERIES_CREATE,
    "bulk": UnifiedPermission.DELIVERIES_MANAGE,
    "api_keys": UnifiedPermission.SETTINGS_MANAGE,
    "orders": UnifiedPermission.DELIVERIES_READ,
    "orders_write": UnifiedPermission.DELIVERIES_MANAGE,
    "tracking": UnifiedPermission.DELIVERIES_READ,
    "invoices": UnifiedPermission.BILLING_READ,
    "invoices_pay": UnifiedPermission.BILLING_MANAGE,
    "statements": UnifiedPermission.BILLING_READ,
    "reports": UnifiedPermission.OPERATIONS_READ,
    "billing": UnifiedPermission.BILLING_MANAGE,
    "users": UnifiedPermission.USERS_MANAGE,
    "settings": UnifiedPermission.SETTINGS_MANAGE,
    "support": UnifiedPermission.LEGACY_SUPPORT_MANAGE,
    "claims": UnifiedPermission.LEGACY_SUPPORT_MANAGE,
}


def modules_for_permissions(permissions: frozenset[UnifiedPermission] | set[UnifiedPermission]) -> list[str]:
    """Nav/module keys implied by a unified permission pack (admin + merchant catalogs)."""
    if UnifiedPermission.SYSTEM_ALL in permissions:
        return sorted(set(ADMIN_MODULE_TO_PERMISSION) | set(MERCHANT_MODULE_TO_PERMISSION))
    modules: set[str] = set()
    for module, perm in ADMIN_MODULE_TO_PERMISSION.items():
        if perm in permissions:
            modules.add(module)
    for module, perm in MERCHANT_MODULE_TO_PERMISSION.items():
        if perm in permissions:
            modules.add(module)
    return sorted(modules)

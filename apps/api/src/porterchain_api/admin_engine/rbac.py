"""Admin portal module catalog + SpiceDB Check helpers.

``MODULE_PERMISSIONS`` is the **role→module catalog** used to:
- expand ``schema.zed`` platform permissions (via ``platform_roles``)
- project UX module lists (authorize responses, nav hints)

It is **not** the authorization Check SoT — ``require_module`` Checks SpiceDB only.
"""

from dataclasses import dataclass

from porterchain_api.admin_models import AdminUser
from porterchain_api.domain.admin_states import AdminRole, PORTAL_ROLE_MAP


@dataclass(frozen=True)
class AdminContext:
    user: AdminUser
    role: AdminRole


MODULE_PERMISSIONS: dict[str, frozenset[AdminRole]] = {
    "dashboard": frozenset(AdminRole),
    "crm": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.SALES, AdminRole.SALES_MANAGER, AdminRole.MARKETING}
    ),
    "crm_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.SALES,
            AdminRole.SALES_MANAGER,
            AdminRole.SUPPORT,
            AdminRole.SUPPORT_LEAD,
            AdminRole.MARKETING,
        }
    ),
    "quotes": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SALES, AdminRole.FLEET_MANAGER}
    ),
    "quotes_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.DISPATCHER,
            AdminRole.SUPPORT,
            AdminRole.SUPPORT_LEAD,
            AdminRole.SALES,
            AdminRole.FINANCE,
            AdminRole.READ_ONLY,
        }
    ),
    "bookings": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}
    ),
    "merchants": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.SALES,
            AdminRole.SALES_MANAGER,
            AdminRole.COMPLIANCE,
        }
    ),
    "merchants_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.DISPATCHER,
            AdminRole.SUPPORT,
            AdminRole.SALES,
            AdminRole.FINANCE,
            AdminRole.COMPLIANCE,
            AdminRole.READ_ONLY,
        }
    ),
    "drivers": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER, AdminRole.COMPLIANCE}
    ),
    "drivers_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.DISPATCHER,
            AdminRole.SUPPORT,
            AdminRole.SALES,
            AdminRole.COMPLIANCE,
            AdminRole.READ_ONLY,
        }
    ),
    "dispatch": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER}),
    "dispatch_read": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}
    ),
    "orders": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}
    ),
    "orders_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.DISPATCHER,
            AdminRole.SUPPORT,
            AdminRole.SUPPORT_LEAD,
            AdminRole.SALES,
            AdminRole.FINANCE,
            AdminRole.COMPLIANCE,
            AdminRole.READ_ONLY,
        }
    ),
    "pricing": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.SALES, AdminRole.SALES_MANAGER}),
    "pricing_read": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SALES}),
    "finance": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.FINANCE, AdminRole.SUPPORT_LEAD}),
    "finance_read": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.FINANCE, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}
    ),
    "claims": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.SUPPORT_LEAD, AdminRole.FINANCE, AdminRole.COMPLIANCE}
    ),
    "claims_read": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}
    ),
    "support": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD}
    ),
    "support_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.DISPATCHER,
            AdminRole.SUPPORT,
            AdminRole.SUPPORT_LEAD,
            AdminRole.SALES,
            AdminRole.FINANCE,
            AdminRole.READ_ONLY,
        }
    ),
    "reports": frozenset(AdminRole),
    "settings": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN}),
    "notifications": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.SUPPORT_LEAD, AdminRole.MARKETING}
    ),
    "notifications_read": frozenset(AdminRole),
    "developers": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DEVELOPER}),
    "diagnostics": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DEVELOPER}),
    "diagnostics_write": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN}),
    "map": frozenset(
        {AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER, AdminRole.SUPPORT}
    ),
    "routes": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER, AdminRole.FLEET_MANAGER}),
    "routes_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.DISPATCHER,
            AdminRole.FLEET_MANAGER,
            AdminRole.SUPPORT,
            AdminRole.SUPPORT_LEAD,
            AdminRole.READ_ONLY,
        }
    ),
    "routes_dispatch": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.DISPATCHER}),
    "content": frozenset({AdminRole.SUPER_ADMIN, AdminRole.ADMIN, AdminRole.MARKETING}),
    "content_read": frozenset(
        {
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.MARKETING,
            AdminRole.SALES,
            AdminRole.READ_ONLY,
        }
    ),
}


def require_module(ctx: AdminContext, module: str) -> None:
    """Authorize admin module via SpiceDB only — no matrix fallback, no portal bypass."""
    from porterchain_api.authz.client import get_authz_client
    from porterchain_api.authz.tuples import PLATFORM_ID

    user_id = getattr(ctx.user, "porterchain_user_id", None)
    if not user_id:
        raise PermissionError(f"admin_forbidden:{module}:unlinked_user")

    client = get_authz_client()
    # Check the exact module key (e.g. finance_read) — never OR with portal ``admin``.
    if client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission=module,
        subject_id=user_id,
    ):
        return
    raise PermissionError(f"admin_forbidden:{module}")

def parse_admin_role(role_str: str) -> AdminRole:
    key = role_str.lower().replace(" ", "_")
    if key in PORTAL_ROLE_MAP:
        return PORTAL_ROLE_MAP[key]
    for role in AdminRole:
        if role.value == role_str or role.name.lower() == key:
            return role
    return AdminRole.READ_ONLY

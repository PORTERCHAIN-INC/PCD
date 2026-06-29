"""Map Porterchain admin roles → Fleetbase IAM roles/permissions."""

from porterchain_api.domain.admin_states import AdminRole

# Fleetbase uses Spatie permissions: "{extension} {action} {resource}"
FLEETBASE_CONSOLE_ROLES: frozenset[AdminRole] = frozenset(
    {
        AdminRole.SUPER_ADMIN,
        AdminRole.ADMIN,
        AdminRole.DISPATCHER,
        AdminRole.FLEET_MANAGER,
        AdminRole.SUPPORT,
        AdminRole.SUPPORT_LEAD,
    }
)

FLEETBASE_READ_ONLY_ROLES: frozenset[AdminRole] = frozenset(
    {AdminRole.SUPPORT, AdminRole.SUPPORT_LEAD, AdminRole.READ_ONLY}
)

ADMIN_TO_FLEETBASE_PERMISSIONS: dict[AdminRole, list[str]] = {
    AdminRole.SUPER_ADMIN: ["*"],
    AdminRole.ADMIN: [
        "fleet-ops * order",
        "fleet-ops * driver",
        "fleet-ops * vehicle",
        "fleet-ops * fleet",
        "fleet-ops dispatch order",
        "iam * user",
    ],
    AdminRole.DISPATCHER: [
        "fleet-ops list order",
        "fleet-ops view order",
        "fleet-ops update order",
        "fleet-ops dispatch order",
        "fleet-ops list driver",
        "fleet-ops view driver",
        "fleet-ops list vehicle",
        "fleet-ops view vehicle",
        "fleet-ops list fleet",
    ],
    AdminRole.FLEET_MANAGER: [
        "fleet-ops * driver",
        "fleet-ops * vehicle",
        "fleet-ops * fleet",
        "fleet-ops list order",
        "fleet-ops view order",
        "fleet-ops dispatch order",
    ],
    AdminRole.SUPPORT: [
        "fleet-ops list order",
        "fleet-ops view order",
        "fleet-ops list driver",
        "fleet-ops view driver",
    ],
    AdminRole.SUPPORT_LEAD: [
        "fleet-ops list order",
        "fleet-ops view order",
        "fleet-ops update order",
        "fleet-ops list driver",
        "fleet-ops view driver",
    ],
}


def can_access_fleetbase_console(admin_role: AdminRole) -> bool:
    return admin_role in FLEETBASE_CONSOLE_ROLES


def fleetbase_permissions_for_admin(admin_role: AdminRole) -> list[str]:
    return list(ADMIN_TO_FLEETBASE_PERMISSIONS.get(admin_role, []))

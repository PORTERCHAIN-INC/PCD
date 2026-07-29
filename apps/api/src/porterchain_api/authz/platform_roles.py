"""Platform (admin) role → SpiceDB relation mapping.

``MODULE_PERMISSIONS`` is the catalog of which AdminRole may touch which module.
It drives schema permission expansions and memory Checks — not Postgres ACL rows.
Live authorization is SpiceDB Check against those expansions.
"""

from __future__ import annotations

from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS
from porterchain_api.domain.admin_states import AdminRole

# Every staff role is a platform relation (replaces monolithic ``staff``).
PLATFORM_ROLE_RELATIONS: frozenset[str] = frozenset(r.value for r in AdminRole)

# Portal entry: any provisioned staff role.
PORTAL_ENTRY_ROLES: frozenset[str] = PLATFORM_ROLE_RELATIONS

# God-mode permission — super_admin only.
SYSTEM_ALL_ROLES: frozenset[str] = frozenset({AdminRole.SUPER_ADMIN.value})


def relation_for_admin_role(role: AdminRole | str) -> str:
    if isinstance(role, AdminRole):
        return role.value
    key = str(role).lower().replace(" ", "_")
    try:
        return AdminRole(key).value
    except ValueError:
        for r in AdminRole:
            if r.value == key or r.name.lower() == key:
                return r.value
        return AdminRole.READ_ONLY.value


def to_schema_permission(permission: str) -> str:
    """Map API/module permission names to SpiceDB schema permission names.

    SpiceDB rejects a permission that shares a name with a relation on the same
    definition. Role relations that also appear in MODULE_PERMISSIONS (finance,
    support) use ``mod_<name>`` in schema.zed. Legacy ``admin`` → ``portal``.
    """
    if permission == "admin":
        return "portal"
    if permission in ("system:all",):
        return "system_all"
    if permission.startswith("mod_"):
        return permission
    if permission in PLATFORM_ROLE_RELATIONS and permission in MODULE_PERMISSIONS:
        return f"mod_{permission}"
    return permission


def from_schema_permission(permission: str) -> str:
    """Inverse of ``to_schema_permission`` for MODULE_PERMISSIONS lookups."""
    if permission.startswith("mod_"):
        return permission[4:]
    if permission == "portal":
        return permission
    return permission


def roles_for_platform_permission(permission: str) -> frozenset[str]:
    """Which role relations satisfy a platform permission name."""
    schema_perm = to_schema_permission(permission)
    if schema_perm in ("portal",):
        return PORTAL_ENTRY_ROLES
    if schema_perm in ("system_all",):
        return SYSTEM_ALL_ROLES
    module = from_schema_permission(schema_perm)
    allowed = MODULE_PERMISSIONS.get(module)
    if allowed is None:
        return frozenset()
    return frozenset(r.value for r in allowed)


def all_platform_permission_names() -> frozenset[str]:
    names = {"portal", "admin", "system_all"}
    for key in MODULE_PERMISSIONS:
        names.add(to_schema_permission(key))
        names.add(key)
    return frozenset(names)

"""CurrentPrincipal — PorterChain authorization object (permissions from SpiceDB)."""

from __future__ import annotations

from dataclasses import dataclass, field

from porterchain_api.auth.unified_catalog import (
    AccountStatus,
    AssignableRole,
    ScopeType,
    UnifiedPermission,
)


@dataclass(frozen=True)
class RoleAssignmentView:
    role_key: str
    scope_type: str
    scope_id: str


@dataclass(frozen=True)
class CurrentPrincipal:
    """Request-scoped principal resolved from AuthenticatedIdentity + SpiceDB."""

    user_id: str  # porterchain_users.id (internal UUID)
    status: str
    onboarding_status: str
    email: str | None
    session_id: str | None
    default_workspace: str | None
    roles: frozenset[AssignableRole]
    role_assignments: tuple[RoleAssignmentView, ...] = ()
    permissions: frozenset[UnifiedPermission] = field(default_factory=frozenset)
    organization_ids: frozenset[str] = field(default_factory=frozenset)
    auth_subject: str | None = None
    auth_issuer: str | None = None
    auth_provider: str = "clerk"
    legacy_profile_ids: dict[str, str] = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE.value

    def has_permission(
        self,
        permission: UnifiedPermission | str,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
    ) -> bool:
        key = (
            permission
            if isinstance(permission, UnifiedPermission)
            else UnifiedPermission(permission)
        )
        if UnifiedPermission.SYSTEM_ALL in self.permissions:
            return True
        if key not in self.permissions:
            return False
        if scope_type is None:
            return True
        return self._assignment_covers_scope(scope_type, scope_id or "")

    def _assignment_covers_scope(self, scope_type: str, scope_id: str) -> bool:
        wanted = scope_type
        for a in self.role_assignments:
            if a.scope_type in ("global", "platform") and wanted in ("global", "platform", ""):
                return True
            if a.scope_type == wanted:
                if not scope_id or not a.scope_id or a.scope_id == scope_id:
                    return True
        return False

    def has_organization_scope(self, organization_id: str) -> bool:
        if UnifiedPermission.SYSTEM_ALL in self.permissions:
            return True
        if not organization_id:
            return False
        if organization_id in self.organization_ids:
            return True
        return any(
            a.scope_type == "organization" and a.scope_id == organization_id
            for a in self.role_assignments
        )

    def has_self_scope(self, profile_id: str) -> bool:
        if UnifiedPermission.SYSTEM_ALL in self.permissions:
            return True
        if not profile_id:
            return False
        return any(
            a.scope_type == "self" and (a.scope_id == profile_id or not a.scope_id)
            for a in self.role_assignments
        )

    def has_any_permission(self, *permissions: UnifiedPermission | str) -> bool:
        return any(self.has_permission(p) for p in permissions)

    def has_role(self, role: AssignableRole | str) -> bool:
        key = role if isinstance(role, AssignableRole) else AssignableRole(role)
        return key in self.roles

    def session_context(self) -> dict:
        """Safe payload for /session-context — no secrets."""
        from porterchain_api.auth.modules_catalog import modules_for_permissions

        return {
            "user_id": self.user_id,
            "status": self.status,
            "onboarding_status": self.onboarding_status,
            "default_workspace": self.default_workspace,
            "email": self.email,
            "roles": sorted(r.value for r in self.roles),
            "permissions": sorted(p.value for p in self.permissions),
            "modules": modules_for_permissions(self.permissions),
            "organization_ids": sorted(self.organization_ids),
            "role_assignments": [
                {
                    "role_key": a.role_key,
                    "scope_type": a.scope_type,
                    "scope_id": a.scope_id or None,
                }
                for a in self.role_assignments
            ],
            "workspaces": _workspaces_for(self),
            "legacy_profile_ids": dict(self.legacy_profile_ids),
            "auth": {
                "provider": self.auth_provider,
                "subject": self.auth_subject,
                "issuer": self.auth_issuer,
            },
        }


def _workspaces_for(principal: CurrentPrincipal) -> list[dict]:
    """Portal shells the user is actually provisioned for.

    Do **not** use ``has_permission`` here: ``SYSTEM_ALL`` would inflate merchant /
    driver / customer workspaces for every super_admin. Workspaces require the
    explicit portal permission (or SYSTEM_ALL / PLATFORM_ADMIN for admin only).
    """
    perms = principal.permissions
    workspaces: list[dict] = []
    if (
        UnifiedPermission.PLATFORM_ADMIN_ACCESS in perms
        or UnifiedPermission.SYSTEM_ALL in perms
    ):
        workspaces.append({"id": "admin", "label": "Admin", "kind": "platform"})
    if UnifiedPermission.MERCHANT_PORTAL_ACCESS in perms:
        for org_id in sorted(principal.organization_ids) or [""]:
            workspaces.append(
                {
                    "id": f"merchant:{org_id}" if org_id else "merchant",
                    "label": "Merchant",
                    "kind": "organization",
                    "organization_id": org_id or None,
                }
            )
    if UnifiedPermission.DRIVER_PORTAL_ACCESS in perms:
        workspaces.append({"id": "driver", "label": "Driver", "kind": "driver"})
    if UnifiedPermission.CUSTOMER_PORTAL_ACCESS in perms:
        workspaces.append({"id": "customer", "label": "Customer", "kind": "customer"})
    return workspaces


__all__ = [
    "RoleAssignmentView",
    "CurrentPrincipal",
    "ScopeType",
]

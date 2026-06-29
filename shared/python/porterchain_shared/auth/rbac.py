"""RBAC enforcement helpers."""

from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.auth.roles import Permission, PlatformRole


class RBACPolicy:
    """Declarative RBAC policy for route and service guards."""

    def __init__(self, required_permissions: frozenset[Permission] | None = None) -> None:
        self.required_permissions = required_permissions or frozenset()

    def check(self, principal: AuthPrincipal) -> bool:
        if not self.required_permissions:
            return True
        user_perms = principal.permissions()
        return self.required_permissions.issubset(user_perms)


def require_permission(principal: AuthPrincipal, permission: Permission) -> None:
    if not principal.can(permission):
        raise PermissionError(f"missing_permission:{permission.value}")


def require_any_role(principal: AuthPrincipal, *roles: PlatformRole) -> None:
    if not principal.has_any_role(*roles):
        raise PermissionError(f"missing_role:{','.join(r.value for r in roles)}")

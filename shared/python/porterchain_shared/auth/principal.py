"""Authenticated principal — supports multiple roles per user (Clerk JWT + metadata)."""

from dataclasses import dataclass, field

from porterchain_shared.auth.roles import Permission, PlatformRole, ROLE_PERMISSIONS
from porterchain_shared.types.user_types import UserType


@dataclass(frozen=True)
class AuthPrincipal:
    user_id: str
    user_type: UserType
    roles: frozenset[PlatformRole] = field(default_factory=frozenset)
    org_id: str | None = None
    email: str | None = None
    session_id: str | None = None

    def has_role(self, role: PlatformRole) -> bool:
        return role in self.roles

    def has_any_role(self, *roles: PlatformRole) -> bool:
        return bool(self.roles.intersection(roles))

    def permissions(self) -> frozenset[Permission]:
        perms: set[Permission] = set()
        for role in self.roles:
            perms.update(ROLE_PERMISSIONS.get(role, frozenset()))
        return frozenset(perms)

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions()

    @classmethod
    def visitor(cls, session_id: str | None = None) -> "AuthPrincipal":
        return cls(
            user_id="anonymous",
            user_type=UserType.VISITOR,
            roles=frozenset({PlatformRole.VISITOR}),
            session_id=session_id,
        )

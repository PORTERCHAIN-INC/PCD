"""Phase 3 leftovers removed — overrides lived in Postgres ACL tables (dropped)."""

from __future__ import annotations

from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.unified_catalog import (
    AccountStatus,
    AssignableRole,
    UnifiedPermission,
)


def test_current_principal_has_permission() -> None:
    principal = CurrentPrincipal(
        user_id="u1",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        email="a@x.com",
        session_id=None,
        default_workspace="admin",
        roles=frozenset({AssignableRole.SUPER_ADMIN}),
        permissions=frozenset({UnifiedPermission.SYSTEM_ALL}),
    )
    assert principal.has_permission(UnifiedPermission.PLATFORM_ADMIN_ACCESS)

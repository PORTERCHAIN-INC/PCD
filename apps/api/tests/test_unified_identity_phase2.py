"""Unified catalog labels — enums only; SpiceDB is authz SoT."""

from __future__ import annotations

from porterchain_api.auth.unified_catalog import (
    INVITE_ONLY_ROLES,
    AssignableRole,
    UnifiedPermission,
    admin_role_to_assignable,
    is_invite_only,
)
from porterchain_api.domain.admin_states import AdminRole


def test_assignable_roles_exist() -> None:
    assert AssignableRole.SUPER_ADMIN.value == "super_admin"
    assert AssignableRole.CUSTOMER.value == "customer"
    assert AssignableRole.DRIVER.value == "driver"


def test_invite_only_roles() -> None:
    assert is_invite_only(AssignableRole.SUPER_ADMIN)
    assert AssignableRole.SUPER_ADMIN in INVITE_ONLY_ROLES


def test_admin_role_map() -> None:
    assert admin_role_to_assignable(AdminRole.SUPER_ADMIN) == AssignableRole.SUPER_ADMIN


def test_permission_enum_labels() -> None:
    assert UnifiedPermission.PLATFORM_ADMIN_ACCESS.value
    assert UnifiedPermission.MERCHANT_PORTAL_ACCESS.value

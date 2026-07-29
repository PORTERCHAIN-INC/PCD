"""SpiceDB / Zanzibar authz unit tests (in-memory graph)."""

from __future__ import annotations

import pytest

from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.admin_models import AdminUser
from porterchain_api.authz.client import AuthzClient, Relationship, reset_authz_client
from porterchain_api.authz.tuples import PLATFORM_ID, TupleWriter
from porterchain_api.domain.admin_states import AdminRole


@pytest.fixture(autouse=True)
def _memory_authz(monkeypatch: pytest.MonkeyPatch):
    reset_authz_client()
    monkeypatch.setenv("SPICEDB_USE_MEMORY", "true")
    monkeypatch.setenv("SPICEDB_ENABLED", "false")
    yield
    reset_authz_client()


def test_platform_super_admin_portal_and_system_all() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-admin-1"
    client.write_relationships(
        [Relationship("platform", PLATFORM_ID, "super_admin", "user", uid)]
    )
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="portal",
        subject_id=uid,
    )
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="system_all",
        subject_id=uid,
    )
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="finance",
        subject_id=uid,
    )


def test_sales_cannot_access_finance_or_system_all() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-sales-1"
    client.write_relationships([Relationship("platform", PLATFORM_ID, "sales", "user", uid)])
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="portal",
        subject_id=uid,
    )
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="crm",
        subject_id=uid,
    )
    assert not client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="finance",
        subject_id=uid,
    )
    assert not client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="system_all",
        subject_id=uid,
    )
    assert not client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="settings",
        subject_id=uid,
    )


def test_require_module_does_not_bypass_via_portal_admin() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-sales-2"
    client.write_relationships([Relationship("platform", PLATFORM_ID, "sales", "user", uid)])
    reset_authz_client()
    # Force shared client to use this memory by patching get_authz_client
    from porterchain_api.authz import client as client_mod

    client_mod._client = client  # noqa: SLF001

    user = AdminUser(
        id="adm-1",
        clerk_user_id="clerk_sales",
        email="sales@example.com",
        name="Sales",
        role=AdminRole.SALES.value,
        is_active=True,
        porterchain_user_id=uid,
    )
    ctx = AdminContext(user=user, role=AdminRole.SALES)
    require_module(ctx, "crm")
    with pytest.raises(PermissionError, match="admin_forbidden:finance"):
        require_module(ctx, "finance")


def test_org_member_and_admin_permissions() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    org = "org-1"
    member = "user-member"
    admin = "user-admin"
    client.write_relationships(
        [
            Relationship("organization", org, "member", "user", member),
            Relationship("organization", org, "admin", "user", admin),
        ]
    )
    assert client.check(
        resource_type="organization",
        resource_id=org,
        permission="portal",
        subject_id=member,
    )
    assert not client.check(
        resource_type="organization",
        resource_id=org,
        permission="manage",
        subject_id=member,
    )
    assert client.check(
        resource_type="organization",
        resource_id=org,
        permission="manage",
        subject_id=admin,
    )


def test_tuple_writer_maps_admin_role_relation() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    writer = TupleWriter(client=client)
    writer.grant_platform_staff("u1", role="support")
    assert client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="support",
        subject_id="u1",
    )
    assert not client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="settings",
        subject_id="u1",
    )

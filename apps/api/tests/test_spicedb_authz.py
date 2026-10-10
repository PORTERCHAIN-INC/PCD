"""SpiceDB / Zanzibar authz unit tests (in-memory graph)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

    client_mod._client = client

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


def test_bulk_check_matches_serial_checks() -> None:
    from porterchain_api.authz.client import BulkCheckItem

    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-bulk-1"
    client.write_relationships(
        [
            Relationship("platform", PLATFORM_ID, "sales", "user", uid),
            Relationship("organization", "org-bulk", "ops", "user", uid),
        ]
    )
    items = [
        BulkCheckItem("platform", PLATFORM_ID, "portal", subject_id=uid),
        BulkCheckItem("platform", PLATFORM_ID, "crm", subject_id=uid),
        BulkCheckItem("platform", PLATFORM_ID, "finance", subject_id=uid),
        BulkCheckItem("organization", "org-bulk", "portal", subject_id=uid),
        BulkCheckItem("organization", "org-bulk", "manage", subject_id=uid),
    ]
    bulk = client.bulk_check(items)
    serial = [
        client.check(
            resource_type=i.resource_type,
            resource_id=i.resource_id,
            permission=i.permission,
            subject_id=i.subject_id,
        )
        for i in items
    ]
    assert bulk == serial == [True, True, False, True, False]


def test_seat_revoke_clears_nav_and_live_check_immediately() -> None:
    """P5.3: no Check-result cache — seat remove is visible on the next request."""
    from porterchain_api.auth.principal_resolution_service import (
        PrincipalResolutionService,
    )
    from porterchain_api.auth.unified_catalog import UnifiedPermission
    from porterchain_api.authz import client as client_mod

    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-seat-1"
    org = "org-seat-1"
    writer = TupleWriter(client=client)
    writer.grant_org_member(uid, org, role="ops")
    client_mod._client = client

    svc = PrincipalResolutionService()
    before = svc._permissions_from_spicedb(uid, {org})
    assert UnifiedPermission.MERCHANT_PORTAL_ACCESS in before
    assert client.check(
        resource_type="organization",
        resource_id=org,
        permission="portal",
        subject_id=uid,
    )

    writer.revoke_org_member(uid, org)

    assert not client.check(
        resource_type="organization",
        resource_id=org,
        permission="portal",
        subject_id=uid,
    )
    after = svc._permissions_from_spicedb(uid, {org})
    assert UnifiedPermission.MERCHANT_PORTAL_ACCESS not in after


def test_platform_role_revoke_blocks_require_module_immediately() -> None:
    """P5.3: live require_module fails as soon as the platform tuple is gone."""
    from porterchain_api.authz import client as client_mod

    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-staff-revoke"
    client.write_relationships(
        [Relationship("platform", PLATFORM_ID, "sales", "user", uid)]
    )
    client_mod._client = client

    user = AdminUser(
        id="adm-revoke",
        clerk_user_id="clerk_revoke",
        email="revoke@example.com",
        name="Revoke",
        role=AdminRole.SALES.value,
        is_active=True,
        porterchain_user_id=uid,
    )
    ctx = AdminContext(user=user, role=AdminRole.SALES)
    require_module(ctx, "crm")

    client.delete_relationships(
        [Relationship("platform", PLATFORM_ID, "sales", "user", uid)]
    )
    with pytest.raises(PermissionError, match="admin_forbidden:crm"):
        require_module(ctx, "crm")


def test_account_suspend_rejects_principal_without_ttl_wait() -> None:
    """P5.3: Postgres account suspend is a hard fail on the next resolve (no authz TTL)."""
    from fastapi import HTTPException

    from porterchain_api.auth.identity import AuthenticatedIdentity
    from porterchain_api.auth.principal_resolution_service import (
        PrincipalResolutionService,
    )
    from porterchain_api.auth.unified_catalog import AccountStatus, AuthProvider
    from porterchain_api.user_models import PorterchainUser

    user = PorterchainUser(
        id="u-susp-1",
        clerk_user_id="clerk_susp",
        email="susp@example.com",
        role="merchant_ops",
        status=AccountStatus.SUSPENDED.value,
    )
    identity = AuthenticatedIdentity(
        subject="clerk_susp",
        email="susp@example.com",
        issuer="https://example.clerk.accounts.dev",
        provider=AuthProvider.CLERK.value,
        session_id=None,
    )
    svc = PrincipalResolutionService()
    with patch.object(svc, "_resolve_user", return_value=user):
        with pytest.raises(HTTPException) as exc:
            svc.resolve(MagicMock(), identity)
    assert exc.value.status_code == 403
    assert exc.value.detail == "account_suspended"

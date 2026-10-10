"""P1 authz hardening: fail-closed scopes, revoke, single sync path, identity_link heal."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.dependencies import (
    assert_organization_scope,
    assert_self_scope,
)
from porterchain_api.auth.unified_catalog import (
    AccountStatus,
    AssignableRole,
    UnifiedPermission,
)
from porterchain_api.authz.client import AuthzClient, Relationship, reset_authz_client
from porterchain_api.authz.tuples import PLATFORM_ID, TupleWriter
from porterchain_api.user_models import PorterchainUser


@pytest.fixture(autouse=True)
def _memory_authz(monkeypatch: pytest.MonkeyPatch):
    reset_authz_client()
    monkeypatch.setenv("SPICEDB_USE_MEMORY", "true")
    monkeypatch.setenv("SPICEDB_ENABLED", "false")
    yield
    reset_authz_client()


def _principal(**kwargs) -> CurrentPrincipal:
    base = dict(
        user_id="u1",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        email="a@example.com",
        session_id=None,
        default_workspace=None,
        roles=frozenset({AssignableRole.MERCHANT_OPS}),
        permissions=frozenset({UnifiedPermission.MERCHANT_PORTAL_ACCESS}),
        organization_ids=frozenset({"org-a"}),
    )
    base.update(kwargs)
    return CurrentPrincipal(**base)


def test_assert_organization_scope_fail_closed_on_check_error() -> None:
    principal = _principal()
    db = MagicMock()
    with patch("porterchain_api.authz.client.get_authz_client") as get_client:
        client = MagicMock()
        client.check.side_effect = RuntimeError("spicedb_down")
        get_client.return_value = client
        with pytest.raises(HTTPException) as exc:
            assert_organization_scope(principal, "org-a", db)
        assert exc.value.status_code == 403
        assert exc.value.detail == "organization_scope_denied"


def test_assert_organization_scope_heals_stale_spicedb() -> None:
    principal = _principal()
    db = MagicMock()
    user = PorterchainUser(id="u1", clerk_user_id="user_x", email="a@example.com", role="merchant_owner")
    with (
        patch("porterchain_api.authz.client.get_authz_client") as get_client,
        patch("porterchain_api.authz.tuples.TupleWriter") as writer_cls,
        patch(
            "porterchain_api.auth.staff_identity.get_porterchain_user",
            return_value=user,
        ),
    ):
        client = MagicMock()
        client.check.side_effect = [False, True]
        get_client.return_value = client
        writer_cls.return_value.sync_user_from_profiles.return_value = "tok"
        assert_organization_scope(principal, "org-a", db)
        writer_cls.return_value.sync_user_from_profiles.assert_called_once_with(db, user)
        assert client.check.call_count == 2


def test_assert_self_scope_fail_closed_on_check_error() -> None:
    principal = _principal(
        roles=frozenset({AssignableRole.DRIVER}),
        permissions=frozenset({UnifiedPermission.DRIVER_PORTAL_ACCESS}),
        organization_ids=frozenset(),
    )
    db = MagicMock()
    with patch("porterchain_api.authz.client.get_authz_client") as get_client:
        client = MagicMock()
        client.bulk_check.side_effect = RuntimeError("spicedb_down")
        get_client.return_value = client
        with pytest.raises(HTTPException) as exc:
            assert_self_scope(principal, "drv-1", db)
        assert exc.value.status_code == 403


def test_revoke_all_for_user_clears_memory_graph() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-revoke-1"
    client.write_relationships(
        [
            Relationship("platform", PLATFORM_ID, "sales", "user", uid),
            Relationship("organization", "org-1", "member", "user", uid),
        ]
    )
    writer = TupleWriter(client=client)
    user = PorterchainUser(id=uid, clerk_user_id="clerk_x", email="x@example.com", role="sales")
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.first.return_value = None
    writer.revoke_all_for_user(db, user)
    assert not client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="crm",
        subject_id=uid,
    )


def test_user_sync_identity_link_points_at_porterchain_user(db) -> None:
    """After sync, IdentityLink.platform_user_id must be porterchain_users.id."""
    import uuid

    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.user_sync_service import UserSyncService
    from porterchain_api.identity_models import IdentityLink

    clerk_id = f"clerk_link_{uuid.uuid4().hex[:12]}"
    email = f"link_{uuid.uuid4().hex[:8]}@example.com"
    admin = AdminUser(
        clerk_user_id=clerk_id,
        email=email,
        name="Link",
        role="sales",
        is_active=True,
    )
    db.add(admin)
    db.commit()

    claims = ClerkClaims(
        clerk_user_id=clerk_id,
        email=email,
        issuer="https://example.clerk.accounts.dev",
    )
    user = UserSyncService().sync(db, claims)
    link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == clerk_id).one()
    assert link.platform_user_id == user.id
    assert link.platform_user_id != admin.id

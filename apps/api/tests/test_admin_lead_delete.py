"""Admin lead delete — super_admin (system_all) only."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser
from porterchain_api.authz.client import AuthzClient, Relationship, reset_authz_client
from porterchain_api.authz.tuples import PLATFORM_ID
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.routers.admin import leads as leads_mod


@pytest.fixture(autouse=True)
def _memory_authz(monkeypatch: pytest.MonkeyPatch):
    reset_authz_client()
    monkeypatch.setenv("SPICEDB_USE_MEMORY", "true")
    monkeypatch.setenv("SPICEDB_ENABLED", "false")
    yield
    reset_authz_client()


def _bind_authz(client: AuthzClient) -> None:
    from porterchain_api.authz import client as client_mod

    reset_authz_client()
    client_mod._client = client


def _admin_ctx(*, role: AdminRole, uid: str) -> AdminContext:
    suffix = uuid4().hex[:8]
    user = AdminUser(
        id=f"adm-{suffix}",
        clerk_user_id=f"clerk_{suffix}",
        email=f"{role.value}-{suffix}@test.local",
        name=role.value,
        role=role.value,
        is_active=True,
        porterchain_user_id=uid,
    )
    return AdminContext(user=user, role=role)


def test_delete_lead_forbidden_for_sales(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = f"user-sales-{uuid4().hex[:8]}"
    client.write_relationships([Relationship("platform", PLATFORM_ID, "sales", "user", uid)])
    _bind_authz(client)

    delete_mock = MagicMock()
    monkeypatch.setattr(leads_mod._crm, "delete_lead", delete_mock)

    ctx = _admin_ctx(role=AdminRole.SALES, uid=uid)
    with pytest.raises(HTTPException) as exc_info:
        leads_mod.delete_lead(lead_id="lead-1", ctx=ctx, db=MagicMock())
    assert exc_info.value.status_code == 403
    delete_mock.assert_not_called()


def test_delete_lead_super_admin_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = f"user-sa-{uuid4().hex[:8]}"
    client.write_relationships(
        [Relationship("platform", PLATFORM_ID, "super_admin", "user", uid)]
    )
    _bind_authz(client)

    delete_mock = MagicMock()
    monkeypatch.setattr(leads_mod._crm, "delete_lead", delete_mock)

    ctx = _admin_ctx(role=AdminRole.SUPER_ADMIN, uid=uid)
    assert leads_mod.delete_lead(lead_id="lead-1", ctx=ctx, db=MagicMock()) is None
    delete_mock.assert_called_once()
    assert delete_mock.call_args.args[1] == "lead-1"


def test_delete_lead_missing_is_404(monkeypatch: pytest.MonkeyPatch) -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = f"user-sa-{uuid4().hex[:8]}"
    client.write_relationships(
        [Relationship("platform", PLATFORM_ID, "super_admin", "user", uid)]
    )
    _bind_authz(client)

    def _raise(_db, _lead_id: str) -> None:
        raise LookupError("lead_not_found")

    monkeypatch.setattr(leads_mod._crm, "delete_lead", _raise)

    ctx = _admin_ctx(role=AdminRole.SUPER_ADMIN, uid=uid)
    with pytest.raises(HTTPException) as exc_info:
        leads_mod.delete_lead(lead_id="missing-lead-id", ctx=ctx, db=MagicMock())
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "lead_not_found"

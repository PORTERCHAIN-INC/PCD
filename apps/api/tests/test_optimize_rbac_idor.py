"""Optimize endpoints — RBAC (dispatch / dispatch_read) + driver IDOR.

Maps to docs/ROUTE_OPTIMIZATION_DEV_TEST_CASES.md AUTH-*/API-A-011 / API-D-006.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from porterchain_driver.jobs import JobsService

from porterchain_api.admin_engine.rbac import AdminContext, require_module
from porterchain_api.admin_models import AdminUser
from porterchain_api.authz.client import AuthzClient, Relationship, reset_authz_client
from porterchain_api.authz.tuples import PLATFORM_ID
from porterchain_api.dispatch_engine.optimize_events import assert_driver_scoped
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.routers import operations as ops_router
from porterchain_api.schemas_admin import OptimizeCommitBody, OptimizeRunBody


@pytest.fixture(autouse=True)
def _memory_authz(monkeypatch: pytest.MonkeyPatch):
    reset_authz_client()
    monkeypatch.setenv("SPICEDB_USE_MEMORY", "true")
    monkeypatch.setenv("SPICEDB_ENABLED", "false")
    yield
    reset_authz_client()


def _ctx(role: AdminRole, uid: str, *, porterchain_user_id: str) -> AdminContext:
    user = AdminUser(
        id=uid,
        clerk_user_id=f"clerk_{uid}",
        email=f"{uid}@example.com",
        name=role.value,
        role=role.value,
        is_active=True,
        porterchain_user_id=porterchain_user_id,
    )
    return AdminContext(user=user, role=role)


def _bind_client(client: AuthzClient) -> None:
    from porterchain_api.authz import client as client_mod

    client_mod._client = client


def test_sales_forbidden_on_dispatch_and_dispatch_read() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-sales-opt"
    client.write_relationships([Relationship("platform", PLATFORM_ID, "sales", "user", uid)])
    _bind_client(client)
    ctx = _ctx(AdminRole.SALES, "adm-sales", porterchain_user_id=uid)
    with pytest.raises(PermissionError, match="admin_forbidden:dispatch_read"):
        require_module(ctx, "dispatch_read")
    with pytest.raises(PermissionError, match="admin_forbidden:dispatch"):
        require_module(ctx, "dispatch")


def test_support_can_read_optimize_pool_not_run() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-support-opt"
    client.write_relationships([Relationship("platform", PLATFORM_ID, "support", "user", uid)])
    _bind_client(client)
    ctx = _ctx(AdminRole.SUPPORT, "adm-support", porterchain_user_id=uid)
    require_module(ctx, "dispatch_read")
    with pytest.raises(PermissionError, match="admin_forbidden:dispatch"):
        require_module(ctx, "dispatch")


def test_dispatcher_can_read_and_mutate_optimize() -> None:
    client = AuthzClient(
        enabled=False, required=False, endpoint="", preshared_key="", use_memory=True
    )
    uid = "user-disp-opt"
    client.write_relationships(
        [Relationship("platform", PLATFORM_ID, "dispatcher", "user", uid)]
    )
    _bind_client(client)
    ctx = _ctx(AdminRole.DISPATCHER, "adm-disp", porterchain_user_id=uid)
    require_module(ctx, "dispatch_read")
    require_module(ctx, "dispatch")


def test_optimize_pool_router_maps_forbidden_to_403() -> None:
    ctx = _ctx(AdminRole.SALES, "adm-x", porterchain_user_id="u-x")
    with patch.object(
        ops_router,
        "require_module",
        side_effect=PermissionError("admin_forbidden:dispatch_read"),
    ), pytest.raises(HTTPException) as excinfo:
        ops_router.optimize_pool(ctx, MagicMock())
    assert excinfo.value.status_code == 403
    assert "dispatch_read" in str(excinfo.value.detail)


def test_optimize_run_router_requires_dispatch_not_read() -> None:
    ctx = _ctx(AdminRole.SUPPORT, "adm-s", porterchain_user_id="u-s")
    body = OptimizeRunBody(mode="allocate", engine="vroom")
    with patch.object(
        ops_router,
        "require_module",
        side_effect=PermissionError("admin_forbidden:dispatch"),
    ), pytest.raises(HTTPException) as excinfo:
        ops_router.optimize_run(body, ctx, MagicMock())
    assert excinfo.value.status_code == 403
    assert "dispatch" in str(excinfo.value.detail)


def test_optimize_commit_router_requires_dispatch() -> None:
    ctx = _ctx(AdminRole.SUPPORT, "adm-s2", porterchain_user_id="u-s2")
    body = OptimizeCommitBody(assignments=[{"order_id": "o1"}], run_id="run-1")
    with patch.object(
        ops_router,
        "require_module",
        side_effect=PermissionError("admin_forbidden:dispatch"),
    ), pytest.raises(HTTPException) as excinfo:
        ops_router.optimize_commit(body, ctx, MagicMock())
    assert excinfo.value.status_code == 403


def test_driver_cannot_poll_another_drivers_optimize_run() -> None:
    svc = JobsService()
    driver_b = SimpleNamespace(id="drv-b")
    rec = {
        "run_id": "run-a",
        "status": "ready",
        "pc_driver_id": "drv-a",
        "assignments": [{"order_id": "o1", "sequence": 1}],
        "metrics": {},
    }
    with patch(
        "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService.get_run",
        return_value=rec,
    ):
        with pytest.raises(LookupError, match="optimize_run_not_found"):
            svc.optimize_run_status(MagicMock(), driver_b, "run-a")


def test_driver_can_poll_own_optimize_run() -> None:
    svc = JobsService()
    driver = SimpleNamespace(id="drv-a")
    rec = {
        "run_id": "run-a",
        "status": "ready",
        "pc_driver_id": "drv-a",
        "assignments": [{"order_id": "o1", "sequence": 1}],
        "metrics": {},
        "apply_on_ready": False,
    }
    with (
        patch(
            "porterchain_api.admin_engine.orchestrator_ops_service.OrchestratorOpsService.get_run",
            return_value=rec,
        ),
        patch("porterchain_driver.sequence_store.read_sequence", return_value=None),
        patch("porterchain_driver.sequence_store.apply_run_to_driver") as apply,
        patch.object(svc, "list_jobs", return_value={"jobs": []}),
        patch.object(
            svc,
            "plan_from_run",
            return_value={"status": "ready", "run_id": "run-a", "applied": False},
        ),
    ):
        out = svc.optimize_run_status(MagicMock(), driver, "run-a", apply=False)
    apply.assert_not_called()
    assert out["status"] == "ready"


def test_assert_driver_scoped_rejects_foreign_orders() -> None:
    with pytest.raises(AssertionError, match="cross_driver_order_ids"):
        assert_driver_scoped(["ord-1"], ["ord-1", "ord-other"], engine="vroom")


def test_unlinked_admin_user_forbidden() -> None:
    user = AdminUser(
        id="adm-nolink",
        clerk_user_id="clerk_nolink",
        email="nolink@example.com",
        name="No Link",
        role=AdminRole.ADMIN.value,
        is_active=True,
        porterchain_user_id=None,
    )
    ctx = AdminContext(user=user, role=AdminRole.ADMIN)
    with pytest.raises(PermissionError, match="unlinked_user"):
        require_module(ctx, "dispatch")

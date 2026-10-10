"""P0 driver + admin-driver catalog cases (dev suite).

Covers AUTH/API/policy gaps from docs/DRIVER_ADMIN_DEV_TEST_CASES.md:
lifecycle, assigned-order guard, identity never auto-APPROVE, dev-login gate,
no PorterChain VROOM client, admin action channel stubs.
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings, get_settings
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.api_service import DriverApiService
from porterchain_api.driver_engine.verification_service import DriverVerificationService
from porterchain_api.main import app

pytestmark = pytest.mark.driver_p0


# ── Helpers ──────────────────────────────────────────────────────────────


def _admin_ctx() -> SimpleNamespace:
    return SimpleNamespace(user=SimpleNamespace(id="admin-p0"))


def _mock_driver(**kwargs) -> SimpleNamespace:
    base = dict(
        id="d-p0",
        status=DriverStatus.PENDING.value,
        clerk_user_id="user_d_p0",
        vehicles=[],
        fleetbase_driver_id=None,
        is_online=True,
        availability="idle",
        email="driver-p0@test.porterchain.com",
        phone="+14165550100",
        full_name="P0 Driver",
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def _lifecycle_svc(driver: SimpleNamespace):
    from porterchain_api.admin_engine.driver_service import AdminDriverService

    svc = AdminDriverService()
    svc._get_or_raise = MagicMock(return_value=driver)  # type: ignore[method-assign]
    svc._audit = MagicMock()  # type: ignore[method-assign]
    svc._fleetbase = MagicMock()
    return svc


# ── Admin lifecycle (API-A-02) ───────────────────────────────────────────


def test_suspend_driver_sets_offline_and_suspended() -> None:
    driver = _mock_driver(status=DriverStatus.APPROVED.value, is_online=True)
    svc = _lifecycle_svc(driver)
    db = MagicMock()

    with patch("porterchain_api.admin_engine.driver_service.emit_event"), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out, warning = svc.suspend_driver(db, _admin_ctx(), "d-p0", None)

    assert out.status == DriverStatus.SUSPENDED.value
    assert out.is_online is False
    assert warning is None


def test_deactivate_is_suspend_alias() -> None:
    driver = _mock_driver(status=DriverStatus.APPROVED.value)
    svc = _lifecycle_svc(driver)
    db = MagicMock()

    with patch("porterchain_api.admin_engine.driver_service.emit_event"), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out, _ = svc.deactivate_driver(db, _admin_ctx(), "d-p0", None)

    assert out.status == DriverStatus.SUSPENDED.value


def test_reject_driver_bars_from_pool() -> None:
    driver = _mock_driver(status=DriverStatus.PENDING.value, is_online=True)
    svc = _lifecycle_svc(driver)
    db = MagicMock()

    with patch("porterchain_api.admin_engine.driver_service.emit_event"), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out, _ = svc.reject_driver(db, _admin_ctx(), "d-p0", None)

    assert out.status == DriverStatus.REJECTED.value
    assert out.is_online is False
    assert out.availability == "offline"


def test_rehire_moves_rejected_to_pending() -> None:
    driver = _mock_driver(status=DriverStatus.REJECTED.value)
    svc = _lifecycle_svc(driver)
    db = MagicMock()

    with patch("porterchain_api.admin_engine.driver_service.emit_event"), patch(
        "porterchain_api.auth.authz_sync.sync_authz_after_persona_mutation",
    ):
        out = svc.rehire_driver(db, _admin_ctx(), "d-p0")

    assert out.status == DriverStatus.PENDING.value
    assert out.is_online is False


def test_rehire_rejects_approved() -> None:
    driver = _mock_driver(status=DriverStatus.APPROVED.value)
    svc = _lifecycle_svc(driver)
    db = MagicMock()

    with pytest.raises(ValueError, match="driver_not_rehirable"):
        svc.rehire_driver(db, _admin_ctx(), "d-p0")


# ── Policy: identity never auto-APPROVE (ARCH-06) ────────────────────────


def test_identity_verified_does_not_auto_approve(db: Session) -> None:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"p0-ident-{suffix}@test.porterchain.com",
        full_name=f"P0 Ident {suffix}",
        status=DriverStatus.PENDING.value,
        clerk_user_id=f"clerk_p0_ident_{suffix}",
        license_verified=False,
        documents={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    DriverVerificationService().apply_identity_session(
        db,
        row,
        session_id="vs_p0",
        verified=True,
        status="verified",
        document_summary={"type": "driving_license", "number": "P01234"},
    )
    db.commit()
    db.refresh(row)

    assert row.license_verified is True
    assert row.status == DriverStatus.PENDING.value


# ── Assigned-order guard (API-D-02) ──────────────────────────────────────


def test_require_assigned_order_allows_own() -> None:
    db = MagicMock()
    order = SimpleNamespace(id="ord-own", assigned_driver_id="driver-a")
    db.get = MagicMock(return_value=order)

    out = DriverApiService.require_assigned_order(db, driver_id="driver-a", order_id="ord-own")
    assert out.id == "ord-own"


def test_require_assigned_order_allows_unassigned() -> None:
    """Unassigned orders are loadable (assignment may land after fetch)."""
    db = MagicMock()
    order = SimpleNamespace(id="ord-open", assigned_driver_id=None)
    db.get = MagicMock(return_value=order)

    out = DriverApiService.require_assigned_order(db, driver_id="driver-a", order_id="ord-open")
    assert out.id == "ord-open"


def test_require_assigned_order_rejects_other_driver() -> None:
    db = MagicMock()
    order = SimpleNamespace(id="ord-1", assigned_driver_id="driver-a")
    db.get = MagicMock(return_value=order)

    with pytest.raises(PermissionError, match="not_assigned_driver"):
        DriverApiService.require_assigned_order(db, driver_id="driver-b", order_id="ord-1")


def test_require_assigned_order_missing() -> None:
    db = MagicMock()
    db.get = MagicMock(return_value=None)

    with pytest.raises(LookupError, match="order_not_found"):
        DriverApiService.require_assigned_order(db, driver_id="d1", order_id="missing")


# ── Dev login gate (AUTH-03) ─────────────────────────────────────────────


def test_allow_auth_dev_bypass_only_in_development() -> None:
    from porterchain_api.auth.dev import allow_auth_dev_bypass

    local = SimpleNamespace(app_env="local", clerk_dev_bypass=True)
    prod = SimpleNamespace(app_env="production", clerk_dev_bypass=True)
    local_off = SimpleNamespace(app_env="local", clerk_dev_bypass=False)
    staging = SimpleNamespace(app_env="staging", clerk_dev_bypass=True)

    assert allow_auth_dev_bypass(local) is True  # type: ignore[arg-type]
    assert allow_auth_dev_bypass(prod) is False  # type: ignore[arg-type]
    assert allow_auth_dev_bypass(local_off) is False  # type: ignore[arg-type]
    assert allow_auth_dev_bypass(staging) is False  # type: ignore[arg-type]


def test_dev_login_404_when_bypass_disabled() -> None:
    """Dev picker must 404 when bypass is off (even in local)."""
    settings = Settings(
        app_env="local",
        clerk_dev_bypass=False,
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        r = client.post("/driver-api/v1/auth/dev-login", json={"email": "x@y.com"})
        assert r.status_code == 404
        assert r.json()["detail"] == "not_found"
        r2 = client.get("/driver-api/v1/auth/dev-drivers")
        assert r2.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_get_driver_context_suspended_403(db: Session) -> None:
    from porterchain_api.auth.driver import get_driver_context

    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"p0-sus-{suffix}@test.porterchain.com",
        full_name=f"P0 Sus {suffix}",
        status=DriverStatus.SUSPENDED.value,
        clerk_user_id=f"clerk_p0_sus_{suffix}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    bypass_settings = Settings(
        app_env="local",
        clerk_dev_bypass=True,
        stripe_mock=True,
        jwt_secret="test-jwt-secret-local",
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
    )

    async def _run() -> None:
        with pytest.raises(HTTPException) as ei:
            await get_driver_context(
                db=db,
                settings=bypass_settings,
                credentials=None,
                x_driver_id=row.id,
            )
        assert ei.value.status_code == 403
        assert ei.value.detail == "driver_suspended"

    asyncio.run(_run())


# ── Admin action stubs (API-A-03) ────────────────────────────────────────


def test_admin_driver_action_rejects_unimplemented() -> None:
    from porterchain_api.auth.driver_admin_action import run_admin_driver_action

    db = MagicMock()
    driver = _mock_driver()
    with pytest.raises(NotImplementedError, match="request_documents_not_implemented"):
        run_admin_driver_action(db, driver, "request_documents", None)
    with pytest.raises(NotImplementedError, match="reset_password_not_implemented"):
        run_admin_driver_action(db, driver, "reset_password", None)


# ── Architecture: no PC VROOM client (FB-04) ─────────────────────────────


def test_no_porterchain_vroom_client_in_api() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "porterchain_api"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "vroom" not in text.lower():
            continue
        # Allow comments / docs / intentional skip strings mentioning VROOM
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = ""
                if isinstance(node, ast.Import):
                    mod = ",".join(a.name for a in node.names)
                else:
                    mod = node.module or ""
                if "vroom" in mod.lower():
                    offenders.append(f"{path.relative_to(root)}:{getattr(node, 'lineno', '?')}:{mod}")
            if isinstance(node, ast.Call):
                # ban httpx/requests to a host containing 'vroom'
                pass
    assert not offenders, f"PorterChain VROOM client imports found: {offenders}"


def test_driver_api_openapi_has_core_p0_paths() -> None:
    paths = set(app.openapi().get("paths", {}))
    required = {
        "/driver-api/v1/me",
        "/driver-api/v1/jobs",
        "/driver-api/v1/navigation/session",
        "/driver-api/v1/location",
        "/driver-api/v1/push/register",
        "/driver-api/v1/offline/sync",
        "/v1/admin/drivers",
        "/v1/admin/drivers/{driver_id}/approve",
        "/v1/admin/drivers/{driver_id}/suspend",
        "/v1/admin/drivers/{driver_id}/invite",
        "/v1/admin/drivers/{driver_id}/action",
    }
    missing = sorted(p for p in required if p not in paths)
    assert not missing, f"missing OpenAPI paths: {missing}"


def test_me_mapper_not_shadowed_by_profile_route() -> None:
    """Regression: route `def driver_profile` must not shadow mapper used by GET /me."""
    import importlib

    from porterchain_api.routers.driver import profile as profile_mod

    importlib.reload(profile_mod)
    assert profile_mod.map_driver_profile.__module__.endswith("driver_engine.mappers")
    # Callable accepts wallet_cents kwarg (route handler does not).
    import inspect

    sig = inspect.signature(profile_mod.map_driver_profile)
    assert "wallet_cents" in sig.parameters

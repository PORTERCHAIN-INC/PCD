"""P0 handshake regressions — FCM/WS principal + Fleetbase SSO fail-closed.

Maps to docs/AUTHENTICATION_DRIVER_ADMIN_DEV_TEST_MATRIX.md §6–7:
HS-FCM-001/003/004/007 · HS-FB-002/003/004.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.sso_service import SsoService
from porterchain_api.auth.unified_catalog import AccountStatus, AssignableRole, UnifiedPermission
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.notification_engine.principal import (
    get_notification_user,
    resolve_notification_ws_user,
)
from porterchain_api.schemas_driver import PushRegisterRequest


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "a" * 32,
        "sso_jwt_secret": "b" * 32,
        "spicedb_enabled": False,
        "spicedb_use_memory": True,
        "spicedb_required": False,
        "stripe_mock": True,
        "fleetbase_sso_enabled": False,
        "fleetbase_api_url": "http://localhost:8000",
        "fleetbase_api_key": "test",
        "fleetbase_console_url": "",
        "fleetbase_default_company_uuid": "co-test",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _current(**kwargs) -> CurrentPrincipal:
    base = dict(
        user_id="pc-user-1",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        email="ops@porterchain.com",
        session_id="sid",
        default_workspace="admin",
        roles=frozenset({AssignableRole.ADMIN}),
        permissions=frozenset({UnifiedPermission.PLATFORM_ADMIN_ACCESS}),
        organization_ids=frozenset(),
        auth_subject="staff:admin-1",
        auth_provider="staff_idp",
        legacy_profile_ids={"admin_user_id": "admin-1"},
    )
    base.update(kwargs)
    return CurrentPrincipal(**base)


# ── HS-FCM — notification principal / WS ─────────────────────────────────────


def test_hs_fcm_003_notification_user_requires_credentials() -> None:
    async def _run() -> None:
        with pytest.raises(HTTPException) as exc:
            await get_notification_user(
                db=MagicMock(),
                settings=_settings(),
                credentials=None,
                x_merchant_id=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "authentication_required"

    asyncio.run(_run())


def test_hs_fcm_007_garbage_token_does_not_authenticate() -> None:
    """Firebase/FCM tokens must never authorize notification APIs."""

    async def _run() -> None:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fcm-device-token-xyz")
        with (
            patch(
                "porterchain_api.notification_engine.principal._resolve_staff_notification_user",
                return_value=None,
            ),
            patch(
                "porterchain_api.auth.driver._driver_id_from_token",
                side_effect=HTTPException(status_code=401, detail="invalid_driver_token"),
            ),
            patch(
                "porterchain_api.auth.clerk.verify_clerk_token",
                new_callable=AsyncMock,
                side_effect=ValueError("not jwt"),
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_notification_user(
                    db=MagicMock(),
                    settings=_settings(),
                    credentials=creds,
                    x_merchant_id=None,
                )
            assert exc.value.status_code == 401
            assert exc.value.detail == "authentication_required"

    asyncio.run(_run())


def test_hs_fcm_004_ws_empty_token_returns_none() -> None:
    async def _run() -> None:
        assert await resolve_notification_ws_user("") is None
        assert await resolve_notification_ws_user("   ".strip()) is None

    asyncio.run(_run())


def test_hs_fcm_004_ws_bad_token_returns_none_not_raise() -> None:
    async def _run() -> None:
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        with (
            patch("porterchain_api.db.SessionLocal", return_value=mock_db),
            patch("porterchain_api.config.get_settings", return_value=_settings()),
            patch(
                "porterchain_api.notification_engine.principal._resolve_staff_notification_user",
                return_value=None,
            ),
            patch(
                "porterchain_api.auth.driver._driver_id_from_token",
                side_effect=ValueError("bad"),
            ),
            patch(
                "porterchain_api.auth.clerk.verify_clerk_token",
                new_callable=AsyncMock,
                side_effect=ValueError("bad"),
            ),
        ):
            assert await resolve_notification_ws_user("eyJhbGciOi.fake") is None

    asyncio.run(_run())


def test_hs_fcm_001_register_push_requires_driver_context_dependency() -> None:
    """Route is wired to get_driver_context — unauthenticated callers never reach FCM store."""
    from porterchain_api.auth.driver import get_driver_context
    from porterchain_api.routers.driver import communications as comms

    deps = comms.register_push.__annotations__
    # FastAPI Annotated dependency is on the ctx parameter default
    assert comms.register_push.__name__ == "register_push"
    sig_default = comms.register_push.__defaults__
    assert get_driver_context is not None
    # Inspect Depends in signature via __kwdefaults__ / annotations string
    import inspect

    params = inspect.signature(comms.register_push).parameters
    ctx = params["ctx"]
    assert "get_driver_context" in str(ctx.annotation) or "DriverContext" in str(ctx.annotation)


def test_hs_fcm_001_register_push_invalid_token_400() -> None:
    from porterchain_api.driver_engine.rbac import DriverContext
    from porterchain_api.notification_engine.device_service import InvalidFcmToken
    from porterchain_api.routers.driver.communications import register_push

    driver = MagicMock()
    driver.id = "drv-1"
    ctx = DriverContext(driver=driver)
    body = PushRegisterRequest(device_token="bad", platform="web")
    db = MagicMock()

    with (
        patch("porterchain_api.routers.driver.communications.db_transaction"),
        patch("porterchain_api.routers.driver.communications.svc") as svc,
    ):
        svc.platform.push.register_device.side_effect = InvalidFcmToken("nope")
        with pytest.raises(HTTPException) as exc:
            register_push(body, ctx, db)
        assert exc.value.status_code == 400
        assert exc.value.detail == "fcm_token_invalid"


# ── HS-FB — Fleetbase SSO fail-closed ────────────────────────────────────────


def test_hs_fb_004_sso_disabled_raises() -> None:
    with pytest.raises(ValueError, match="fleetbase_sso_disabled"):
        SsoService().exchange_fleetbase_session_for_principal(
            MagicMock(),
            _settings(fleetbase_sso_enabled=False),
            _current(),
        )


def test_hs_fb_002_sso_forbidden_without_admin_principal() -> None:
    db = MagicMock()
    with patch.object(SsoService, "auth_principal_from_current", return_value=None):
        with pytest.raises(PermissionError, match="fleetbase_console_forbidden"):
            SsoService().exchange_fleetbase_session_for_principal(
                db,
                _settings(fleetbase_sso_enabled=True),
                _current(),
            )


def test_hs_fb_002_sso_forbidden_for_read_only_admin() -> None:
    """READ_ONLY is not in FLEETBASE_CONSOLE_ROLES."""
    from porterchain_shared.auth.principal import AuthPrincipal
    from porterchain_shared.auth.roles import PlatformRole
    from porterchain_shared.types.user_types import UserType

    admin = MagicMock()
    admin.id = "admin-1"
    admin.role = AdminRole.READ_ONLY.value
    admin.is_active = True
    admin.email = "ro@porterchain.com"
    admin.clerk_user_id = None

    principal = AuthPrincipal(
        user_id="admin-1",
        user_type=UserType.ADMIN,
        roles=frozenset({PlatformRole.OPERATIONS}),
        org_id=None,
        email="ro@porterchain.com",
        session_id="sid",
    )
    db = MagicMock()
    with (
        patch.object(SsoService, "auth_principal_from_current", return_value=principal),
        patch(
            "porterchain_api.auth.sso_service.get_admin_user",
            return_value=admin,
        ),
    ):
        with pytest.raises(PermissionError, match="fleetbase_console_forbidden"):
            SsoService().exchange_fleetbase_session_for_principal(
                db,
                _settings(fleetbase_sso_enabled=True),
                _current(),
            )


def test_hs_fb_003_sso_issues_token_when_fleetbase_exchange_down() -> None:
    """Bridge down must not block SSO JWT mint — fail soft on Fleetbase HTTP only."""
    from porterchain_shared.auth.principal import AuthPrincipal
    from porterchain_shared.auth.roles import PlatformRole
    from porterchain_shared.types.user_types import UserType

    admin = MagicMock()
    admin.id = "admin-1"
    admin.role = AdminRole.ADMIN.value
    admin.is_active = True
    admin.email = "ops@porterchain.com"
    admin.clerk_user_id = None
    admin.fleetbase_user_uuid = None

    principal = AuthPrincipal(
        user_id="admin-1",
        user_type=UserType.ADMIN,
        roles=frozenset({PlatformRole.ADMIN}),
        org_id=None,
        email="ops@porterchain.com",
        session_id="sid",
    )
    link = MagicMock()
    link.fleetbase_permissions = []
    link.fleetbase_roles = []
    link.fleetbase_user_uuid = None

    db = MagicMock()
    settings = _settings(fleetbase_sso_enabled=True)

    with (
        patch.object(SsoService, "auth_principal_from_current", return_value=principal),
        patch("porterchain_api.auth.sso_service.get_admin_user", return_value=admin),
        patch.object(SsoService, "_upsert_identity_link", return_value=link),
        patch(
            "porterchain_fleetbase_adapter.auth.FleetbaseSsoClient.exchange_sso_token",
            side_effect=RuntimeError("bridge_down"),
        ),
    ):
        out = SsoService().exchange_fleetbase_session_for_principal(db, settings, _current())

    assert out["sso_token"]
    assert out["console_url"] == ""
    assert out["fleetbase_session"] is None

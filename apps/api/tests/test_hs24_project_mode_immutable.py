"""HS-24 — POST /v1/admin/settings/project-mode always 403 project_mode_immutable."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import Settings, get_settings
from porterchain_api.main import app
from porterchain_api.routers.admin.settings import settings_project_mode_change


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "b" * 48,
        "database_url": "postgresql+psycopg://u:p@h/d",
        "stripe_mock": True,
        "stripe_secret": "",
        "clerk_unified_mode": False,
        "clerk_secret_key": "",
        "clerk_publishable_key": "",
        "clerk_jwks_url": "",
        "clerk_customer_secret_key": "",
        "clerk_customer_publishable_key": "",
        "clerk_customer_jwks_url": "",
        "clerk_merchant_secret_key": "",
        "clerk_merchant_publishable_key": "",
        "clerk_merchant_jwks_url": "",
        "clerk_admin_secret_key": "",
        "clerk_admin_publishable_key": "",
        "clerk_admin_jwks_url": "",
        "clerk_driver_secret_key": "",
        "clerk_driver_publishable_key": "",
        "clerk_driver_jwks_url": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_hs24_project_mode_endpoint_always_403() -> None:
    """In-process flip is intentional-skip — change via pnpm mode:set / Doppler + restart."""
    with patch("porterchain_api.routers.admin.settings.require_module"):
        with pytest.raises(HTTPException) as exc:
            settings_project_mode_change(MagicMock(), _settings())
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "project_mode_immutable"


def test_hs24_http_post_project_mode_immutable() -> None:
    admin = AdminContext(
        user=AdminUser(
            clerk_user_id="hs24-admin",
            email="hs24@porterchain.test",
            role="super_admin",
            is_active=True,
        ),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_settings] = lambda: _settings()
    client = TestClient(app)
    try:
        with patch("porterchain_api.routers.admin.settings.require_module"):
            r = client.post("/v1/admin/settings/project-mode", json={"mode": "development"})
        assert r.status_code == 403, r.text
        detail = r.json().get("detail") or r.json()
        assert detail.get("code") == "project_mode_immutable"
    finally:
        app.dependency_overrides.pop(get_admin_context, None)
        app.dependency_overrides.pop(get_settings, None)

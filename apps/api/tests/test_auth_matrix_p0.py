"""P0 auth matrix regressions — Staff IdP + driver Clerk seams.

Maps to docs/AUTHENTICATION_DRIVER_ADMIN_DEV_TEST_MATRIX.md:
AD-AUTH-002/003/005 · DR-AUTH-002/003/005/007 · X-001 (via Clerk-on-admin).

Does not duplicate cutover/phase5 suites — only holes those leave open.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.email_identity import EMAIL_CLERK_MISMATCH
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive
from porterchain_api.auth.staff_session import STAFF_COOKIE_NAME
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "a" * 32,
        "spicedb_enabled": False,
        "spicedb_use_memory": True,
        "spicedb_required": False,
        "stripe_mock": True,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def _persona(*, admin=False, merchant=False, driver=False, customer=False) -> MagicMock:
    """Bundle-shaped mock — avoids query/.first vs merchant .all() mock traps."""
    from porterchain_api.auth.persona_bundle import PersonaBundle

    return PersonaBundle(
        clerk_user_id="user_x",
        admin=MagicMock() if admin else None,
        merchant_users=[MagicMock()] if merchant else [],
        driver=MagicMock() if driver else None,
        customer=MagicMock() if customer else None,
    )


# ── AD-AUTH / cookie path ───────────────────────────────────────────────────


def test_ad_auth_003_clerk_jwt_still_retired() -> None:
    """MISS-001 / AD-AUTH-003 — permanent regression for Staff IdP cutover."""

    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        with pytest.raises(HTTPException) as exc:
            await get_admin_context(
                request,
                authorization="Bearer eyJhbGciOiJSUzI1NiJ9.fake.sig",
                db=MagicMock(),
                settings=_settings(),
                x_admin_role=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "admin_clerk_retired_use_staff_idp"

    asyncio.run(_run())


def test_ad_auth_012_bypass_still_rejects_clerk_jwt() -> None:
    """Local bypass must never reopen the retired Clerk-admin path (live :8001 proved)."""

    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        with pytest.raises(HTTPException) as exc:
            await get_admin_context(
                request,
                authorization="Bearer eyJhbGciOiJSUzI1NiJ9.fake.sig",
                db=MagicMock(),
                settings=_settings(clerk_dev_bypass=True, app_env="local"),
                x_admin_role=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "admin_clerk_retired_use_staff_idp"

    asyncio.run(_run())


def test_ad_auth_002_missing_credentials_401() -> None:
    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        with pytest.raises(HTTPException) as exc:
            await get_admin_context(
                request,
                authorization=None,
                db=MagicMock(),
                settings=_settings(clerk_dev_bypass=False),
                x_admin_role=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "missing_bearer_token"

    asyncio.run(_run())


def test_ad_auth_005_cookie_only_staff_session() -> None:
    """HttpOnly pc_staff_sid without Authorization header resolves AdminContext."""
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.staff_session import StaffSession

    async def _run() -> None:
        request = MagicMock()
        request.cookies = {STAFF_COOKIE_NAME: "cookie-sid"}
        admin = AdminUser(
            id="admin-cookie",
            email="ops@porterchain.com",
            name="Ops",
            role=AdminRole.ADMIN.value,
            is_active=True,
        )
        session = StaffSession(
            session_id="cookie-sid",
            admin_user_id="admin-cookie",
            email="ops@porterchain.com",
            role="admin",
            created_at=0,
            expires_at=9e9,
        )
        db = MagicMock()
        # staff_lookups.get_admin_user / legacy query — accept either
        db.get.return_value = admin
        db.query.return_value.filter.return_value.first.return_value = admin

        with (
            patch("porterchain_api.auth.admin.get_session", return_value=session),
            patch("porterchain_api.auth.admin._finish_admin_context") as finish,
        ):
            finish.return_value = MagicMock()
            await get_admin_context(
                request,
                authorization=None,
                db=db,
                settings=_settings(clerk_dev_bypass=False),
                x_admin_role=None,
            )
            finish.assert_called_once()

    asyncio.run(_run())


# ── DR / portal_guard hole (phase5 covers admin/merchant/customer only) ─────


def test_dr_auth_005_driver_portal_requires_provisioning() -> None:
    claims = ClerkClaims(clerk_user_id="user_customer_only", email="c@example.com")
    db = MagicMock()
    with patch(
        "porterchain_api.auth.portal_guard.load_persona_bundle",
        return_value=_persona(customer=True),
    ):
        with pytest.raises(HTTPException) as exc:
            assert_clerk_id_exclusive(db, claims, portal="driver", settings=_settings())
    assert exc.value.status_code == 403
    assert exc.value.detail == "driver_user_not_provisioned"


def test_dr_auth_004_driver_portal_ok_when_provisioned() -> None:
    claims = ClerkClaims(clerk_user_id="user_driver", email="d@example.com")
    db = MagicMock()
    with patch(
        "porterchain_api.auth.portal_guard.load_persona_bundle",
        return_value=_persona(driver=True),
    ):
        assert_clerk_id_exclusive(db, claims, portal="driver", settings=_settings())


# ── get_driver_context fail-closed ──────────────────────────────────────────


def test_dr_auth_002_driver_auth_required_when_bypass_off() -> None:
    from porterchain_api.auth.driver import get_driver_context

    async def _run() -> None:
        # local + bypass false — no production Clerk triad required
        with pytest.raises(HTTPException) as exc:
            await get_driver_context(
                db=MagicMock(),
                settings=_settings(clerk_dev_bypass=False, app_env="local"),
                credentials=None,
                x_driver_id=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "driver_auth_required"

    asyncio.run(_run())


def test_dr_auth_003_invalid_driver_token() -> None:
    from porterchain_api.auth.driver import get_driver_context

    async def _run() -> None:
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")
        with patch(
            "porterchain_api.auth.clerk.verify_clerk_token",
            new_callable=AsyncMock,
            side_effect=ValueError("bad"),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_driver_context(
                    db=MagicMock(),
                    settings=_settings(clerk_dev_bypass=False),
                    credentials=creds,
                    x_driver_id=None,
                )
            assert exc.value.status_code == 401
            assert exc.value.detail == "invalid_driver_token"

    asyncio.run(_run())


def test_dr_auth_007_email_mismatch_403() -> None:
    from porterchain_api.admin_models import Driver
    from porterchain_api.auth.driver import get_driver_context
    from porterchain_api.domain.admin_states import DriverStatus

    async def _run() -> None:
        claims = ClerkClaims(
            clerk_user_id="clerk_drv",
            email="clerk@example.com",
        )
        driver = Driver(
            id="drv-1",
            email="other@example.com",
            full_name="Drv",
            status=DriverStatus.APPROVED.value,
            clerk_user_id="clerk_drv",
        )
        bundle = MagicMock()
        bundle.driver = driver
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="tok")

        with (
            patch(
                "porterchain_api.auth.clerk.verify_clerk_token",
                new_callable=AsyncMock,
                return_value=claims,
            ),
            patch("porterchain_api.auth.prepare.prepare_user_from_claims"),
            patch(
                "porterchain_api.auth.portal_guard.assert_clerk_id_exclusive",
            ),
            patch(
                "porterchain_api.auth.persona_bundle.load_persona_bundle",
                return_value=bundle,
            ),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_driver_context(
                    db=MagicMock(),
                    settings=_settings(clerk_dev_bypass=False),
                    credentials=creds,
                    x_driver_id=None,
                )
            assert exc.value.status_code == 403
            assert exc.value.detail == EMAIL_CLERK_MISMATCH

    asyncio.run(_run())


def test_x_001_driver_looking_bearer_cannot_be_staff_sess() -> None:
    """Clerk-shaped Bearer is never treated as staff_sess prefix."""
    from porterchain_api.auth.admin import _looks_like_clerk_bearer
    from porterchain_api.auth.staff_session import session_id_from_authorization

    clerkish = "Bearer eyJhbGciOiJSUzI1NiJ9.fake.sig"
    assert _looks_like_clerk_bearer(clerkish) is True
    assert session_id_from_authorization(clerkish) is None
    assert session_id_from_authorization("Bearer staff_sess_abc") == "abc"

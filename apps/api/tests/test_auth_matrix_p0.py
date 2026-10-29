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


def _kc_claims(azp: str, email: str | None = "ops@porterchain.com", auth_time: int | None = None):
    return ClerkClaims(
        clerk_user_id="kc-sub-1",
        email=email,
        phone=None,
        org_id=None,
        org_role=None,
        public_metadata={},
        session_id="kc-sid",
        authorized_party=azp,
        auth_time=auth_time,
    )


JWT = "Bearer eyJhbGciOiJSUzI1NiJ9.eyJhenAiOiJ4In0.sig"


@pytest.mark.parametrize("bypass", [False, True])
def test_ad_auth_003_non_admin_client_token_rejected(bypass: bool) -> None:
    """A valid Keycloak token from another portal client never reaches /v1/admin (bypass or not)."""

    async def _run() -> None:
        request = MagicMock()
        with patch(
            "porterchain_api.auth.keycloak.verify_keycloak_token",
            AsyncMock(return_value=_kc_claims("pc-merchant-portal")),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_admin_context(
                    request, authorization=JWT, db=MagicMock(),
                    settings=_settings(clerk_dev_bypass=bypass), x_admin_role=None,
                )
        assert exc.value.status_code == 401
        assert exc.value.detail == "admin_token_wrong_client"

    asyncio.run(_run())


def test_ad_auth_005_pc_admin_token_resolves_staff_by_email() -> None:
    from porterchain_api.admin_models import AdminUser

    async def _run() -> None:
        request = MagicMock()
        admin = AdminUser(id="admin-kc", email="ops@porterchain.com", name="Ops",
                          role=AdminRole.ADMIN.value, is_active=True)
        with (
            patch("porterchain_api.auth.keycloak.verify_keycloak_token",
                  AsyncMock(return_value=_kc_claims("pc-admin"))),
            patch("porterchain_api.admin_engine.staff_lookups.get_admin_by_email", return_value=admin),
            patch("porterchain_api.auth.admin._staff_identity_current", return_value=True),
            patch("porterchain_api.auth.admin._finish_admin_context") as finish,
        ):
            finish.return_value = MagicMock()
            await get_admin_context(request, authorization=JWT, db=MagicMock(),
                                    settings=_settings(), x_admin_role=None)
            assert finish.call_args.args[1] is admin
        assert request.state.admin_claims.authorized_party == "pc-admin"

    asyncio.run(_run())


@pytest.mark.parametrize("email,active,detail", [(None, True, "admin_email_unverified"),
                                                 ("ops@porterchain.com", False, "admin_user_inactive"),
                                                 ("nobody@porterchain.com", True, "admin_user_not_found")])
def test_ad_auth_006_pc_admin_token_requires_known_active_staff(email, active, detail) -> None:
    from porterchain_api.admin_models import AdminUser

    async def _run() -> None:
        admin = AdminUser(id="a1", email="ops@porterchain.com", role="admin", is_active=active)
        found = admin if email == "ops@porterchain.com" else None
        with (
            patch("porterchain_api.auth.keycloak.verify_keycloak_token",
                  AsyncMock(return_value=_kc_claims("pc-admin", email=email))),
            patch("porterchain_api.admin_engine.staff_lookups.get_admin_by_email", return_value=found),
        ):
            with pytest.raises(HTTPException) as exc:
                await get_admin_context(MagicMock(), authorization=JWT, db=MagicMock(),
                                        settings=_settings(), x_admin_role=None)
        assert exc.value.status_code == 403
        assert exc.value.detail == detail

    asyncio.run(_run())


@pytest.mark.parametrize("token", ["staff_sess_abc", "pc_imp_x", "opaque"])
def test_x_001_legacy_staff_bearers_rejected(token: str) -> None:
    """The retired Staff IdP bearer and other opaque tokens are never admin credentials."""

    async def _run() -> None:
        with pytest.raises(HTTPException) as exc:
            await get_admin_context(MagicMock(), authorization=f"Bearer {token}", db=MagicMock(),
                                    settings=_settings(), x_admin_role=None)
        assert exc.value.status_code == 401
        assert exc.value.detail == "invalid_token"

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



"""Auth cutover guards — platform_driver, staff IdP, seats, retail self-signup."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.admin_engine.platform_user_authorize import authorize_platform_user
from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS, permissions_catalog
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.clerk_config_audit import audit_clerk_settings, resolve_clerk_runtime_mode
from porterchain_api.auth.staff_session import (
    STAFF_BEARER_PREFIX,
    bearer_token_for_session,
    session_id_from_authorization,
)
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.merchant_engine.rbac import permissions_catalog as merchant_permissions_catalog


def test_admin_permissions_catalog_covers_all_roles() -> None:
    catalog = permissions_catalog()
    role_values = {r["role"] for r in catalog["roles"]}
    assert role_values == {r.value for r in AdminRole}
    assert len(catalog["modules"]) == len(MODULE_PERMISSIONS)
    super_admin = next(r for r in catalog["roles"] if r["role"] == "super_admin")
    assert "settings" in super_admin["modules"]
    read_only = next(r for r in catalog["roles"] if r["role"] == "read_only")
    assert "settings" not in read_only["modules"]


def test_merchant_permissions_catalog_has_five_product_roles() -> None:
    catalog = merchant_permissions_catalog()
    roles = {r["role"] for r in catalog["roles"]}
    assert roles >= {
        "merchant_owner",
        "merchant_admin",
        "merchant_ops",
        "merchant_finance",
        "merchant_readonly",
    }


def test_authorize_customer_raises_self_signup_only() -> None:
    with pytest.raises(ValueError, match="customer_self_signup_only"):
        authorize_platform_user(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            "customer",
            email="c@example.com",
        )


def test_get_customer_context_deleted() -> None:
    import porterchain_api.auth.customer as customer_mod

    assert not hasattr(customer_mod, "get_customer_context")
    assert not hasattr(customer_mod, "CustomerContext")
    assert hasattr(customer_mod, "require_customer")


def test_staff_bearer_helpers() -> None:
    assert session_id_from_authorization("Bearer staff_sess_abc123") == "abc123"
    assert session_id_from_authorization("Bearer eyJhbGciOi...") is None
    assert bearer_token_for_session("xyz") == f"{STAFF_BEARER_PREFIX}xyz"


def test_get_admin_context_rejects_clerk_jwt() -> None:
    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        with pytest.raises(HTTPException) as exc:
            await get_admin_context(
                request,
                authorization="Bearer eyJhbGciOiJSUzI1NiJ9.fake.sig",
                db=MagicMock(),
                settings=Settings(app_env="local", clerk_dev_bypass=False),
                x_admin_role=None,
            )
        assert exc.value.status_code == 401
        assert exc.value.detail == "admin_clerk_retired_use_staff_idp"

    asyncio.run(_run())


def test_notification_principal_accepts_staff_session() -> None:
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.staff_session import StaffSession
    from porterchain_api.notification_engine.principal import (
        _resolve_staff_notification_user,
        get_notification_user,
        resolve_notification_ws_user,
    )

    admin = AdminUser(
        id="admin-n1",
        email="ops@porterchain.com",
        name="Ops",
        role=AdminRole.SUPER_ADMIN.value,
        is_active=True,
    )
    session = StaffSession(
        session_id="notif-sid",
        admin_user_id="admin-n1",
        email="ops@porterchain.com",
        role="super_admin",
        created_at=0,
        expires_at=9e9,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = admin

    with patch(
        "porterchain_api.notification_engine.principal.get_session",
        return_value=session,
    ):
        resolved = _resolve_staff_notification_user(db, "staff_sess_notif-sid")
        assert resolved is not None
        assert resolved.user_role == "admin"
        assert resolved.user_id == "admin-n1"

        async def _http() -> None:
            creds = MagicMock()
            creds.credentials = "staff_sess_notif-sid"
            user = await get_notification_user(
                db=db,
                settings=Settings(app_env="local", clerk_dev_bypass=False),
                credentials=creds,
                x_merchant_id=None,
            )
            assert user.user_role == "admin"
            assert user.user_id == "admin-n1"

        asyncio.run(_http())

        async def _ws() -> None:
            with patch("porterchain_api.db.SessionLocal", return_value=db):
                user = await resolve_notification_ws_user("staff_sess_notif-sid")
                assert user is not None
                assert user.user_role == "admin"
                assert user.user_id == "admin-n1"

        asyncio.run(_ws())


def test_get_admin_context_accepts_staff_session() -> None:
    from porterchain_api.auth.staff_session import StaffSession
    from porterchain_api.admin_models import AdminUser

    async def _run() -> None:
        request = MagicMock()
        request.cookies = {}
        admin = AdminUser(
            id="admin-1",
            email="ops@porterchain.com",
            name="Ops",
            role=AdminRole.ADMIN.value,
            is_active=True,
        )
        session = StaffSession(
            session_id="sid1",
            admin_user_id="admin-1",
            email="ops@porterchain.com",
            role="admin",
            created_at=0,
            expires_at=9e9,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = admin
        settings = Settings(app_env="local", clerk_dev_bypass=False, spicedb_enabled=False)

        with (
            patch("porterchain_api.auth.admin.get_session", return_value=session),
            patch("porterchain_api.auth.admin._finish_admin_context") as finish,
        ):
            finish.return_value = MagicMock()
            await get_admin_context(
                request,
                authorization="Bearer staff_sess_sid1",
                db=db,
                settings=settings,
                x_admin_role=None,
            )
            finish.assert_called_once()

    asyncio.run(_run())


def test_staff_passkey_options_anti_enumeration() -> None:
    """Unknown emails and no-passkey staff get decoy options — never staff_not_found."""
    from unittest.mock import MagicMock, patch

    from porterchain_api.admin_engine import staff_webauthn

    settings = Settings(
        app_env="local",
        admin_portal_url="http://localhost:3002",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with patch.object(staff_webauthn, "_store_challenge", return_value="decoy-chal") as store:
        payload = staff_webauthn.authentication_options(
            db, settings, email="unknown@example.com"
        )
    assert payload["challenge_id"] == "decoy-chal"
    assert payload["email"] == "unknown@example.com"
    store.assert_called_once()
    assert store.call_args.args[0] == "login_decoy"


def test_staff_passkey_decoy_verify_fails_generically() -> None:
    from unittest.mock import patch

    from porterchain_api.admin_engine import staff_webauthn

    settings = Settings(app_env="local", admin_portal_url="http://localhost:3002")
    with patch.object(
        staff_webauthn,
        "_pop_challenge",
        return_value={"kind": "login_decoy", "admin_user_id": "decoy", "challenge": "x"},
    ):
        with pytest.raises(ValueError, match="passkey_login_failed"):
            staff_webauthn.verify_authentication(
                MagicMock(),
                settings,
                challenge_id="x",
                credential={"id": "cred"},
            )


def test_architecture_census_staff_not_clerk() -> None:
    from pathlib import Path

    text = Path(__file__).resolve().parents[3].joinpath("ARCHITECTURE.md").read_text()
    assert "Staff IdP session" in text
    assert "| Staff | `/v1/admin` | Clerk staff |" not in text


def test_clerk_audit_platform_driver_secret_matrix() -> None:
    settings = Settings(
        app_env="local",
        clerk_unified_mode=False,
        clerk_publishable_key="pk_test_platform",
        clerk_secret_key="sk_test_platform",
        clerk_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_customer_publishable_key="pk_test_platform",
        clerk_customer_secret_key="sk_test_platform",
        clerk_customer_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_merchant_publishable_key="pk_test_platform",
        clerk_merchant_secret_key="sk_test_platform",
        clerk_merchant_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_admin_publishable_key="pk_test_platform",
        clerk_admin_secret_key="sk_test_platform",
        clerk_admin_jwks_url="https://platform.clerk.accounts.dev/.well-known/jwks.json",
        clerk_driver_publishable_key="pk_test_driver",
        clerk_driver_secret_key="sk_test_driver",
        clerk_driver_jwks_url="https://driver.clerk.accounts.dev/.well-known/jwks.json",
    )
    assert resolve_clerk_runtime_mode(settings) == "platform_driver"
    findings = {f.name: f for f in audit_clerk_settings(settings)}
    assert findings["CLERK_CONFIGURATION_MODE"].detail == "platform_driver"
    assert findings["SECRET_ACCESS_MATRIX"].status == "info"
    assert "staff IdP" in findings["SECRET_ACCESS_MATRIX"].detail
    assert "CLERK_MODE_RETIRED" not in findings


def test_invite_admin_staff_and_merchant_invite_deleted() -> None:
    from porterchain_api.auth.invitation_service import InvitationService

    assert not hasattr(InvitationService, "invite_admin_staff")
    assert not hasattr(InvitationService, "invite_merchant_owner")
    assert not hasattr(InvitationService, "invite_merchant_member")


def test_ensure_staff_identity_prefers_existing_staff_subject(db) -> None:
    """Dev bypass / rebind must not UniqueViolation when staff:{id} already exists."""
    from uuid import uuid4

    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.user_models import PorterchainUser

    suffix = uuid4().hex[:8]
    admin = AdminUser(
        email=f"dev-ops-{suffix}@porterchain.com",
        name="Dev Ops",
        role="admin",
        is_active=True,
        clerk_user_id=f"dev_clerk_user_{suffix}",
    )
    db.add(admin)
    db.flush()

    staff_pc = PorterchainUser(
        clerk_user_id=f"staff:{admin.id}",
        email=admin.email,
        role="admin",
        status="active",
        default_workspace="admin",
    )
    legacy_pc = PorterchainUser(
        clerk_user_id=f"legacy_clerk_{suffix}",
        email=admin.email,
        role="unprovisioned",
        status="active",
    )
    db.add_all([staff_pc, legacy_pc])
    db.flush()
    admin.porterchain_user_id = legacy_pc.id
    db.commit()

    bound = ensure_staff_identity(db, admin)
    db.refresh(admin)
    assert bound == staff_pc.id
    assert admin.porterchain_user_id == staff_pc.id
    assert admin.clerk_user_id == f"staff:{admin.id}"


def test_staff_session_index_and_revoke_all() -> None:
    import json
    import time

    from porterchain_api.auth import staff_session as ss

    store: dict[str, str] = {}
    sets: dict[str, set[str]] = {}

    class FakeRedis:
        def setex(self, key, ttl, value):
            store[key] = value

        def get(self, key):
            return store.get(key)

        def delete(self, key):
            return 1 if store.pop(key, None) is not None else 0

        def sadd(self, key, member):
            sets.setdefault(key, set()).add(member)

        def expire(self, key, ttl):
            return True

        def srem(self, key, member):
            if key in sets:
                sets[key].discard(member)

        def smembers(self, key):
            return set(sets.get(key, set()))

        def ping(self):
            return True

    with patch.object(ss, "_client", return_value=FakeRedis()):
        a = ss.create_session(admin_user_id="admin-1", email="a@pc.com", role="admin")
        b = ss.create_session(admin_user_id="admin-1", email="a@pc.com", role="admin")
        assert a and b
        listed = ss.list_sessions_for_user("admin-1", current_session_id=a.session_id)
        assert len(listed) == 2
        assert any(row["is_current"] for row in listed)
        revoked = ss.revoke_all_for_user("admin-1", except_session_id=a.session_id)
        assert revoked == 1
        left = ss.list_sessions_for_user("admin-1", current_session_id=a.session_id)
        assert len(left) == 1
        assert left[0]["session_id"] == a.session_id


def test_staff_session_absolute_cap() -> None:
    import json
    import time

    from porterchain_api.auth import staff_session as ss

    store: dict[str, str] = {}

    class FakeRedis:
        def setex(self, key, ttl, value):
            store[key] = value

        def get(self, key):
            return store.get(key)

        def delete(self, key):
            return 1 if store.pop(key, None) is not None else 0

        def sadd(self, *a, **k):
            return 1

        def expire(self, *a, **k):
            return True

        def srem(self, *a, **k):
            return 1

        def smembers(self, key):
            return set()

        def ping(self):
            return True

    with patch.object(ss, "_client", return_value=FakeRedis()):
        session = ss.create_session(admin_user_id="admin-1", email="a@pc.com", role="admin")
        assert session is not None
        raw = json.loads(store[f"{ss.SESSION_PREFIX}{session.session_id}"])
        raw["absolute_expires_at"] = time.time() - 10
        store[f"{ss.SESSION_PREFIX}{session.session_id}"] = json.dumps(raw)
        assert ss.get_session(session.session_id) is None


def test_staff_step_up_freshness() -> None:
    import time

    from porterchain_api.auth.staff_session import StaffSession, assert_recent_step_up

    now = time.time()
    fresh = StaffSession(
        session_id="s1",
        admin_user_id="a1",
        email="a@pc.com",
        role="admin",
        created_at=now,
        expires_at=now + 3600,
        absolute_expires_at=now + 86400,
        step_up_at=now,
    )
    assert_recent_step_up(fresh)
    stale = StaffSession(
        session_id="s2",
        admin_user_id="a1",
        email="a@pc.com",
        role="admin",
        created_at=now - 3600,
        expires_at=now + 3600,
        absolute_expires_at=now + 86400,
        step_up_at=now - 3600,
    )
    with pytest.raises(PermissionError, match="staff_step_up_required"):
        assert_recent_step_up(stale)


def test_auth_sli_prometheus_lines() -> None:
    from porterchain_api.auth.sli_metrics import (
        auth_events_snapshot,
        note_auth_event,
        prometheus_auth_lines,
        reset_auth_events_for_tests,
    )

    reset_auth_events_for_tests()
    note_auth_event("staff_login_passkey", "ok")
    note_auth_event("staff_step_up_check", "required")
    text = "\n".join(prometheus_auth_lines())
    assert "porterchain_auth_events_total" in text
    assert 'kind="staff_login_passkey"' in text
    assert 'result="ok"' in text
    snap = auth_events_snapshot()
    assert snap["staff_login_passkey"]["ok"] == 1
    assert snap["staff_step_up_check"]["required"] == 1
    reset_auth_events_for_tests()


def test_staff_session_stores_client_meta() -> None:
    from porterchain_api.auth import staff_session as ss

    store: dict[str, str] = {}
    sets: dict[str, set[str]] = {}

    class FakeRedis:
        def setex(self, key, ttl, value):
            store[key] = value

        def get(self, key):
            return store.get(key)

        def delete(self, key):
            return 1 if store.pop(key, None) is not None else 0

        def sadd(self, key, member):
            sets.setdefault(key, set()).add(member)

        def expire(self, key, ttl):
            return True

        def srem(self, key, member):
            if key in sets:
                sets[key].discard(member)

        def smembers(self, key):
            return set(sets.get(key, set()))

        def ping(self):
            return True

    fake = FakeRedis()
    monkey = pytest.MonkeyPatch()
    monkey.setattr(ss, "_client", lambda: fake)
    try:
        session = ss.create_session(
            admin_user_id="admin-1",
            email="ops@porterchain.com",
            role="super_admin",
            client_meta={
                "client_ip": "203.0.113.9",
                "user_agent": "Mozilla/5.0 Chrome/120.0",
                "device_label": "Chrome",
            },
        )
        assert session is not None
        assert session.client_ip == "203.0.113.9"
        assert session.device_label == "Chrome"
        pub = session.public_dict(current_session_id=session.session_id)
        assert pub["client_ip"] == "203.0.113.9"
        assert pub["device_label"] == "Chrome"
        assert pub["is_current"] is True
        touched = ss.get_session(session.session_id, touch=True)
        assert touched is not None
        assert touched.client_ip == "203.0.113.9"
        assert touched.device_label == "Chrome"
    finally:
        monkey.undo()


def test_client_meta_from_request_prefers_forwarded() -> None:
    from unittest.mock import MagicMock

    from porterchain_api.auth.staff_session import client_meta_from_request

    req = MagicMock()
    req.headers.get.side_effect = lambda k, d=None: {
        "x-forwarded-for": "198.51.100.2, 10.0.0.1",
        "user-agent": "Mozilla/5.0 (Macintosh) Firefox/128.0",
    }.get(k.lower() if isinstance(k, str) else k, d)
    # headers.get is case-sensitive in our helper — pass exact keys
    req.headers.get = lambda key, default="": {
        "x-forwarded-for": "198.51.100.2, 10.0.0.1",
        "user-agent": "Mozilla/5.0 (Macintosh) Firefox/128.0",
    }.get(key, default)
    meta = client_meta_from_request(req)
    assert meta["client_ip"] == "198.51.100.2"
    assert meta["device_label"] == "Firefox"


def test_enforce_staff_step_up_dev_bypass() -> None:
    from unittest.mock import MagicMock

    from porterchain_api.auth.staff_step_up import enforce_staff_step_up

    req = MagicMock()
    req.cookies = {}
    settings = Settings(app_env="local", clerk_dev_bypass=True)
    # Should not raise for Bearer dev
    enforce_staff_step_up(req, "Bearer dev", settings)

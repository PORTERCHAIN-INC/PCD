"""Admin portal on Keycloak ``pc-admin`` (Staff IdP login removed).

Unit tests run everywhere. Integration tests use the THROWAWAY Keycloak only
(scripts/test-keycloak.sh, :18180) and are skipped unless PCD_TEST_KEYCLOAK_URL is set.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import HTTPException

from porterchain_api.auth import keycloak_admin
from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.keycloak_staff import STEP_UP_MAX_AGE_SECONDS, assert_recent_login, looks_like_jwt
from porterchain_api.config import Settings

BASE = os.environ.get("PCD_TEST_KEYCLOAK_URL", "").rstrip("/")
if BASE and any(p in BASE for p in (":8180", ":8543")):
    raise RuntimeError("refusing to run against the live pch-keycloak ports")
needs_kc = pytest.mark.skipif(not BASE, reason="PCD_TEST_KEYCLOAK_URL not set")


def _claims(azp="pc-admin", email="ops@porterchain.com", auth_time=None) -> IdentityClaims:
    return IdentityClaims(clerk_user_id="kc-1", email=email, phone=None, org_id=None, org_role=None,
                       public_metadata={}, session_id="sid", authorized_party=azp, auth_time=auth_time)


# ── unit ──────────────────────────────────────────────────────────────────────


def test_looks_like_jwt() -> None:
    assert looks_like_jwt("a.b.c")
    assert not looks_like_jwt("staff_sess_abc")
    assert not looks_like_jwt("opaque")


def test_step_up_freshness() -> None:
    now = time.time()
    assert_recent_login(_claims(auth_time=int(now - 60)), now=now)
    for stale in (None, int(now - STEP_UP_MAX_AGE_SECONDS - 5)):
        with pytest.raises(PermissionError, match="staff_step_up_required"):
            assert_recent_login(_claims(auth_time=stale), now=now)
    with pytest.raises(PermissionError):
        assert_recent_login(None)


def test_enforce_staff_step_up_uses_verified_admin_claims() -> None:
    from porterchain_api.auth.staff_step_up import enforce_staff_step_up

    s = Settings(_env_file=None, app_env="local", auth_dev_bypass=False)
    req = MagicMock()
    req.state = SimpleNamespace(admin_claims=_claims(auth_time=int(time.time())))
    enforce_staff_step_up(req, "Bearer a.b.c", s)
    req.state = SimpleNamespace(admin_claims=_claims(auth_time=int(time.time()) - 3600))
    with pytest.raises(HTTPException) as exc:
        enforce_staff_step_up(req, "Bearer a.b.c", s)
    assert exc.value.status_code == 403 and exc.value.detail == "staff_step_up_required"
    req.state = SimpleNamespace()
    with pytest.raises(HTTPException):
        enforce_staff_step_up(req, "Bearer a.b.c", s)
    # dev bypass: Bearer dev skips step-up
    enforce_staff_step_up(MagicMock(), "Bearer dev", Settings(_env_file=None, app_env="local", auth_dev_bypass=True))


def test_notification_admin_recipient_only_for_pc_admin() -> None:
    from porterchain_api.notification_engine.principal import _admin_recipient_from_claims

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id="adm-1")
    assert _admin_recipient_from_claims(db, _claims()).user_id == "adm-1"
    assert _admin_recipient_from_claims(db, _claims(azp="pc-merchant-portal")) is None
    assert _admin_recipient_from_claims(db, _claims(email=None)) is None


def test_staff_accounts_require_keycloak_outside_local() -> None:
    from porterchain_api.admin_engine.staff_accounts import _admin

    unset = dict(keycloak_url="", keycloak_internal_url="", keycloak_admin_client_id="pc-api-admin",
                 keycloak_admin_client_secret="", keycloak_realm="porterchain")
    assert _admin(SimpleNamespace(app_env="local", **unset)) is None
    with pytest.raises(keycloak_admin.KeycloakAdminUnavailable, match="keycloak_admin_unconfigured"):
        _admin(SimpleNamespace(app_env="production", **unset))


def test_enroll_local_without_keycloak_creates_admin_user(db) -> None:
    from porterchain_api.admin_engine.staff_accounts import StaffAccountService
    from porterchain_api.admin_models import AdminUser

    email = f"kc-enroll-{uuid.uuid4().hex[:8]}@porterchain.com"
    ctx = SimpleNamespace(user=SimpleNamespace(id="actor", email="actor@porterchain.com"), role="super_admin")
    with patch("porterchain_api.admin_engine.staff_accounts.log_admin_audit"), \
         patch("porterchain_api.admin_engine.staff_accounts.ensure_staff_identity"):
        out = StaffAccountService().enroll(db, ctx, Settings(_env_file=None, app_env="local"),
                                           email=email, role="support", name="Kc Test")
    assert out["keycloak_provisioned"] is False and out["email_sent"] is False
    assert "enrollment_token" not in out
    row = db.query(AdminUser).filter(AdminUser.email == email).one()
    assert row.role == "support" and row.is_active
    db.delete(row)
    db.commit()


def test_keycloak_admin_role_sync_adds_mfa_for_admin_tiers() -> None:
    calls: list[tuple[str, str, object]] = []
    roles = {n: {"id": n, "name": n} for n in ("admin", "support", "mfa_required")}

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "t", "expires_in": 60})
        calls.append((req.method, path, req.content))
        if path.endswith("/role-mappings/realm") and req.method == "GET":
            return httpx.Response(200, json=[roles["support"]])
        if "/roles/" in path:
            return httpx.Response(200, json=roles[path.rsplit("/", 1)[1]])
        return httpx.Response(204)

    keycloak_admin._token_cache.clear()
    s = Settings(_env_file=None, keycloak_url="http://kc.test", keycloak_admin_client_secret="x")
    kc = keycloak_admin.KeycloakAdmin(s, client=httpx.Client(transport=httpx.MockTransport(handler)))
    kc._sync_roles("u1", "admin")
    methods = [(m, p.rsplit("/", 1)[1]) for m, p, _ in calls]
    assert ("DELETE", "realm") in methods and ("POST", "realm") in methods
    posted = next(c for m, p, c in calls if m == "POST" and p.endswith("/role-mappings/realm"))
    assert b"admin" in posted and b"mfa_required" in posted


# ── integration (throwaway Keycloak) ─────────────────────────────────────────


def _master_headers(c: httpx.Client) -> dict:
    tok = c.post(f"{BASE}/realms/master/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": "admin-cli", "username": "admin",
        "password": os.environ.get("PCD_TEST_KEYCLOAK_ADMIN_PASSWORD", "test-admin-only")}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _kc_settings() -> Settings:
    return Settings(_env_file=None, keycloak_url=BASE, keycloak_admin_client_secret="test-api-admin-secret")


@needs_kc
def test_service_account_provisions_staff_lifecycle() -> None:
    keycloak_admin._token_cache.clear()
    kc = keycloak_admin.KeycloakAdmin(_kc_settings())
    email = f"staff-{uuid.uuid4().hex[:8]}@example.test"
    kc_id, created = kc.ensure_staff_user(email=email, name="Ada Ops", role="admin")
    assert created
    assert kc.ensure_staff_user(email=email, name="Ada Ops", role="admin") == (kc_id, False)
    assert "CONFIGURE_TOTP" in kc.pending_actions(kc_id)
    with httpx.Client(timeout=20) as c:
        h = _master_headers(c)
        adm = f"{BASE}/admin/realms/porterchain"
        names = {r["name"] for r in c.get(f"{adm}/users/{kc_id}/role-mappings/realm", headers=h).json()}
        assert {"admin", "mfa_required"} <= names
        kc._sync_roles(kc_id, "support")
        names = {r["name"] for r in c.get(f"{adm}/users/{kc_id}/role-mappings/realm", headers=h).json()}
        assert "support" in names and "admin" not in names and "mfa_required" not in names
        assert kc.reset_mfa(kc_id) == 0
        assert "CONFIGURE_TOTP" in kc.pending_actions(kc_id)
        assert isinstance(kc.send_actions_email(kc_id, ["UPDATE_PASSWORD"]), bool)  # no SMTP in test
        assert kc.disable(email) is True
        assert c.get(f"{adm}/users/{kc_id}", headers=h).json()["enabled"] is False
        c.delete(f"{adm}/users/{kc_id}", headers=h)


@needs_kc
def test_bad_service_account_secret_is_unavailable() -> None:
    keycloak_admin._token_cache.clear()
    s = Settings(_env_file=None, keycloak_url=BASE, keycloak_admin_client_secret="wrong")
    with pytest.raises(keycloak_admin.KeycloakAdminUnavailable, match="keycloak_admin_auth_failed"):
        keycloak_admin.KeycloakAdmin(s).find_user("x@example.test")


@pytest.fixture
def pc_admin_user():
    """Support-tier staff user (no OTP) in the THROWAWAY realm."""
    with httpx.Client(timeout=20) as c:
        h = _master_headers(c)
        adm = f"{BASE}/admin/realms/porterchain"
        email = f"ops-{uuid.uuid4().hex[:8]}@example.test"
        pw = uuid.uuid4().hex + "Aa1!"
        c.post(f"{adm}/users", headers=h, json={"username": email, "email": email, "enabled": True,
                                                "emailVerified": True, "requiredActions": []})
        uid = c.get(f"{adm}/users?email={email}&exact=true", headers=h).json()[0]["id"]
        c.put(f"{adm}/users/{uid}/reset-password", headers=h, json={"type": "password", "value": pw, "temporary": False})
        role = c.get(f"{adm}/roles/support", headers=h).json()
        c.post(f"{adm}/users/{uid}/role-mappings/realm", headers=h, json=[role])
        yield {"email": email, "password": pw}
        c.delete(f"{adm}/users/{uid}", headers=_master_headers(c))


def _browser_login(email: str, password: str) -> str:
    """Real pc-admin authorization-code + PKCE login through the Keycloak login form."""
    import base64
    import hashlib
    import html
    import re
    import secrets
    from urllib.parse import parse_qs, urlparse

    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect = "http://localhost:3002/auth/callback"
    realm = f"{BASE}/realms/porterchain/protocol/openid-connect"
    with httpx.Client(timeout=20, follow_redirects=False) as c:
        page = c.get(f"{realm}/auth", params={
            "client_id": "pc-admin", "response_type": "code", "scope": "openid",
            "redirect_uri": redirect, "code_challenge": challenge, "code_challenge_method": "S256",
            "state": "s1"})
        # Keycloak sets Secure cookies; http.cookiejar drops them on plain http → forward by hand.
        jar = "; ".join(v.split(";", 1)[0] for k, v in page.headers.multi_items() if k.lower() == "set-cookie")
        action = html.unescape(re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', page.text).group(1))
        res = c.post(action, data={"username": email, "password": password, "credentialId": ""},
                     headers={"Cookie": jar})
        location = res.headers.get("location", "")
        if res.status_code != 302 or not location.startswith(redirect):
            body = res.text
            if res.status_code == 302:  # e.g. required-action / OTP step inside Keycloak
                body = c.get(location, headers={"Cookie": jar}).text + location
            open("/tmp/kc_page.html", "w").write(body)
        assert res.status_code == 302 and location.startswith(redirect), "login form did not redirect"
        code = parse_qs(urlparse(res.headers["location"]).query)["code"][0]
        tok = c.post(f"{realm}/token", data={"grant_type": "authorization_code", "client_id": "pc-admin",
                                             "code": code, "redirect_uri": redirect, "code_verifier": verifier})
        tok.raise_for_status()
        return tok.json()["access_token"]


@needs_kc
def test_real_pc_admin_token_resolves_admin_context(db, pc_admin_user) -> None:
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.admin import get_admin_context

    tok = _browser_login(pc_admin_user["email"], pc_admin_user["password"])
    row = AdminUser(email=pc_admin_user["email"], name="Ops", role="support", is_active=True,
                    clerk_user_id=f"pending:{pc_admin_user['email']}")
    db.add(row)
    db.commit()
    request = MagicMock()
    request.state = SimpleNamespace()
    try:
        with patch("porterchain_api.auth.admin._staff_identity_current", return_value=True), \
             patch("porterchain_api.auth.admin._finish_admin_context", side_effect=lambda d, u, s, r: u), \
             patch("porterchain_api.platform.admin_ip_allowlist.enforce"):
            user = asyncio.run(get_admin_context(request, authorization=f"Bearer {tok}", db=db,
                                                 settings=Settings(_env_file=None, keycloak_url=BASE),
                                                 x_admin_role=None))
        assert user.id == row.id
        assert request.state.admin_claims.auth_time  # step-up source
        assert_recent_login(request.state.admin_claims)
    finally:
        db.delete(row)
        db.commit()


@needs_kc
def test_admin_tier_login_requires_totp() -> None:
    """super_admin/admin carry mfa_required → pc-admin login stops at TOTP setup, no code issued."""
    keycloak_admin._token_cache.clear()
    kc = keycloak_admin.KeycloakAdmin(_kc_settings())
    email = f"adm-{uuid.uuid4().hex[:8]}@example.test"
    kc_id, _ = kc.ensure_staff_user(email=email, name="Adm", role="admin")
    pw = uuid.uuid4().hex + "Aa1!"
    with httpx.Client(timeout=20) as c:
        h = _master_headers(c)
        adm = f"{BASE}/admin/realms/porterchain"
        c.put(f"{adm}/users/{kc_id}", headers=h, json={"emailVerified": True, "requiredActions": []})
        c.put(f"{adm}/users/{kc_id}/reset-password", headers=h, json={"type": "password", "value": pw, "temporary": False})
        try:
            with pytest.raises(AssertionError, match="login form did not redirect"):
                _browser_login(email, pw)
            page = open("/tmp/kc_page.html").read().lower()
            assert "authenticator" in page or "otp" in page
        finally:
            c.delete(f"{adm}/users/{kc_id}", headers=h)

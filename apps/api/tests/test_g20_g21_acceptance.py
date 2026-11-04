"""G20 (Shopify review, 76 §10) and G21 (mobile review, 76 §11) acceptance checks.

Covers the IDs that had no direct test yet: A-SHR-02/05/07 and A-APR-03/07/08.
A-SHR-01/06 and A-APR-01/02/04 live in test_g20_*, test_g21_*, the merchant-portal
shopifyEmbedG20 test and the Maestro flows. A-APR-05/06 are manual release checks.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
import tomllib
from pathlib import Path

import jwt
import pytest

from porterchain_api.config import Settings
from porterchain_api.integrations.shopify_hmac import verify_webhook_hmac
from porterchain_api.merchant_engine.shopify_session import verify_session_token
from porterchain_api.merchant_engine.shopify_urls import oauth_scopes

REPO = Path(__file__).resolve().parents[3]
KEY, SECRET, SHOP = "g20-client-id", "g20-app-secret-0123456789abcdef-0123", "pcdc-demo.myshopify.com"


def _settings(**kw) -> Settings:
    return Settings(shopify_api_key=KEY, shopify_api_secret=SECRET, **kw)


def _session_token(secret: str = SECRET, **over) -> str:
    now = int(time.time())
    claims = {"iss": f"https://{SHOP}/admin", "dest": f"https://{SHOP}", "aud": KEY,
              "sub": "1", "exp": now + 60, "nbf": now - 5, "iat": now - 5, "jti": "j"}
    claims.update(over)
    return jwt.encode(claims, secret, algorithm="HS256")


# --- G20 -------------------------------------------------------------------------------

@pytest.mark.tc_id("A-SHR-02")
def test_a_shr_02_session_token_valid_expired_forged() -> None:
    assert verify_session_token(_session_token(), _settings()) == SHOP
    with pytest.raises(ValueError):
        verify_session_token(_session_token(exp=int(time.time()) - 600), _settings())
    with pytest.raises(ValueError):
        verify_session_token(_session_token(secret="forged-secret-forged-secret-forged-0000"), _settings())


@pytest.mark.tc_id("A-SHR-05")
def test_a_shr_05_compliance_webhook_hmac() -> None:
    body = json.dumps({"shop_domain": SHOP}).encode()
    good = base64.b64encode(hmac.new(SECRET.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_webhook_hmac(body, good, [SECRET])
    assert not verify_webhook_hmac(body, "AAAA", [SECRET])
    assert not verify_webhook_hmac(body, None, [SECRET])
    assert not verify_webhook_hmac(body + b" ", good, [SECRET])


@pytest.mark.tc_id("A-SHR-07")
def test_a_shr_07_requested_scopes_equal_used_scopes() -> None:
    toml = tomllib.loads((REPO / "integrations/shopify/shopify.app.custom.toml").read_text())
    declared = set(toml["access_scopes"]["scopes"].split(","))
    requested = set(oauth_scopes(Settings(shopify_returns_scope_enabled=False)).split(","))
    assert declared == requested, (declared ^ requested)
    src = "\n".join(p.read_text() for p in (REPO / "apps/api/src/porterchain_api").rglob("shopify*.py"))
    unused = {s for s in declared if s.split("_", 1)[1] not in src and s not in src}
    assert not unused, f"declared but never used: {unused}"


# --- G21 -------------------------------------------------------------------------------

@pytest.mark.tc_id("A-APR-03")
def test_a_apr_03_web_deletion_page_for_both_apps() -> None:
    page = (REPO / "website/src/app/[locale]/delete-account/page.tsx").read_text()
    assert 'data-testid="delete-account-page"' in page
    assert "customer" in page.lower() and "driver" in page.lower()
    policy = (REPO / "website/src/lib/seo/url-policy.ts").read_text()
    assert '"delete-account"' in policy


@pytest.mark.tc_id("A-APR-07")
def test_a_apr_07_no_otp_captcha_except_staff_totp_and_brute_force() -> None:
    realm = json.loads((REPO / "infrastructure/keycloak/realm-porterchain.json").read_text())
    assert realm["bruteForceProtected"] is True and realm["failureFactor"] == 10
    roles = {r["name"]: r for r in realm["roles"]["realm"]}
    for staff in ("super_admin", "admin"):
        assert "mfa_required" in roles[staff].get("composites", {}).get("realm", [])
    for persona in ("customer", "driver", "merchant_owner"):
        if persona in roles:
            assert "mfa_required" not in json.dumps(roles[persona])
    flows = {f["alias"]: f for f in realm["authenticationFlows"]}
    otp_flows = [a for a, f in flows.items()
                 if any(e.get("authenticator") == "auth-otp-form" for e in f["authenticationExecutions"])]
    assert otp_flows == ["pc-staff-otp"], otp_flows


_RUNTIME_ROOTS = ("apps/api/src", "apps/admin/src", "apps/customer/src", "apps/merchant-portal/src",
                  "apps/driver-portal/src", "apps/mobile-customer/src", "apps/mobile-driver/src",
                  "website/src", "packages/auth/src", "packages/config", "shared/python")


@pytest.mark.tc_id("A-APR-08")
def test_a_apr_08_no_clerk_in_runtime_code() -> None:
    hits = []
    for root in _RUNTIME_ROOTS:
        for p in (REPO / root).rglob("*"):
            if p.suffix not in {".py", ".ts", ".tsx", ".mjs", ".js", ".json"} or not p.is_file():
                continue
            if any(part in {"node_modules", "__pycache__", ".next"} for part in p.parts):
                continue
            if p.name in {"security-headers.test.mjs", "no-login-loop.test.ts"}:
                continue  # guards that assert Clerk is absent
            if re.search(r"clerk", p.read_text(errors="ignore"), re.I):
                hits.append(str(p.relative_to(REPO)))
    assert hits == [], hits
    for app in ("mobile-customer", "mobile-driver", "website"):
        pkg = json.loads((REPO / f"apps/{app}/package.json" if app != "website" else REPO / "website/package.json").read_text())
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        assert not [d for d in deps if d.startswith("@clerk/")], app

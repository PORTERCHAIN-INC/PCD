"""L36 integration: real tokens from the THROWAWAY Keycloak (scripts/test-keycloak.sh, :18180).

Skipped unless PCD_TEST_KEYCLOAK_URL is set. Never points at pch-keycloak (8180/8543).
Adds a test-only direct-grant client at runtime (not part of realm-as-code).
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from porterchain_api.auth import keycloak as kc
from porterchain_api.config import Settings

BASE = os.environ.get("PCD_TEST_KEYCLOAK_URL", "").rstrip("/")
pytestmark = pytest.mark.skipif(not BASE, reason="PCD_TEST_KEYCLOAK_URL not set")
if BASE and any(p in BASE for p in (":8180", ":8543")):
    raise RuntimeError("refusing to run against the live pch-keycloak ports")


def _admin(client: httpx.Client) -> dict:
    tok = client.post(f"{BASE}/realms/master/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": "admin-cli", "username": "admin",
        "password": os.environ.get("PCD_TEST_KEYCLOAK_ADMIN_PASSWORD", "test-admin-only")}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def realm_user():
    with httpx.Client(timeout=20) as c:
        h = _admin(c)
        adm = f"{BASE}/admin/realms/porterchain"
        cid = "pc-test-direct"
        if not c.get(f"{adm}/clients?clientId={cid}", headers=h).json():
            c.post(f"{adm}/clients", headers=h, json={
                "clientId": cid, "publicClient": True, "directAccessGrantsEnabled": True,
                "standardFlowEnabled": False})
            internal = c.get(f"{adm}/clients?clientId={cid}", headers=h).json()[0]["id"]
            ref = c.get(f"{adm}/clients?clientId=pc-driver-app", headers=h).json()[0]
            for m in ref.get("protocolMappers", []):
                m.pop("id", None)
                c.post(f"{adm}/clients/{internal}/protocol-mappers/models", headers=h, json=m)
        email = f"it-{uuid.uuid4().hex[:8]}@example.test"
        pw = uuid.uuid4().hex + "Aa1!"
        c.post(f"{adm}/users", headers=h, json={"username": email, "email": email, "enabled": True,
                                                "emailVerified": True, "requiredActions": []})
        uid = c.get(f"{adm}/users?email={email}&exact=true", headers=h).json()[0]["id"]
        c.put(f"{adm}/users/{uid}/reset-password", headers=h, json={"type": "password", "value": pw, "temporary": False})
        role = c.get(f"{adm}/roles/driver", headers=h).json()
        c.post(f"{adm}/users/{uid}/role-mappings/realm", headers=h, json=[role])
        yield {"id": uid, "email": email, "password": pw, "client": cid}
        c.delete(f"{adm}/users/{uid}", headers=_admin(c))


def _password_token(u: dict) -> str:
    r = httpx.post(f"{BASE}/realms/porterchain/protocol/openid-connect/token", data={
        "grant_type": "password", "client_id": u["client"], "username": u["email"],
        "password": u["password"], "scope": "openid"}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def test_realm_as_code_imported():
    with httpx.Client(timeout=20) as c:
        h = _admin(c)
        realm = c.get(f"{BASE}/admin/realms/porterchain", headers=h).json()
        assert realm["bruteForceProtected"] is True
        assert realm["browserFlow"] == "pc-browser"
        clients = {x["clientId"]: x for x in c.get(f"{BASE}/admin/realms/porterchain/clients", headers=h).json()}
        for cid in ("pc-website", "pc-merchant-portal", "pc-admin", "pc-api", "pc-customer-app", "pc-driver-app"):
            assert cid in clients
        assert clients["pc-customer-app"]["attributes"]["pkce.code.challenge.method"] == "S256"
        assert clients["pc-customer-app"]["redirectUris"] == ["porterchain-customer://auth"]
        assert clients["pc-admin"]["directAccessGrantsEnabled"] is False
        assert {"aud-pc-api", "pc-roles"} <= {m["name"] for m in clients["pc-customer-app"]["protocolMappers"]}
        app_scopes = c.get(f"{BASE}/admin/realms/porterchain/clients/{clients['pc-customer-app']['id']}/default-client-scopes", headers=h).json()
        assert {"basic", "email", "profile", "roles"} <= {s["name"] for s in app_scopes}
        admin_role = c.get(f"{BASE}/admin/realms/porterchain/roles/super_admin/composites", headers=h).json()
        assert "mfa_required" in {r["name"] for r in admin_role}
        idps = {i["alias"] for i in c.get(f"{BASE}/admin/realms/porterchain/identity-provider/instances", headers=h).json()}
        assert "google" in idps


@pytest.mark.asyncio
async def test_real_keycloak_token_verifies(realm_user):
    token = _password_token(realm_user)
    s = Settings(keycloak_url=BASE, keycloak_allowed_clients="pc-test-direct")
    claims = await kc.verify_keycloak_token(token, s)
    assert claims.clerk_user_id == realm_user["id"]
    assert claims.email == realm_user["email"]
    assert "driver" in claims.public_metadata["roles"]


@pytest.mark.asyncio
async def test_real_token_rejected_for_unlisted_client(realm_user):
    from fastapi import HTTPException

    token = _password_token(realm_user)
    with pytest.raises(HTTPException):
        await kc.verify_keycloak_token(token, Settings(keycloak_url=BASE))

"""L36: Keycloak JWT verification (unit, self-signed RSA JWKS) — the only auth provider."""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from porterchain_api.auth import keycloak as kc
from porterchain_api.config import Settings

ISS = "https://auth.example.test/realms/porterchain"


@pytest.fixture()
def keypair(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(key.public_key(), as_dict=True) | {"kid": "k1", "use": "sig", "alg": "RS256"}

    async def fake(url, *, force=False):
        assert url == f"{ISS}/protocol/openid-connect/certs"
        return {"keys": [jwk]}

    monkeypatch.setattr(kc, "_fetch_jwks", fake)
    return key


def _settings(**kw) -> Settings:
    return Settings(keycloak_issuer=ISS, **kw)


def _token(key, **over):
    now = int(time.time())
    payload = {"iss": ISS, "sub": "kc-user-1", "aud": ["pc-api"], "azp": "pc-merchant-portal",
               "exp": now + 300, "iat": now, "auth_time": now, "typ": "Bearer", "sid": "s1",
               "email": "Owner@Example.com", "email_verified": True,
               "pc_roles": ["merchant_owner", "default-roles-porterchain"], "org_id": "org-9"}
    payload.update(over)
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": over.pop("_kid", "k1")})


@pytest.mark.asyncio
async def test_valid_token_maps_sub_roles_org(keypair):
    c = await kc.verify_keycloak_token(_token(keypair), _settings())
    assert c.auth_subject == "kc-user-1"
    assert c.email == "owner@example.com"
    assert c.org_id == "org-9"
    assert c.metadata_role == "merchant_owner"
    assert c.idp_app == "merchant"
    assert c.issuer == ISS and c.authorized_party == "pc-merchant-portal"


@pytest.mark.asyncio
@pytest.mark.parametrize("over,detail", [
    ({"iss": "https://evil/realms/porterchain"}, "invalid_token"),
    ({"aud": ["other"]}, "invalid_token"),
    ({"exp": int(time.time()) - 120}, "invalid_token"),
    ({"azp": "random-client"}, "invalid_token_azp"),
    ({"typ": "Refresh"}, "invalid_token_type"),
])
async def test_rejects_bad_tokens(keypair, over, detail):
    with pytest.raises(HTTPException) as ei:
        await kc.verify_keycloak_token(_token(keypair, **over), _settings())
    assert ei.value.status_code == 401 and ei.value.detail == detail


@pytest.mark.asyncio
async def test_rejects_foreign_signing_key(keypair):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as ei:
        await kc.verify_keycloak_token(_token(other), _settings())
    assert ei.value.status_code == 401


@pytest.mark.asyncio
async def test_unconfigured_is_503():
    with pytest.raises(HTTPException) as ei:
        await kc.verify_keycloak_token("x.y.z", Settings(keycloak_issuer="", keycloak_url=""))
    assert ei.value.status_code == 503


def test_auth_provider_is_keycloak_only():
    assert Settings().auth_provider == "keycloak"
    with pytest.raises(Exception):
        Settings(auth_provider="clerk")


def test_issuer_from_url_and_realm():
    s = Settings(keycloak_url="https://auth.porterchain.com/", keycloak_realm="porterchain")
    assert kc.keycloak_issuer(s) == "https://auth.porterchain.com/realms/porterchain"
    s2 = Settings(keycloak_url="https://auth.porterchain.com", keycloak_internal_url="http://keycloak:8080")
    assert kc.keycloak_jwks_url(s2) == "http://keycloak:8080/realms/porterchain/protocol/openid-connect/certs"


@pytest.mark.asyncio
async def test_hs256_alg_confusion_rejected(keypair):
    forged = jwt.encode({"iss": ISS, "sub": "attacker", "exp": int(time.time()) + 60, "iat": int(time.time())},
                        "secret-" + "x" * 40, algorithm="HS256", headers={"kid": "k1"})
    with pytest.raises(HTTPException) as ei:
        await kc.verify_keycloak_token(forged, _settings())
    assert ei.value.status_code == 401

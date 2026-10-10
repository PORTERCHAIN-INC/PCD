"""PyJWT migration (python-jose removed): Clerk RS256 JWKS verify + driver HS256 tokens."""

from __future__ import annotations

import asyncio
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from porterchain_api.auth import clerk_identity_provider as cip
from porterchain_api.config import Settings
from porterchain_driver.auth_tokens import DRIVER_TOKEN_AUD, decode_driver_token


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "local",
        "clerk_dev_bypass": False,
        "jwt_secret": "b" * 48,
        "database_url": "postgresql+psycopg://u:p@h/d",
        "clerk_authorized_issuers": "",
        "clerk_authorized_parties": "",
        "clerk_audience": "",
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


@pytest.fixture
def rsa_pair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    pub.update({"kid": "kid-1", "alg": "RS256", "use": "sig"})
    return key, {"keys": [pub]}


@pytest.fixture
def patched_jwks(monkeypatch, rsa_pair):
    _key, jwks = rsa_pair

    async def _fake_jwks(_url: str) -> dict:
        return jwks

    monkeypatch.setattr(cip, "_get_jwks", _fake_jwks)
    monkeypatch.setattr(cip, "clerk_jwks_urls", lambda _s: [("merchant", "https://example.invalid/jwks")])
    monkeypatch.setattr(
        "porterchain_api.auth.email_identity.enrich_claims_with_verified_email", lambda claims, _s: claims
    )
    return rsa_pair


def _token(key, *, kid="kid-1", **claims) -> str:
    now = int(time.time())
    payload = {"sub": "user_123", "iss": "https://clerk.example", "iat": now, "nbf": now - 5, "exp": now + 300}
    payload.update(claims)
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": kid})


def test_valid_rs256_token_verifies(patched_jwks):
    key, _ = patched_jwks
    claims = asyncio.run(cip.verify_clerk_token(_token(key, email="a@b.co", azp="https://m.example"), _settings()))
    assert claims.clerk_user_id == "user_123"
    assert claims.clerk_app == "merchant"
    assert claims.authorized_party == "https://m.example"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda key: _token(key, exp=int(time.time()) - 60),  # expired
        lambda key: _token(key, kid="unknown"),  # unknown kid
        lambda key: _token(rsa.generate_private_key(public_exponent=65537, key_size=2048)),  # wrong signer
        lambda key: "not-a-jwt",
    ],
)
def test_bad_tokens_are_401(patched_jwks, mutate):
    key, _ = patched_jwks
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cip.verify_clerk_token(mutate(key), _settings()))
    assert exc.value.status_code == 401


def test_audience_enforced_when_configured(patched_jwks):
    key, _ = patched_jwks
    settings = _settings(clerk_audience="pcd-api")
    ok = asyncio.run(cip.verify_clerk_token(_token(key, aud="pcd-api"), settings))
    assert ok.clerk_user_id == "user_123"
    with pytest.raises(HTTPException):
        asyncio.run(cip.verify_clerk_token(_token(key, aud="other"), settings))


def test_hs256_none_alg_confusion_rejected(patched_jwks):
    """A token signed HS256 with the public key material must never verify."""
    _key, jwks = patched_jwks
    forged = jwt.encode({"sub": "attacker", "exp": int(time.time()) + 60}, "secret-" + "x" * 40, algorithm="HS256", headers={"kid": "kid-1"})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cip.verify_clerk_token(forged, _settings()))
    assert exc.value.status_code == 401


def test_driver_token_roundtrip_and_audience():
    secret = "s" * 48
    now = int(time.time())
    good = jwt.encode({"driver_id": "d1", "type": "access", "aud": DRIVER_TOKEN_AUD, "exp": now + 60}, secret, algorithm="HS256")
    assert decode_driver_token(good, secret=secret)["driver_id"] == "d1"
    wrong_aud = jwt.encode({"driver_id": "d1", "type": "access", "aud": "x", "exp": now + 60}, secret, algorithm="HS256")
    with pytest.raises(jwt.PyJWTError):
        decode_driver_token(wrong_aud, secret=secret)
    refresh = jwt.encode({"driver_id": "d1", "type": "refresh", "aud": DRIVER_TOKEN_AUD, "exp": now + 60}, secret, algorithm="HS256")
    with pytest.raises(ValueError):
        decode_driver_token(refresh, secret=secret)

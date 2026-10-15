"""Clerk webhooks from Platform and Porterchain Driver instances (separate signing secrets)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from porterchain_api.auth import clerk_webhook_service as svc

P_SECRET = "whsec_" + base64.b64encode(b"platform-secret-bytes-0123456789").decode()
D_SECRET = "whsec_" + base64.b64encode(b"driver-secret-bytes-012345678901").decode()


def _sign(secret: str, msg_id: str, ts: str, body: bytes) -> str:
    key = base64.b64decode(secret[len("whsec_") :])
    sig = hmac.new(key, f"{msg_id}.{ts}.{body.decode()}".encode(), hashlib.sha256).digest()
    return "v1," + base64.b64encode(sig).decode()


def _settings(**kw):
    base = dict(
        clerk_webhook_signing_secret=P_SECRET,
        clerk_driver_webhook_signing_secret=D_SECRET,
        clerk_jwks_url="https://clerk.admin.porterchain.com/.well-known/jwks.json",
        clerk_admin_jwks_url="",
        clerk_driver_jwks_url="https://clerk.driver.porterchain.com/.well-known/jwks.json",
        clerk_authorized_issuers="",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class _DB:
    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def captured(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(svc, "claim_clerk_event", lambda db, **k: True)
    monkeypatch.setattr(svc, "complete_clerk_event", lambda db, **k: None)
    monkeypatch.setattr(svc, "release_clerk_event", lambda db, **k: None)

    def fake_ensure(self, db, **k):
        seen.update(k)

    monkeypatch.setattr(svc.EnsureUserService, "ensure_from_clerk_user_payload", fake_ensure)
    return seen


def _call(secret: str | None, settings, body: dict | None = None):
    payload = json.dumps(body or {"type": "user.updated", "data": {"id": "user_1", "email_addresses": []}}).encode()
    ts = str(int(time.time()))
    sig = _sign(secret, "msg_1", ts, payload) if secret else "v1,AAAA"
    return svc.ClerkWebhookService().handle(
        _DB(), settings, payload=payload, svix_id="msg_1", svix_timestamp=ts, svix_signature=sig
    )


def test_platform_secret_accepted_and_platform_issuer(captured):
    assert _call(P_SECRET, _settings())["status"] == "ok"
    assert captured["issuer"] == "https://clerk.admin.porterchain.com"


def test_driver_secret_accepted_and_driver_issuer(captured):
    assert _call(D_SECRET, _settings())["status"] == "ok"
    assert captured["issuer"] == "https://clerk.driver.porterchain.com"


def test_bad_signature_rejected(captured):
    with pytest.raises(HTTPException) as e:
        _call(None, _settings())
    assert e.value.status_code == 400


def test_driver_signature_rejected_when_driver_secret_missing(captured):
    with pytest.raises(HTTPException) as e:
        _call(D_SECRET, _settings(clerk_driver_webhook_signing_secret=""))
    assert e.value.status_code == 400


def test_not_configured_is_503(captured):
    with pytest.raises(HTTPException) as e:
        _call(P_SECRET, _settings(clerk_webhook_signing_secret="", clerk_driver_webhook_signing_secret=""))
    assert e.value.status_code == 503


def test_driver_only_secret_works(captured):
    assert _call(D_SECRET, _settings(clerk_webhook_signing_secret=""))["status"] == "ok"

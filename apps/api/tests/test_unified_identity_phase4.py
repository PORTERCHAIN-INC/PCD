"""Phase 4 — Clerk webhooks, ensure-user, no elevation, deactivate."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.auth.clerk_webhook_idempotency import claim_clerk_event
from porterchain_api.auth.clerk_webhook_service import ClerkWebhookService
from porterchain_api.auth.clerk_webhook_verify import (
    ClerkWebhookSignatureError,
    verify_clerk_webhook_signature,
)
from porterchain_api.auth.ensure_user_service import EnsureUserService
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.unified_catalog import AccountStatus, AssignableRole, is_invite_only
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.config import Settings
from porterchain_api.user_models import PorterchainUser


def _whsec_secret() -> tuple[str, bytes]:
    key = b"phase4-test-signing-key-32bytes!!"
    return "whsec_" + base64.b64encode(key).decode(), key


def _sign(payload: bytes, *, key: bytes, svix_id: str, ts: str) -> str:
    signed = f"{svix_id}.{ts}.{payload.decode()}".encode()
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def test_verify_clerk_webhook_signature_ok() -> None:
    secret, key = _whsec_secret()
    payload = b'{"type":"user.created"}'
    svix_id = "msg_test_1"
    ts = str(int(time.time()))
    sig = _sign(payload, key=key, svix_id=svix_id, ts=ts)
    verify_clerk_webhook_signature(
        payload=payload,
        secret=secret,
        svix_id=svix_id,
        svix_timestamp=ts,
        svix_signature=sig,
    )


def test_verify_clerk_webhook_signature_rejects_bad_sig() -> None:
    secret, _key = _whsec_secret()
    with pytest.raises(ClerkWebhookSignatureError):
        verify_clerk_webhook_signature(
            payload=b"{}",
            secret=secret,
            svix_id="msg_1",
            svix_timestamp=str(int(time.time())),
            svix_signature="v1,notavalidsignature",
        )


def test_ensure_user_never_grants_invite_only_from_identity_alone() -> None:
    db = MagicMock()
    # No existing user / link / legacy profiles
    empty = MagicMock()
    empty.filter.return_value.first.return_value = None
    empty.filter.return_value.all.return_value = []
    db.query.return_value = empty

    created: list[PorterchainUser] = []

    def add(obj):
        if isinstance(obj, PorterchainUser):
            obj.id = "new-user-id"
            created.append(obj)

    db.add.side_effect = add

    identity = AuthenticatedIdentity(
        provider="clerk",
        issuer="https://clerk.example",
        subject="user_meta_admin",
        email="someone@example.com",
        email_verified=True,
        adapter_context={"clerk_app": "admin"},
    )
    # Simulate public_metadata temptation via email domain — ensure must ignore
    user = EnsureUserService().ensure_from_identity(db, identity, email_verified=True, commit=False)
    assert user.role == "unprovisioned"
    assert user.status == AccountStatus.PENDING.value
    assert not is_invite_only(AssignableRole.CUSTOMER)
    assert is_invite_only(AssignableRole.ADMIN)
    assert is_invite_only(AssignableRole.SUPER_ADMIN)


def test_user_sync_unprovisioned_ignores_metadata_role() -> None:
    svc = UserSyncService()
    claims = ClerkClaims(
        clerk_user_id="user_x",
        email="x@example.com",
        public_metadata={"role": "super_admin"},
        org_role="admin",
    )
    snap = svc._platform_snapshot(MagicMock(), claims, None)
    assert snap["role"] == "unprovisioned"
    assert snap["status"] == "pending"


def test_deactivate_does_not_delete_user_row() -> None:
    db = MagicMock()
    user = PorterchainUser(
        id="u1",
        clerk_user_id="clerk_del",
        email="d@example.com",
        role="customer",
        status=AccountStatus.ACTIVE.value,
        onboarding_status="complete",
        profile={},
    )
    link = MagicMock()
    link.deactivated_at = None
    link.is_current = True

    user_q = MagicMock()
    user_q.filter.return_value.first.return_value = user
    link_q = MagicMock()
    link_q.filter.return_value.all.return_value = [link]

    def query(model):
        name = getattr(model, "__name__", str(model))
        if "PorterchainUser" in name or model is PorterchainUser:
            return user_q
        return link_q

    db.query.side_effect = query
    EnsureUserService().deactivate_clerk_user(db, clerk_user_id="clerk_del", commit=False)
    assert user.status == AccountStatus.DEACTIVATED.value
    assert link.is_current is False
    assert link.deactivated_at is not None
    db.delete.assert_not_called()


def test_webhook_requires_secret() -> None:
    settings = Settings(
        _env_file=None,
        jwt_secret="a" * 32,
        clerk_webhook_signing_secret="",
        clerk_secret_key="",
        clerk_jwks_url="",
        clerk_customer_secret_key="",
        clerk_customer_jwks_url="",
        clerk_merchant_secret_key="",
        clerk_merchant_jwks_url="",
        clerk_admin_secret_key="",
        clerk_admin_jwks_url="",
        clerk_driver_secret_key="",
        clerk_driver_jwks_url="",
    )
    with pytest.raises(HTTPException) as exc:
        ClerkWebhookService().handle(
            MagicMock(),
            settings,
            payload=b"{}",
            svix_id="msg_1",
            svix_timestamp=str(int(time.time())),
            svix_signature="v1,x",
        )
    assert exc.value.status_code == 503


def test_webhook_duplicate_returns_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    secret, key = _whsec_secret()
    settings = Settings(
        _env_file=None,
        jwt_secret="a" * 32,
        clerk_webhook_signing_secret=secret,
        clerk_secret_key="",
        clerk_jwks_url="",
        clerk_customer_secret_key="",
        clerk_customer_jwks_url="",
        clerk_merchant_secret_key="",
        clerk_merchant_jwks_url="",
        clerk_admin_secret_key="",
        clerk_admin_jwks_url="",
        clerk_driver_secret_key="",
        clerk_driver_jwks_url="",
    )
    body = {
        "type": "user.created",
        "data": {
            "id": "user_abc",
            "email_addresses": [
                {
                    "id": "em_1",
                    "email_address": "new@example.com",
                    "verification": {"status": "verified"},
                }
            ],
            "primary_email_address_id": "em_1",
        },
    }
    payload = json.dumps(body).encode()
    svix_id = "msg_dup_1"
    ts = str(int(time.time()))
    sig = _sign(payload, key=key, svix_id=svix_id, ts=ts)

    monkeypatch.setattr(
        "porterchain_api.auth.clerk_webhook_service.claim_clerk_event",
        lambda *a, **k: False,
    )
    db = MagicMock()
    result = ClerkWebhookService().handle(
        db,
        settings,
        payload=payload,
        svix_id=svix_id,
        svix_timestamp=ts,
        svix_signature=sig,
    )
    assert result == {"status": "duplicate"}

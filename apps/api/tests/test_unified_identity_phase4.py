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

from porterchain_api.auth.ensure_user_service import EnsureUserService
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.unified_catalog import AccountStatus, AssignableRole, is_invite_only
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.config import Settings
from porterchain_api.user_models import PorterchainUser


def _whsec_secret() -> tuple[str, bytes]:
    key = b"phase4-test-signing-key-32bytes!!"
    return "whsec_" + base64.b64encode(key).decode(), key


def _sign(payload: bytes, *, key: bytes, svix_id: str, ts: str) -> str:
    signed = f"{svix_id}.{ts}.{payload.decode()}".encode()
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


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
    claims = IdentityClaims(
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

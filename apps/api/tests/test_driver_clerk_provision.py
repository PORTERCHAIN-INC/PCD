"""Admin-created drivers get a Clerk user directly (no invite link)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.auth import invitation_service as inv_mod
from porterchain_api.auth.clerk_client import ClerkInviteResult
from porterchain_api.auth.invitation_service import InvitationService


class FakeClerk:
    def __init__(self, existing: dict | None = None, fail: bool = False) -> None:
        self.existing = existing
        self.fail = fail
        self.created: list[dict] = []
        self.metadata_updates: list[tuple[str, dict]] = []
        self.revoked: list[str] = []
        self.invited: list[str] = []

    def find_user_by_email(self, email: str):
        if self.fail:
            raise RuntimeError("clerk down")
        return self.existing

    def update_user_metadata(self, uid: str, md: dict) -> None:
        self.metadata_updates.append((uid, md))

    def create_user(self, email: str, **kw):
        self.created.append({"email": email, **kw})
        return {"id": "user_new"}

    def revoke_pending_invitations(self, email: str) -> int:
        self.revoked.append(email)
        return 1

    def invite_user(self, email: str, **kw):
        self.invited.append(email)
        return ClerkInviteResult(action="invited", clerk_invitation_id="inv_x")


def _setup(monkeypatch, clerk: FakeClerk, pending_rows=()):
    monkeypatch.setattr(inv_mod, "clerk_client_for_kind", lambda s, k: clerk)
    monkeypatch.setattr(inv_mod, "log_admin_audit", lambda *a, **k: None)
    import porterchain_api.auth.authz_sync as authz

    monkeypatch.setattr(authz, "sync_authz_after_persona_mutation", lambda db, uid: None)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = list(pending_rows)
    added: list = []
    db.add.side_effect = added.append
    settings = SimpleNamespace(driver_portal_url="https://driver.porterchain.com/")
    driver = SimpleNamespace(
        id="drv1", email="  Abdul.Test@Gmail.com ", full_name="Abdul Salim", clerk_user_id=None
    )
    return db, settings, driver, added


def test_creates_clerk_user_without_password(monkeypatch) -> None:
    clerk = FakeClerk()
    db, settings, driver, added = _setup(monkeypatch, clerk)
    inv = InvitationService().provision_driver_account(db, None, settings, driver)
    assert driver.clerk_user_id == "user_new"
    c = clerk.created[0]
    assert c["email"] == "abdul.test@gmail.com"
    assert c["skip_password_requirement"] is True
    assert "password" not in c
    assert c["public_metadata"]["role"] == "driver"
    assert c["public_metadata"]["driver_id"] == "drv1"
    assert clerk.revoked == ["abdul.test@gmail.com"]
    assert inv.status == "accepted"
    assert inv.invitation_metadata["clerk_action"] == "created"
    assert clerk.invited == []


def test_links_existing_clerk_user_idempotently(monkeypatch) -> None:
    clerk = FakeClerk(existing={"id": "user_old"})
    db, settings, driver, _ = _setup(monkeypatch, clerk)
    InvitationService().provision_driver_account(db, None, settings, driver)
    assert driver.clerk_user_id == "user_old"
    assert clerk.created == []
    assert clerk.metadata_updates[0][0] == "user_old"


def test_closes_local_pending_invites(monkeypatch) -> None:
    row = SimpleNamespace(status="pending", clerk_user_id=None, accepted_at=None)
    db, settings, driver, _ = _setup(monkeypatch, FakeClerk(), pending_rows=[row])
    InvitationService().provision_driver_account(db, None, settings, driver)
    assert row.status == "accepted"
    assert row.clerk_user_id == "user_new"
    assert row.accepted_at is not None


def test_falls_back_to_invite_when_clerk_fails(monkeypatch) -> None:
    clerk = FakeClerk(fail=True)
    db, settings, driver, _ = _setup(monkeypatch, clerk)
    clerk.find_user_by_email = FakeClerk().find_user_by_email  # invite path lookup ok
    svc = InvitationService()
    called = {}

    def fake_invite(db_, ctx_, settings_, driver_):
        called["yes"] = True
        return SimpleNamespace(status="pending")

    monkeypatch.setattr(svc, "invite_driver", fake_invite)
    clerk.create_user = MagicMock(side_effect=RuntimeError("clerk 500"))
    inv = svc.provision_driver_account(db, None, settings, driver)
    assert called.get("yes") is True
    assert inv.status == "pending"
    assert driver.clerk_user_id is None


@pytest.mark.parametrize("revoke_raises", [True])
def test_revoke_failure_does_not_block(monkeypatch, revoke_raises) -> None:
    clerk = FakeClerk()
    clerk.revoke_pending_invitations = MagicMock(side_effect=RuntimeError("x"))
    db, settings, driver, _ = _setup(monkeypatch, clerk)
    InvitationService().provision_driver_account(db, None, settings, driver)
    assert driver.clerk_user_id == "user_new"

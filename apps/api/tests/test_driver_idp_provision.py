"""Admin-created drivers get a Keycloak user directly (no invite link)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.auth import invitation_service as inv_mod
from porterchain_api.auth.identity_directory import InviteResult
from porterchain_api.auth.invitation_service import InvitationService


class FakeIdp:
    def __init__(self, existing: dict | None = None, fail: bool = False) -> None:
        self.existing = existing
        self.fail = fail
        self.created: list[dict] = []
        self.metadata_updates: list[tuple[str, dict]] = []
        self.revoked: list[str] = []
        self.invited: list[str] = []

    def find_user_by_email(self, email: str):
        if self.fail:
            raise RuntimeError("keycloak down")
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
        return InviteResult(action="invited", invitation_id="inv_x")


def _setup(monkeypatch, keycloak: FakeIdp, pending_rows=()):
    monkeypatch.setattr(inv_mod, "directory_for_kind", lambda s, k: keycloak)
    monkeypatch.setattr(inv_mod, "log_admin_audit", lambda *a, **k: None)
    import porterchain_api.auth.authz_sync as authz

    monkeypatch.setattr(authz, "sync_authz_after_persona_mutation", lambda db, uid: None)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = list(pending_rows)
    added: list = []
    db.add.side_effect = added.append
    settings = SimpleNamespace(driver_portal_url="https://driver.porterchain.com/")
    driver = SimpleNamespace(
        id="drv1", email="  Abdul.Test@Gmail.com ", full_name="Abdul Salim", auth_subject=None
    )
    return db, settings, driver, added


def test_creates_idp_user_without_password(monkeypatch) -> None:
    keycloak = FakeIdp()
    db, settings, driver, added = _setup(monkeypatch, keycloak)
    inv = InvitationService().provision_driver_account(db, None, settings, driver)
    assert driver.auth_subject == "user_new"
    c = keycloak.created[0]
    assert c["email"] == "abdul.test@gmail.com"
    assert c["skip_password_requirement"] is True
    assert "password" not in c
    assert c["public_metadata"]["role"] == "driver"
    assert c["public_metadata"]["driver_id"] == "drv1"
    assert keycloak.revoked == ["abdul.test@gmail.com"]
    assert inv.status == "accepted"
    assert inv.invitation_metadata["identity_action"] == "created"
    assert keycloak.invited == []


def test_links_existing_idp_user_idempotently(monkeypatch) -> None:
    keycloak = FakeIdp(existing={"id": "user_old"})
    db, settings, driver, _ = _setup(monkeypatch, keycloak)
    InvitationService().provision_driver_account(db, None, settings, driver)
    assert driver.auth_subject == "user_old"
    assert keycloak.created == []
    assert keycloak.metadata_updates[0][0] == "user_old"


def test_closes_local_pending_invites(monkeypatch) -> None:
    row = SimpleNamespace(status="pending", auth_subject=None, accepted_at=None)
    db, settings, driver, _ = _setup(monkeypatch, FakeIdp(), pending_rows=[row])
    InvitationService().provision_driver_account(db, None, settings, driver)
    assert row.status == "accepted"
    assert row.auth_subject == "user_new"
    assert row.accepted_at is not None


def test_falls_back_to_invite_when_idp_fails(monkeypatch) -> None:
    keycloak = FakeIdp(fail=True)
    db, settings, driver, _ = _setup(monkeypatch, keycloak)
    keycloak.find_user_by_email = FakeIdp().find_user_by_email  # invite path lookup ok
    svc = InvitationService()
    called = {}

    def fake_invite(db_, ctx_, settings_, driver_):
        called["yes"] = True
        return SimpleNamespace(status="pending")

    monkeypatch.setattr(svc, "invite_driver", fake_invite)
    keycloak.create_user = MagicMock(side_effect=RuntimeError("keycloak 500"))
    inv = svc.provision_driver_account(db, None, settings, driver)
    assert called.get("yes") is True
    assert inv.status == "pending"
    assert driver.auth_subject is None


@pytest.mark.parametrize("revoke_raises", [True])
def test_revoke_failure_does_not_block(monkeypatch, revoke_raises) -> None:
    keycloak = FakeIdp()
    keycloak.revoke_pending_invitations = MagicMock(side_effect=RuntimeError("x"))
    db, settings, driver, _ = _setup(monkeypatch, keycloak)
    InvitationService().provision_driver_account(db, None, settings, driver)
    assert driver.auth_subject == "user_new"

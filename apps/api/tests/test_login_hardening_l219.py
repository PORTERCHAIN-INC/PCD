"""L219: Resend invite re-sends the setup email to users who never finished setup."""
from __future__ import annotations

from unittest.mock import MagicMock

from porterchain_api.auth.identity_directory import IdentityDirectory
from porterchain_api.config import Settings


def _dir(rep):
    kc = MagicMock()
    kc.find_user.return_value = rep
    kc._call.return_value = MagicMock(status_code=200, json=lambda: rep)
    kc.send_actions_email.return_value = True
    return IdentityDirectory(Settings(), admin=kc), kc


def test_resend_to_unfinished_user_sends_email():
    d, kc = _dir({"id": "u1", "username": "x@y.test", "email": "x@y.test",
                  "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD"]})
    res = d.invite_user("X@y.test ", redirect_url="http://d/login", metadata={"role": "driver"}, kind="driver")
    kc.send_actions_email.assert_called_once()
    assert kc.send_actions_email.call_args.args[1] == ["VERIFY_EMAIL", "UPDATE_PASSWORD"]
    assert kc.send_actions_email.call_args.kwargs["client_id"] == "pc-driver-portal"
    assert res.action == "invited"


def test_existing_active_user_gets_no_email():
    d, kc = _dir({"id": "u1", "username": "x@y.test", "email": "x@y.test", "requiredActions": []})
    res = d.invite_user("x@y.test", redirect_url="http://d/login", metadata={}, kind="driver")
    kc.send_actions_email.assert_not_called()
    assert res.action == "found"


def test_metadata_update_keeps_username_and_email():
    d, kc = _dir({"id": "u1", "username": "x@y.test", "email": "x@y.test", "attributes": {}})
    d.update_user("u1", metadata={"role": "driver"})
    put = [c for c in kc._call.call_args_list if c.args[0] == "PUT"][0]
    assert put.kwargs["json"]["username"] == "x@y.test"
    assert put.kwargs["json"]["email"] == "x@y.test"


# L220: staff deactivate / reactivate
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

from porterchain_api.admin_engine import staff_accounts  # noqa: E402


def _db(user, other_supers=1):
    db = MagicMock()
    q = db.query.return_value
    q.filter.return_value.first.return_value = user
    q.filter.return_value.count.return_value = other_supers
    return db


def _svc():
    return next(v for v in vars(staff_accounts).values() if isinstance(v, type) and hasattr(v, "set_active"))()


def test_deactivate_staff_disables_login(monkeypatch):
    user = SimpleNamespace(id="s2", email="s@x.test", role="read_only", is_active=True, name=None)
    calls = {}
    monkeypatch.setattr(staff_accounts, "log_admin_audit", lambda *a, **k: None)
    monkeypatch.setattr(staff_accounts.keycloak_admin, "end_staff_sessions",
                        lambda s, e, disable=False: calls.setdefault("disable", (e, disable)) and True)
    out = _svc().set_active(_db(user), SimpleNamespace(user=SimpleNamespace(id="s1")), Settings(), "s2", False)
    assert user.is_active is False and out["is_active"] is False
    assert calls["disable"] == ("s@x.test", True)


def test_cannot_deactivate_self_or_last_super_admin(monkeypatch):
    monkeypatch.setattr(staff_accounts, "log_admin_audit", lambda *a, **k: None)
    me = SimpleNamespace(id="s1", email="me@x.test", role="super_admin", is_active=True, name=None)
    with pytest.raises(ValueError, match="cannot_deactivate_self"):
        _svc().set_active(_db(me), SimpleNamespace(user=me), Settings(), "s1", False)
    with pytest.raises(ValueError, match="last_super_admin"):
        _svc().set_active(_db(me, other_supers=0), SimpleNamespace(user=SimpleNamespace(id="s9")), Settings(), "s1", False)

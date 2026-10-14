"""Owner must never get a false 403 while tuples reconcile or SpiceDB blips."""

from __future__ import annotations

import threading
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from porterchain_api.authz.client import AuthzClient, Relationship


def _client() -> AuthzClient:
    return AuthzClient(enabled=False, required=False, endpoint="", preshared_key="", use_memory=True)


def test_replace_relationships_is_atomic_for_concurrent_checks() -> None:
    c = _client()
    owner = Relationship("platform", "porterchain", "super_admin", "user", "u1")
    c.write_relationships([owner])
    stale = [Relationship("platform", "porterchain", r, "user", "u1") for r in ("admin", "ops", "super_admin")]
    stop = threading.Event()
    denies: list[int] = []

    def reader() -> None:
        while not stop.is_set():
            if not c.check(resource_type="platform", resource_id="porterchain", permission="portal", subject_id="u1"):
                denies.append(1)

    t = threading.Thread(target=reader)
    t.start()
    for _ in range(2000):
        c.replace_relationships(stale, [owner])
    stop.set()
    t.join()
    assert denies == []
    assert c.check(resource_type="platform", resource_id="porterchain", permission="portal", subject_id="u1")


def test_replace_relationships_drops_stale_roles() -> None:
    c = _client()
    c.write_relationships([Relationship("platform", "porterchain", "super_admin", "user", "u2")])
    c.replace_relationships(
        [Relationship("platform", "porterchain", "super_admin", "user", "u2")],
        [],
    )
    assert not c.check(resource_type="platform", resource_id="porterchain", permission="portal", subject_id="u2")


class _Broken:
    def check(self, **_):
        raise RuntimeError("spicedb down")


def test_require_module_spicedb_error_is_503_not_403(monkeypatch) -> None:
    from porterchain_api.admin_engine import rbac

    monkeypatch.setattr("porterchain_api.authz.client.get_authz_client", lambda: _Broken())
    ctx = SimpleNamespace(user=SimpleNamespace(porterchain_user_id="u1"))
    with pytest.raises(HTTPException) as e:
        rbac.require_module(ctx, "merchants_read")
    assert e.value.status_code == 503


def test_admin_portal_check_error_is_503(monkeypatch) -> None:
    from porterchain_api.auth import admin

    monkeypatch.setattr("porterchain_api.authz.client.get_authz_client", lambda: _Broken())
    with pytest.raises(HTTPException) as e:
        admin._check_platform("u1", "portal")
    assert e.value.status_code == 503


def test_bound_staff_with_portal_skips_per_request_reconcile(monkeypatch) -> None:
    from porterchain_api.auth import admin

    monkeypatch.setattr(admin, "_check_platform", lambda sid, perm: True)
    u = SimpleNamespace(id="a1", porterchain_user_id="p1", clerk_user_id="staff:a1")
    assert admin._staff_identity_current(u) is True
    assert admin._staff_identity_current(SimpleNamespace(id="a1", porterchain_user_id=None, clerk_user_id="staff:a1")) is False
    monkeypatch.setattr(admin, "_check_platform", lambda sid, perm: False)
    assert admin._staff_identity_current(u) is False

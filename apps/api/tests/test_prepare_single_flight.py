"""Parallel session-context / job polls must not each run UserSync."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.prepare import (
    _PREPARED,
    _PREPARE_LOCKS,
    invalidate_auth_prepare,
    prepare_user_from_claims,
)
from porterchain_api.auth import prepare as prepare_mod


class _User:
    def __init__(self, id: str, auth_subject: str) -> None:
        self.id = id
        self.auth_subject = auth_subject


class _Db:
    def __init__(self, user: _User) -> None:
        self.info: dict = {}
        self.user = user
        self.gets = 0

    def get(self, model, ident):  # noqa: ANN001
        self.gets += 1
        if ident == self.user.id:
            return self.user
        return None


class _Sync:
    def __init__(self, user: _User, delay: float = 0.0) -> None:
        self.user = user
        self.delay = delay
        self.calls = 0
        self._lock = threading.Lock()

    def sync(self, db, claims):  # noqa: ANN001
        del db, claims
        if self.delay:
            import time

            time.sleep(self.delay)
        with self._lock:
            self.calls += 1
        return self.user


def setup_function() -> None:
    _PREPARED.clear()
    _PREPARE_LOCKS.clear()


def _patch_sync(monkeypatch: pytest.MonkeyPatch, syncer: _Sync) -> None:
    monkeypatch.setattr(
        "porterchain_api.auth.user_sync_service.UserSyncService",
        lambda: syncer,
    )


def test_same_request_syncs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _User("u1", "sub-1")
    syncer = _Sync(user)
    _patch_sync(monkeypatch, syncer)
    db = _Db(user)
    claims = IdentityClaims(auth_subject="sub-1")
    assert prepare_user_from_claims(db, claims) is user
    assert prepare_user_from_claims(db, claims) is user
    assert syncer.calls == 1
    assert db.gets == 0


def test_parallel_prepares_sync_once(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _User("u1", "sub-1")
    syncer = _Sync(user, delay=0.2)
    _patch_sync(monkeypatch, syncer)
    claims = IdentityClaims(auth_subject="sub-1")
    dbs = [_Db(user) for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda db: prepare_user_from_claims(db, claims), dbs))

    assert results == [user] * 8
    assert syncer.calls == 1
    assert sum(db.gets for db in dbs) == 7


def test_invalidate_forces_another_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _User("u1", "sub-1")
    syncer = _Sync(user)
    _patch_sync(monkeypatch, syncer)
    claims = IdentityClaims(auth_subject="sub-1")
    first = _Db(user)
    second = _Db(user)
    prepare_user_from_claims(first, claims)
    invalidate_auth_prepare(first, "sub-1")
    prepare_user_from_claims(second, claims)
    assert syncer.calls == 2


def test_lock_holder_makes_waiter_503(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _User("u1", "sub-1")
    syncer = _Sync(user)
    _patch_sync(monkeypatch, syncer)
    monkeypatch.setattr(prepare_mod, "_PREPARE_LOCK_WAIT_S", 0.05)
    lock = prepare_mod._subject_lock("sub-1")
    assert lock.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as raised:
            prepare_user_from_claims(_Db(user), IdentityClaims(auth_subject="sub-1"))
        assert raised.value.status_code == 503
        assert raised.value.detail == "db_unavailable"
        assert syncer.calls == 0
    finally:
        lock.release()

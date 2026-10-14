"""Driver reviews refused offline actions: retry or discard one, own actions only."""

from __future__ import annotations

from uuid import uuid4

import pytest
from porterchain_driver.offline import OfflineService

from porterchain_api import crm_models, merchant_models, user_models  # noqa: F401 — FK targets
from porterchain_api.admin_models import Driver
from porterchain_api.driver_models import DriverOfflineAction


def _driver(db) -> Driver:
    s = uuid4().hex[:8]
    d = Driver(email=f"or-{s}@offline.test", full_name=f"OR {s}", status="APPROVED", clerk_user_id=f"clerk_or_{s}")
    db.add(d)
    db.flush()
    return d


def _failed(db, d, action="stop_complete") -> DriverOfflineAction:
    a = DriverOfflineAction(driver_id=d.id, action_type=action, payload={"stop_id": "s1"}, status="failed", error="403")
    db.add(a)
    db.flush()
    return a


class OkExec:
    def execute(self, driver, action_type, payload):
        return None


class NoExec:
    def execute(self, driver, action_type, payload):
        raise ValueError("stop_already_closed")


def test_status_lists_failed_items_with_reason(db):
    d = _driver(db)
    a = _failed(db, d)
    st = OfflineService().status(db, d.id)
    assert st["failed_count"] == 1
    assert st["failed"][0]["id"] == a.id and st["failed"][0]["error"] == "403"


def test_retry_one_success_and_refused_again(db):
    d = _driver(db)
    a, b = _failed(db, d), _failed(db, d)
    assert OfflineService().retry_one(db, d, a.id, executor=OkExec())["status"] == "synced"
    out = OfflineService().retry_one(db, d, b.id, executor=NoExec())
    assert out["status"] == "failed" and "stop_already_closed" in out["error"]


def test_discard_one_keeps_audit_row_and_drops_from_count(db):
    d = _driver(db)
    a = _failed(db, d)
    out = OfflineService().discard_one(db, d, a.id)
    assert out["status"] == "discarded" and "discarded_by_driver" in out["error"]
    assert OfflineService().status(db, d.id)["failed_count"] == 0


def test_driver_cannot_touch_another_drivers_action(db):
    mine, other = _driver(db), _driver(db)
    theirs = _failed(db, other)
    with pytest.raises(LookupError):
        OfflineService().discard_one(db, mine, theirs.id)
    with pytest.raises(LookupError):
        OfflineService().retry_one(db, mine, theirs.id, executor=OkExec())
    assert db.get(DriverOfflineAction, theirs.id).status == "failed"

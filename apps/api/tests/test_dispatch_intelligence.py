"""Stuck/idle anomalies, their suggested fixes, re-plan diffs and same-area consolidation."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace as NS

from porterchain_api.dispatch_engine import anomalies, exception_fixes, plan_insights

NOW = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)


def _order(oid, state="DISPATCH_READY", age=0, postal="M5V 2T6", driver=None):
    ts = NOW - timedelta(minutes=age)
    return NS(id=oid, order_number=f"PC-{oid}", state=state, updated_at=ts, created_at=ts,
              assigned_driver_id=driver, dropoff={"postal_code": postal})


def test_stuck_only_past_the_state_limit():
    items = anomalies.stuck_items([_order("a", "DRIVER_ASSIGNED", 25), _order("b", "DRIVER_ASSIGNED", 5),
                                   _order("c", "DELIVERED", 500)], NOW)
    assert [i["order_id"] for i in items] == ["a"]
    assert items[0]["kind"] == "stuck" and items[0]["limit_min"] == 20


def test_idle_driver_gets_oldest_waiting_order():
    d = NS(id="d1", full_name="Sam")
    items = anomalies.idle_items([d], [_order("new", age=2), _order("old", age=40)], NOW)
    assert items[0]["order_id"] == "old" and items[0]["idle_driver_id"] == "d1"
    fixes = exception_fixes.suggest(items[0], plan_id=None, best_driver=None, next_slot=None)
    assert fixes[0]["action"] == "reassign" and fixes[0]["params"]["driver_id"] == "d1"


def test_stuck_before_pickup_suggests_reassign_then_contact():
    item = anomalies.stuck_items([_order("a", "DRIVER_ACCEPTED", 50)], NOW)[0]
    fixes = exception_fixes.suggest(item, plan_id="p1", best_driver={"driver_id": "d2", "name": "Ana",
                                                                     "insertion_minutes": 6}, next_slot=None)
    assert [f["action"] for f in fixes] == ["reassign", "reroute", "contact"]


def test_replan_diff():
    before = [{"driver_id": "d1", "stops": [{"order_id": "a"}, {"order_id": "b"}]}]
    after = [{"driver_id": "d1", "stops": [{"order_id": "a"}]},
             {"driver_id": "d2", "stops": [{"order_id": "b"}, {"order_id": "c"}]}]
    d = plan_insights.diff(before, after)
    assert d["added"] == [{"order_id": "c", "to": "d2"}]
    assert d["moved"] == [{"order_id": "b", "from": "d1", "to": "d2"}]
    assert d["removed"] == []


def test_consolidation_groups_by_fsa_and_flags_splits():
    orders = [_order("a"), _order("b"), _order("c", postal="L4C 1A1"), _order("d", postal="")]
    groups = plan_insights.consolidation(orders, {"a": "d1", "b": "d2"})
    assert len(groups) == 1
    assert groups[0]["fsa"] == "M5V" and groups[0]["split_across"] == 2
    assert "split over 2 drivers" in groups[0]["why"]

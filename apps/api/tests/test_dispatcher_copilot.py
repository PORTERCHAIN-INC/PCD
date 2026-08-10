"""Dispatcher copilot helpers (P2-1)."""

from porterchain_api.admin_engine.dispatcher_copilot_service import _action_id


def test_action_id_stable():
    a = _action_id("ord-1", "drv-1", "assign")
    b = _action_id("ord-1", "drv-1", "assign")
    c = _action_id("ord-1", "drv-2", "assign")
    assert a == b
    assert a != c
    assert len(a) == 16

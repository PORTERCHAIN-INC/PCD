"""Recurring standing orders (§8.1.11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from porterchain_api.merchant_engine.standing_order_service import (
    RECURRENCE_DELTAS,
    advance_next_run,
    standing_error_message,
)


def test_advance_next_run_weekly():
    start = datetime(2026, 7, 9, 8, 0, tzinfo=UTC)
    nxt = advance_next_run(start, "weekly")
    assert nxt == start + RECURRENCE_DELTAS["weekly"]


def test_advance_next_run_defaults_unknown_rule():
    start = datetime(2026, 7, 9, 8, 0, tzinfo=UTC)
    nxt = advance_next_run(start, "custom")
    assert nxt == start + timedelta(weeks=1)


def test_standing_error_message_is_english():
    assert "deleted" in standing_error_message("template_not_found").lower()
    assert "reactivates" in standing_error_message("merchant_not_active").lower()
    assert standing_error_message("unknown_code") == "unknown_code"

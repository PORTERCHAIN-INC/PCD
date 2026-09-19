"""Food SLA dispatch ordering (§8.1.8)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from porterchain_api.order_engine.buckets import dispatch_queue_sort_key


def test_food_window_orders_before_generic():
    now = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    urgent = SimpleNamespace(
        scheduled_at=now + timedelta(hours=5),
        compliance_metadata={
            "delivery_window": {"end": (now + timedelta(minutes=30)).isoformat()},
        },
    )
    normal = SimpleNamespace(
        scheduled_at=now + timedelta(hours=1),
        compliance_metadata=None,
    )
    assert dispatch_queue_sort_key(urgent, now=now) < dispatch_queue_sort_key(normal, now=now)

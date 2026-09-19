"""Order SLA deadline must not treat ASAP scheduled_at=now as already breached."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from porterchain_api.booking_engine.order_sla import order_sla_status, resolve_sla_deadline


def test_asap_parcel_not_breached_immediately():
    now = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
    order = SimpleNamespace(
        state="BOOKED",
        order_type="INSTANT",
        scheduled_at=now,  # Send-now request time
        created_at=now,
        compliance_metadata=None,
    )
    assert order_sla_status(order, now.replace(tzinfo=None)) == "ok"
    assert order_sla_status(order, (now + timedelta(minutes=5)).replace(tzinfo=None)) == "ok"


def test_asap_breaches_after_instant_window():
    created = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    order = SimpleNamespace(
        state="DISPATCH_READY",
        order_type="INSTANT",
        scheduled_at=created,
        created_at=created,
        compliance_metadata=None,
    )
    after = (created + timedelta(hours=4, minutes=1)).replace(tzinfo=None)
    assert order_sla_status(order, after) == "breached"


def test_scheduled_uses_scheduled_at():
    created = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
    scheduled = datetime(2026, 7, 14, 18, 0, tzinfo=UTC)
    order = SimpleNamespace(
        state="BOOKED",
        order_type="SCHEDULED",
        scheduled_at=scheduled,
        created_at=created,
        compliance_metadata=None,
    )
    assert order_sla_status(order, (scheduled - timedelta(hours=2)).replace(tzinfo=None)) == "ok"
    assert order_sla_status(order, (scheduled - timedelta(minutes=10)).replace(tzinfo=None)) == "at_risk"
    assert order_sla_status(order, (scheduled + timedelta(minutes=1)).replace(tzinfo=None)) == "breached"


def test_delivery_window_wins():
    created = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
    window_end = datetime(2026, 7, 14, 11, 0, tzinfo=UTC)
    order = SimpleNamespace(
        state="BOOKED",
        order_type="INSTANT",
        scheduled_at=created,
        created_at=created,
        compliance_metadata={"delivery_window": {"end": window_end.isoformat()}},
    )
    assert resolve_sla_deadline(order) == window_end.replace(tzinfo=None)
    assert order_sla_status(order, (window_end + timedelta(minutes=1)).replace(tzinfo=None)) == "breached"


def test_delivered_is_met():
    now = datetime(2026, 7, 14, 16, 0, tzinfo=UTC)
    order = SimpleNamespace(
        state="DELIVERED",
        order_type="INSTANT",
        scheduled_at=now - timedelta(hours=5),
        created_at=now - timedelta(hours=5),
        compliance_metadata=None,
    )
    assert order_sla_status(order, now.replace(tzinfo=None)) == "met"

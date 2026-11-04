"""L45: a normal ASAP parcel is not labelled critical."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from porterchain_driver.route_optimizer import compute_urgency


def test_asap_normal_parcel_is_high_not_critical():
    now = datetime.now(UTC)
    o = SimpleNamespace(amount_cents=1800, scheduled_at=now - timedelta(minutes=10))
    assert compute_urgency(o, now=now) == "high"


def test_long_overdue_is_critical():
    now = datetime.now(UTC)
    o = SimpleNamespace(amount_cents=1800, scheduled_at=now - timedelta(hours=3))
    assert compute_urgency(o, now=now) == "critical"

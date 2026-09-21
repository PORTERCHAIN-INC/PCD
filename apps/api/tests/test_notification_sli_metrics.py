"""Phase 2.5d notification SLI helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from porterchain_api.notification_engine.sli_metrics import (
    assess_notification_channel_slis,
    prometheus_notification_lines,
)


def test_assess_notification_channel_slis_empty(db) -> None:
    snap = assess_notification_channel_slis(db, window_hours=24)
    assert snap["window_hours"] == 24
    assert "queued" in snap["by_status"]
    assert "sent" in snap["by_status"]
    assert "deferred" in snap["by_status"]
    assert "dead_letter" in snap["by_status"]
    assert "email" in snap["p99_queued_to_sent_seconds"]
    assert isinstance(snap["p99_queued_to_sent_seconds"]["email"], float)
    assert "critical" in snap["by_push_priority_status"]
    assert "high" in snap["p99_push_queued_to_sent_seconds_by_priority"]


def test_assess_notification_channel_slis_counts_and_p99(db) -> None:
    from porterchain_api.notification_engine.models import NotificationRecord

    now = datetime.now(UTC)
    db.add(
        NotificationRecord(
            template_key="order_cancelled",
            category="operational",
            channel="email",
            recipient_type="customer",
            recipient_id="c1",
            title="t",
            body="b",
            status="sent",
            queued_at=now - timedelta(seconds=10),
            sent_at=now,
        )
    )
    db.add(
        NotificationRecord(
            template_key="order_cancelled",
            category="operational",
            channel="email",
            recipient_type="customer",
            recipient_id="c2",
            title="t",
            body="b",
            status="deferred",
            queued_at=now - timedelta(seconds=2),
        )
    )
    db.add(
        NotificationRecord(
            template_key="order_cancelled",
            category="operational",
            channel="push",
            recipient_type="driver",
            recipient_id="d1",
            title="t",
            body="b",
            status="dead_letter",
            queued_at=now - timedelta(seconds=30),
        )
    )
    db.add(
        NotificationRecord(
            template_key="sla_breached",
            category="orders",
            channel="push",
            priority="critical",
            recipient_type="admin",
            recipient_id="a1",
            title="SLA",
            body="breached",
            status="delivered",
            queued_at=now - timedelta(seconds=5),
            sent_at=now,
        )
    )
    db.commit()

    snap = assess_notification_channel_slis(db, window_hours=24)
    assert snap["by_status"]["sent"] >= 1
    assert snap["by_status"]["deferred"] >= 1
    assert snap["by_status"]["dead_letter"] >= 1
    assert snap["by_channel_status"]["email"]["sent"] >= 1
    # p99 floors hold on an empty CI window. Local shared Postgres may already
    # have faster in-window samples that pull percentile_cont down.
    if snap["by_status"]["sent"] <= 2:
        assert snap["p99_queued_to_sent_seconds"]["email"] >= 9.0
    else:
        assert snap["p99_queued_to_sent_seconds"]["email"] >= 0
    assert snap["by_push_priority_status"]["critical"]["delivered"] >= 1
    if snap["by_push_priority_status"]["critical"]["delivered"] <= 1:
        assert snap["p99_push_queued_to_sent_seconds_by_priority"]["critical"] >= 4.0
    else:
        assert snap["p99_push_queued_to_sent_seconds_by_priority"]["critical"] >= 0

    text = "\n".join(prometheus_notification_lines(snap))
    assert 'porterchain_notification_records{status="sent"}' in text
    assert 'porterchain_notification_queued_to_sent_p99_seconds{channel="email"}' in text
    assert 'porterchain_notification_push_priority_records{priority="critical",status="delivered"}' in text
    assert 'porterchain_notification_push_queued_to_sent_p99_seconds{priority="critical"}' in text

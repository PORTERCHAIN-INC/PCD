"""Notification channel SLIs (Phase 2.5d) — gauges for /metrics scrape."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

DEFAULT_WINDOW_HOURS = 24
CHANNELS = ("email", "sms", "push", "in_app")
STATUSES = ("queued", "sent", "deferred", "dead_letter", "failed", "delivered")
PRIORITIES = ("critical", "high", "normal")


def assess_notification_channel_slis(
    db: Session,
    *,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> dict:
    """Counts by status×channel + p99 queued→sent seconds by channel (window).

    Also slices push records by priority (Jeff Dean ops SLO).
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    count_rows = db.execute(
        text(
            """
            SELECT channel, status, COUNT(*)::int AS n
            FROM notification_records
            WHERE created_at >= :cutoff
            GROUP BY channel, status
            """
        ),
        {"cutoff": cutoff},
    ).all()

    by_status: dict[str, int] = {s: 0 for s in STATUSES}
    by_channel_status: dict[str, dict[str, int]] = {
        ch: {s: 0 for s in STATUSES} for ch in CHANNELS
    }
    for row in count_rows:
        ch = str(row.channel or "")
        st = str(row.status or "")
        n = int(row.n or 0)
        if st in by_status:
            by_status[st] += n
        if ch in by_channel_status and st in by_channel_status[ch]:
            by_channel_status[ch][st] = n

    p99_rows = db.execute(
        text(
            """
            SELECT channel,
                   COALESCE(
                     percentile_cont(0.99) WITHIN GROUP (
                       ORDER BY EXTRACT(EPOCH FROM (sent_at - queued_at))
                     ),
                     0
                   )::float AS p99_seconds
            FROM notification_records
            WHERE created_at >= :cutoff
              AND queued_at IS NOT NULL
              AND sent_at IS NOT NULL
              AND sent_at >= queued_at
              AND status IN ('sent', 'delivered')
            GROUP BY channel
            """
        ),
        {"cutoff": cutoff},
    ).all()
    p99_by_channel = {ch: 0.0 for ch in CHANNELS}
    for row in p99_rows:
        ch = str(row.channel or "")
        if ch in p99_by_channel:
            p99_by_channel[ch] = round(float(row.p99_seconds or 0.0), 3)

    push_priority_rows = db.execute(
        text(
            """
            SELECT COALESCE(NULLIF(LOWER(priority), ''), 'normal') AS priority,
                   status,
                   COUNT(*)::int AS n
            FROM notification_records
            WHERE created_at >= :cutoff
              AND channel = 'push'
            GROUP BY 1, status
            """
        ),
        {"cutoff": cutoff},
    ).all()
    by_push_priority_status: dict[str, dict[str, int]] = {
        p: {s: 0 for s in STATUSES} for p in PRIORITIES
    }
    for row in push_priority_rows:
        pri = str(row.priority or "normal")
        if pri not in by_push_priority_status:
            by_push_priority_status[pri] = {s: 0 for s in STATUSES}
        st = str(row.status or "")
        if st in by_push_priority_status[pri]:
            by_push_priority_status[pri][st] = int(row.n or 0)

    p99_push_priority_rows = db.execute(
        text(
            """
            SELECT COALESCE(NULLIF(LOWER(priority), ''), 'normal') AS priority,
                   COALESCE(
                     percentile_cont(0.99) WITHIN GROUP (
                       ORDER BY EXTRACT(EPOCH FROM (sent_at - queued_at))
                     ),
                     0
                   )::float AS p99_seconds
            FROM notification_records
            WHERE created_at >= :cutoff
              AND channel = 'push'
              AND queued_at IS NOT NULL
              AND sent_at IS NOT NULL
              AND sent_at >= queued_at
              AND status IN ('sent', 'delivered')
            GROUP BY 1
            """
        ),
        {"cutoff": cutoff},
    ).all()
    p99_push_by_priority = {p: 0.0 for p in PRIORITIES}
    for row in p99_push_priority_rows:
        pri = str(row.priority or "normal")
        p99_push_by_priority[pri] = round(float(row.p99_seconds or 0.0), 3)

    return {
        "window_hours": window_hours,
        "by_status": by_status,
        "by_channel_status": by_channel_status,
        "p99_queued_to_sent_seconds": p99_by_channel,
        "by_push_priority_status": by_push_priority_status,
        "p99_push_queued_to_sent_seconds_by_priority": p99_push_by_priority,
    }


def prometheus_notification_lines(snapshot: dict) -> list[str]:
    lines = [
        "# HELP porterchain_notification_records Notification records in SLI window by status",
        "# TYPE porterchain_notification_records gauge",
    ]
    for status, n in (snapshot.get("by_status") or {}).items():
        lines.append(f'porterchain_notification_records{{status="{status}"}} {int(n)}')

    lines.extend(
        [
            "# HELP porterchain_notification_channel_records Notification records by channel and status",
            "# TYPE porterchain_notification_channel_records gauge",
        ]
    )
    for channel, statuses in (snapshot.get("by_channel_status") or {}).items():
        for status, n in statuses.items():
            lines.append(
                f'porterchain_notification_channel_records{{channel="{channel}",status="{status}"}} {int(n)}'
            )

    lines.extend(
        [
            "# HELP porterchain_notification_queued_to_sent_p99_seconds "
            "P99 seconds from queued_at to sent_at by channel",
            "# TYPE porterchain_notification_queued_to_sent_p99_seconds gauge",
        ]
    )
    for channel, secs in (snapshot.get("p99_queued_to_sent_seconds") or {}).items():
        lines.append(
            f'porterchain_notification_queued_to_sent_p99_seconds{{channel="{channel}"}} {float(secs)}'
        )

    lines.extend(
        [
            "# HELP porterchain_notification_push_priority_records Push records by priority and status",
            "# TYPE porterchain_notification_push_priority_records gauge",
        ]
    )
    for priority, statuses in (snapshot.get("by_push_priority_status") or {}).items():
        for status, n in statuses.items():
            lines.append(
                f'porterchain_notification_push_priority_records{{priority="{priority}",status="{status}"}} {int(n)}'
            )

    lines.extend(
        [
            "# HELP porterchain_notification_push_queued_to_sent_p99_seconds "
            "P99 seconds from queued_at to sent_at for push by priority",
            "# TYPE porterchain_notification_push_queued_to_sent_p99_seconds gauge",
        ]
    )
    for priority, secs in (snapshot.get("p99_push_queued_to_sent_seconds_by_priority") or {}).items():
        lines.append(
            f'porterchain_notification_push_queued_to_sent_p99_seconds{{priority="{priority}"}} {float(secs)}'
        )
    return lines

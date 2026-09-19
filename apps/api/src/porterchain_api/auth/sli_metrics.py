"""Auth SLI counters — scraped via /metrics (Dean: measure login paths)."""

from __future__ import annotations

from collections import defaultdict

# kind → result → count  (e.g. staff_login / ok|fail|rate_limited)
_auth_events: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))


def note_auth_event(kind: str, result: str) -> None:
    k = (kind or "unknown").strip() or "unknown"
    r = (result or "unknown").strip() or "unknown"
    _auth_events[k][r] += 1


def auth_events_snapshot() -> dict[str, dict[str, int]]:
    """Process-local auth SLI counters for ops dashboards."""
    return {kind: dict(results) for kind, results in sorted(_auth_events.items())}


def prometheus_auth_lines() -> list[str]:
    lines = [
        "# HELP porterchain_auth_events_total Auth path outcomes (process-local counter)",
        "# TYPE porterchain_auth_events_total counter",
    ]
    for kind in sorted(_auth_events):
        for result, value in sorted(_auth_events[kind].items()):
            lines.append(
                f'porterchain_auth_events_total{{kind="{kind}",result="{result}"}} {int(value)}'
            )
    return lines


def reset_auth_events_for_tests() -> None:
    _auth_events.clear()

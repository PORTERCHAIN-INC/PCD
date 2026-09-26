"""Staff notification fan-out — engines may page staff without importing notification_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def dispatch_staff_specs(
    db: Session,
    specs: list[dict[str, Any]],
    *,
    event_type: str,
    correlation_id: str,
) -> None:
    """Expand growth/staff sentinels and dispatch via the notification engine."""
    from porterchain_api.notification_engine.engine import get_notification_engine
    from porterchain_api.notification_engine.staff_fanout import expand_staff_specs

    expanded = expand_staff_specs(db, specs)
    if expanded:
        get_notification_engine().dispatch_multi(
            db,
            expanded,
            event_type=event_type,
            correlation_id=correlation_id,
        )


def growth_staff_sentinel() -> str:
    from porterchain_api.notification_engine.staff_fanout import staff_sentinel

    return staff_sentinel("growth")


__all__ = ["dispatch_staff_specs", "growth_staff_sentinel"]

"""Fleetbase order sync SLO — link rate when dispatch bridge is enabled (DD-05b, §0.1.7)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.fleetbase_engine.retry_queue import ErrorQueue
from porterchain_api.models import Order

SLO_TARGET_PCT = 95.0
_EXCLUDED_STATES = (OrderState.CANCELLED.value, OrderState.REFUNDED.value)


def assess_fleetbase_sync(db: Session, settings: Settings) -> dict:
    """Compute outbound sync link rate and queue health."""
    base = {
        "bridge_enabled": settings.fleetbase_dispatch_bridge,
        "slo_target_pct": SLO_TARGET_PCT,
        "webhook_secret_configured": bool(settings.fleetbase_webhook_secret),
        "api_key_configured": bool(settings.fleetbase_api_key),
        "company_uuid_configured": bool(settings.fleetbase_default_company_uuid),
        "api_url": settings.fleetbase_api_url,
    }
    if not settings.fleetbase_dispatch_bridge:
        return {
            **base,
            "eligible_orders": 0,
            "linked_orders": 0,
            "link_pct": 100.0,
            "meets_slo": True,
            "pending_jobs": 0,
            "dead_letters": 0,
            "queue_stats": {},
        }

    total = (
        db.query(func.count(Order.id)).filter(Order.state.notin_(_EXCLUDED_STATES)).scalar() or 0
    )
    linked = (
        db.query(func.count(Order.id))
        .filter(
            Order.state.notin_(_EXCLUDED_STATES),
            Order.fleetbase_order_id.isnot(None),
        )
        .scalar()
        or 0
    )
    pct = (linked / total * 100.0) if total else 100.0
    stats = ErrorQueue.stats(db)
    pending = int(stats.get("pending", 0)) + int(stats.get("retrying", 0))
    dead = int(stats.get("dead", 0))

    return {
        **base,
        "eligible_orders": int(total),
        "linked_orders": int(linked),
        "link_pct": round(pct, 2),
        "meets_slo": pct >= SLO_TARGET_PCT or total == 0,
        "pending_jobs": pending,
        "dead_letters": dead,
        "queue_stats": stats,
    }

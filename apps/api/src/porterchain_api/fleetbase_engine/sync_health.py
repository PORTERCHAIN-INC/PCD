"""Fleetbase order sync SLO — link rate when dispatch bridge is enabled (DD-05b, §0.1.7, §3.5.5)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.fleetbase_engine.retry_queue import ErrorQueue, FLEETBASE_SYNC_SLO_TARGET_PCT
from porterchain_api.models import Order

SLO_TARGET_PCT = FLEETBASE_SYNC_SLO_TARGET_PCT
_EXCLUDED_STATES = (OrderState.CANCELLED.value, OrderState.REFUNDED.value)


def build_fleetbase_sync_alerts(slo: dict) -> list[dict[str, str]]:
    """Ops alerts when bridge is on and sync health degrades."""
    if not slo.get("bridge_enabled"):
        return []
    alerts: list[dict[str, str]] = []
    if not slo.get("meets_slo"):
        alerts.append(
            {
                "level": "critical",
                "code": "fleetbase_sync_below_slo",
                "message": (
                    f"Link rate {slo.get('link_pct')}% below SLO {slo.get('slo_target_pct')}% "
                    f"({slo.get('linked_orders')}/{slo.get('eligible_orders')} orders)"
                ),
            }
        )
    dead = int(slo.get("dead_letters") or 0)
    if dead > 0:
        alerts.append(
            {
                "level": "warning",
                "code": "fleetbase_sync_dead_letters",
                "message": f"{dead} dead-letter Fleetbase sync job(s) — replay via RUNBOOK",
            }
        )
    pending = int(slo.get("pending_jobs") or 0)
    if pending >= 500:
        alerts.append(
            {
                "level": "warning",
                "code": "fleetbase_sync_backlog",
                "message": f"{pending} pending/retrying Fleetbase sync jobs",
            }
        )
    return alerts


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
        result = {
            **base,
            "eligible_orders": 0,
            "linked_orders": 0,
            "link_pct": 100.0,
            "meets_slo": True,
            "pending_jobs": 0,
            "dead_letters": 0,
            "queue_stats": {},
        }
        result["alerts"] = build_fleetbase_sync_alerts(result)
        return result

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

    result = {
        **base,
        "eligible_orders": int(total),
        "linked_orders": int(linked),
        "link_pct": round(pct, 2),
        "meets_slo": pct >= SLO_TARGET_PCT or total == 0,
        "pending_jobs": pending,
        "dead_letters": dead,
        "queue_stats": stats,
    }
    result["alerts"] = build_fleetbase_sync_alerts(result)
    return result

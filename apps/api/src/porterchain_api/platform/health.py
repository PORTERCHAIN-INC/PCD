"""Deep health checks — liveness vs readiness probes."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_shared.redis_health import ping_redis


def _queue_health() -> dict:
    """Report Redis queue depths and worker heartbeat (DD-04)."""
    try:
        from porterchain_shared.redis_client import get_redis_client
        from porterchain_shared.queue.names import QueueName

        client = get_redis_client()
        depths = {q.value: int(client.llen(q.redis_key)) for q in QueueName}
        heartbeat = client.get("porterchain:worker:heartbeat")
        return {
            "status": "ok" if heartbeat else "no_heartbeat",
            "depths": depths,
            "worker_heartbeat": heartbeat,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc)}


def liveness() -> dict[str, str]:
    return {"status": "ok", "service": "porterchain-api"}


def readiness(db: Session, settings: Settings) -> dict:
    checks: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    checks["redis"] = "ok" if ping_redis() else "unavailable"
    queue = _queue_health()
    checks["queues"] = queue["status"]
    checks["stripe"] = "configured" if settings.stripe_secret else "mock_or_unconfigured"
    checks["fleetbase"] = (
        "bridge_enabled" if settings.fleetbase_dispatch_bridge else "bridge_disabled"
    )

    try:
        from porterchain_api.notification_engine.fcm_service import firebase_production_ready
        from porterchain_shared.config.settings import get_platform_settings

        platform = get_platform_settings()
        if not platform.push_enabled:
            checks["firebase"] = "push_disabled"
        else:
            ready, reason = firebase_production_ready()
            checks["firebase"] = "ok" if ready else (reason or "not_configured")
    except Exception as exc:  # noqa: BLE001
        checks["firebase"] = f"error: {exc}"

    required = {"database": "ok"}
    if settings.app_env != "local":
        required["redis"] = "ok"

    status = "ok" if all(checks.get(k) == v for k, v in required.items()) else "degraded"
    return {"status": status, "service": "porterchain-api", "checks": checks, "queues": queue}

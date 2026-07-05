"""Deep health checks — liveness vs readiness probes."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_shared.redis_health import ping_redis


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
    checks["stripe"] = "configured" if settings.stripe_secret else "mock_or_unconfigured"
    checks["fleetbase"] = (
        "bridge_enabled" if settings.fleetbase_dispatch_bridge else "bridge_disabled"
    )

    try:
        from porterchain_api.notification_engine.fcm_service import firebase_production_ready

        if not settings.push_enabled:
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
    return {"status": status, "service": "porterchain-api", "checks": checks}

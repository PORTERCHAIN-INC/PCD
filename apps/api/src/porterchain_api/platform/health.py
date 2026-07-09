"""Deep health checks — liveness vs readiness probes."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_shared.redis_health import ping_redis


def _routing_health() -> str:
    """Valhalla/OSRM reachability for quote pricing (§0.1.6)."""
    try:
        from porterchain_shared.config.settings import get_platform_settings

        platform = get_platform_settings()
        if platform.routing_engine == "valhalla" and platform.valhalla_url:
            import httpx

            url = f"{platform.valhalla_url.rstrip('/')}/status"
            with httpx.Client(timeout=3.0) as client:
                response = client.get(url)
                if response.status_code < 400:
                    return "ok"
                return f"http_{response.status_code}"
        if platform.osrm_url:
            import httpx

            probe = (
                f"{platform.osrm_url.rstrip('/')}/route/v1/driving/"
                "-79.38,43.65;-79.40,43.66"
            )
            with httpx.Client(timeout=3.0) as client:
                response = client.get(probe, params={"overview": "false"})
                if response.status_code < 400 and "routes" in response.text:
                    return "ok"
                return "unavailable"
        return "unconfigured"
    except Exception as exc:  # noqa: BLE001
        return f"unreachable: {exc}"


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
    fleetbase_sync: dict = {}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    checks["redis"] = "ok" if ping_redis() else "unavailable"
    checks["routing"] = _routing_health()
    try:
        from porterchain_api.auth.clerk_registry import clerk_configuration_mode, clerk_health_checks

        clerk_apps = clerk_health_checks(settings)
        clerk_mode = clerk_configuration_mode(settings)
        if clerk_mode == "incomplete":
            checks["clerk"] = "not_configured"
        elif all(status == "ok" for status in clerk_apps.values()):
            checks["clerk"] = "ok" if clerk_mode == "enterprise" else "legacy_ok"
        else:
            checks["clerk"] = "degraded"
    except Exception as exc:  # noqa: BLE001
        checks["clerk"] = f"error: {exc}"
        clerk_apps = {}
        clerk_mode = "error"
    queue = _queue_health()
    checks["queues"] = queue["status"]
    checks["stripe"] = "configured" if settings.stripe_secret else "mock_or_unconfigured"
    checks["fleetbase"] = (
        "bridge_enabled" if settings.fleetbase_dispatch_bridge else "bridge_disabled"
    )
    if settings.fleetbase_dispatch_bridge:
        try:
            from porterchain_api.fleetbase_engine.sync_health import assess_fleetbase_sync

            fleetbase_sync = assess_fleetbase_sync(db, settings)
            if not fleetbase_sync.get("webhook_secret_configured"):
                checks["fleetbase_webhook"] = "missing_secret"
            else:
                checks["fleetbase_webhook"] = "configured"
            checks["fleetbase_sync"] = (
                "ok" if fleetbase_sync.get("meets_slo") else f"below_slo:{fleetbase_sync.get('link_pct')}%"
            )
        except Exception as exc:  # noqa: BLE001
            checks["fleetbase_sync"] = f"error: {exc}"
            fleetbase_sync = {"error": str(exc)}

    try:
        from porterchain_api.notification_engine.fcm_service import (
            firebase_production_ready,
            firebase_sdk_available,
        )
        from porterchain_shared.config.settings import get_platform_settings

        platform = get_platform_settings()
        if not platform.push_enabled:
            checks["firebase"] = "push_disabled"
        else:
            ready, reason = firebase_production_ready()
            if not ready:
                checks["firebase"] = reason or "not_configured"
            elif not platform.push_send:
                checks["firebase"] = "dry_run"
            elif not firebase_sdk_available():
                checks["firebase"] = "sdk_missing"
            else:
                checks["firebase"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["firebase"] = f"error: {exc}"

    required = {"database": "ok"}
    if settings.app_env != "local":
        required["redis"] = "ok"

    status = "ok" if all(checks.get(k) == v for k, v in required.items()) else "degraded"
    payload: dict = {
        "status": status,
        "service": "porterchain-api",
        "checks": checks,
        "queues": queue,
    }
    if fleetbase_sync:
        payload["fleetbase_sync"] = fleetbase_sync

    try:
        from porterchain_api.merchant_engine.webhook_delivery_health import assess_merchant_webhook_delivery

        merchant_webhooks = assess_merchant_webhook_delivery(db)
        checks["merchant_webhook_delivery"] = (
            "ok" if merchant_webhooks.get("meets_slo") else f"below_slo:{merchant_webhooks.get('success_pct')}%"
        )
        payload["merchant_webhook_delivery"] = merchant_webhooks
    except Exception as exc:  # noqa: BLE001
        checks["merchant_webhook_delivery"] = f"error: {exc}"

    if clerk_apps:
        payload["clerk_apps"] = clerk_apps
        payload["clerk_mode"] = clerk_mode
    return payload


def public_status(db: Session, settings: Settings) -> dict:
    """Public status page payload (§11.3.5) — no auth, minimal detail."""
    ready = readiness(db, settings)
    overall = ready.get("status", "unknown")
    checks = ready.get("checks") or {}
    components = {
        "api": "operational" if checks.get("database") == "ok" else "degraded",
        "database": "operational" if checks.get("database") == "ok" else "outage",
        "redis": "operational" if checks.get("redis") == "ok" else "degraded",
        "payments": "operational" if checks.get("stripe") in ("configured", "mock_or_unconfigured") else "degraded",
        "dispatch": "operational" if checks.get("fleetbase") else "degraded",
    }
    return {
        "status": overall,
        "service": "porterchain",
        "components": components,
        "updated_at": datetime.now(UTC).isoformat(),
    }

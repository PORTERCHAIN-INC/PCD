"""Integration and engine probe mixin."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_helpers import HealthClass, _probe_http
from porterchain_api.auth.clerk_registry import clerk_jwks_urls, is_clerk_configured, is_clerk_secret_configured
from porterchain_api.config import Settings
from porterchain_api.models import Order
from porterchain_api.platform.health import readiness
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
from porterchain_shared.config.settings import PlatformSettings
from porterchain_shared.queue.publisher import queue_depths
from porterchain_shared.redis_health import ping_redis


class DiagnosticsProbesMixin:
    def _probe_fleetbase_console(self, settings: Settings) -> dict[str, Any]:
        url = settings.fleetbase_console_url or "http://localhost:4200"
        status, latency, err = _probe_http(url, local_optional=settings.app_env == "local")
        if settings.app_env == "local" and status == "warning":
            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {"url": url, "skipped": True, "note": "Optional locally"},
            }
        return {
            "status": status,
            "latency_ms": latency,
            "errors": [err] if err and status == "critical" else [],
            "warnings": [err] if err and status == "warning" else [],
            "details": {"url": url},
        }

    def _probe_email(self, platform: PlatformSettings, settings: Settings | None = None) -> dict[str, Any]:
        if platform.smtp_host and platform.smtp_user:
            return {"status": "healthy", "details": {"host": platform.smtp_host, "from": platform.smtp_from}}
        if platform.smtp_host:
            return {"status": "warning", "warnings": ["SMTP host set but credentials incomplete"]}
        if settings is not None and settings.app_env == "local":
            status, latency, err = _probe_http("http://localhost:8025", local_optional=True)
            if status == "healthy":
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "details": {"mode": "mailpit", "smtp": "localhost:1025"},
                }
            return {"status": "warning", "warnings": [err or "Mailpit not reachable"]}
        return {"status": "warning", "warnings": ["SMTP not configured — use Mailpit locally"]}

    def _probe_mailpit(self, settings: Settings) -> dict[str, Any]:
        if settings.app_env != "local":
            return {"status": "healthy", "details": {"note": "Mailpit is local dev only"}}
        status, latency, err = _probe_http("http://localhost:8025", local_optional=True)
        return {
            "status": status,
            "latency_ms": latency,
            "warnings": [err] if err else [],
            "details": {"url": "http://localhost:8025"},
        }

    def _probe_readiness(self, settings: Settings, db: Session) -> dict[str, Any]:
        start = time.monotonic()
        ready = readiness(db, settings)
        latency = (time.monotonic() - start) * 1000
        status: HealthClass = "healthy" if ready.get("status") == "ok" else "warning"
        return {
            "status": status,
            "latency_ms": latency,
            "details": ready,
            "warnings": [] if status == "healthy" else [f"Readiness: {ready.get('status')}"],
        }

    def _probe_metrics(self, settings: Settings) -> dict[str, Any]:
        url = f"{settings.porterchain_api_url.rstrip('/')}/metrics"
        status, latency, err = _probe_http(url)
        return {
            "status": status,
            "latency_ms": latency,
            "errors": [err] if err else [],
            "details": {"url": url},
        }

    def _redis_latency(self, redis_url: str) -> float | None:
        try:
            import redis

            start = time.monotonic()
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return (time.monotonic() - start) * 1000
        except Exception:  # noqa: BLE001
            return None

    def _engine_pricing(self, db: Session) -> dict[str, Any]:
        try:
            from porterchain_api.pricing_engine import get_pricing_service

            get_pricing_service(db)
            return {"status": "healthy", "version": "porterchain_pricing"}
        except Exception as exc:  # noqa: BLE001
            return {"status": "critical", "errors": [str(exc)]}

    def _engine_billing(self, settings: Settings) -> dict[str, Any]:
        warnings: list[str] = []
        if settings.stripe_mock:
            warnings.append("Stripe mock mode active")
        status = "healthy" if settings.stripe_secret or settings.stripe_mock else "warning"
        return {"status": status, "warnings": warnings, "version": "billing_engine"}

    def _engine_notifications(self, db: Session) -> dict[str, Any]:
        from porterchain_api.admin_engine.notification_admin_service import NotificationAdminService

        dash = NotificationAdminService().dashboard(db)
        status = "warning" if dash["failed"] > 0 else "healthy"
        return {"status": status, "details": dash}

    def _engine_orders(self, db: Session) -> dict[str, Any]:
        count = db.query(func.count(Order.id)).scalar() or 0
        return {"status": "healthy", "details": {"order_count": count}}

    def _engine_crm(self, db: Session) -> dict[str, Any]:
        try:
            from porterchain_api.crm_models import CrmLead

            count = db.query(func.count(CrmLead.id)).scalar() or 0
            return {"status": "healthy", "details": {"leads": count}}
        except Exception:  # noqa: BLE001
            return {"status": "healthy", "details": {"leads": 0}}

    def _engine_finance(self, db: Session) -> dict[str, Any]:
        return {"status": "healthy", "details": {"module": "admin_engine.finance_service"}}

    def _engine_claims(self, db: Session) -> dict[str, Any]:
        return {"status": "healthy", "details": {"module": "admin_engine.claims_service"}}

    def _engine_support(self, db: Session) -> dict[str, Any]:
        return {"status": "healthy", "details": {"module": "admin_engine.support_service"}}

    def _probe_fleetbase_adapter(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        try:
            adapter = get_fleetbase_integration(settings)
            status: HealthClass = "healthy" if adapter.is_enabled else "warning"
            warnings = [] if adapter.is_enabled else ["Dispatch bridge disabled"]
            details = {"enabled": adapter.is_enabled}
            if live and adapter.is_enabled:
                status, latency, err = _probe_http(
                    settings.fleetbase_api_url,
                    local_optional=settings.app_env == "local",
                )
                if settings.app_env == "local" and status == "warning":
                    return {"status": "healthy", "latency_ms": latency, "details": {**details, "skipped": True}}
                if err:
                    warnings.append(err)
                return {
                    "status": status if status != "critical" else "warning",
                    "latency_ms": latency,
                    "warnings": warnings,
                    "details": details,
                }
            return {"status": status, "warnings": warnings, "details": details}
        except Exception as exc:  # noqa: BLE001
            return {"status": "critical", "errors": [str(exc)]}

    def _probe_fleetbase(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        if not settings.fleetbase_dispatch_bridge:
            return {"status": "warning", "warnings": ["Dispatch bridge disabled"]}
        status, latency, err = _probe_http(
            settings.fleetbase_api_url,
            local_optional=settings.app_env == "local",
        )
        if settings.app_env == "local" and status == "warning":
            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {"url": settings.fleetbase_api_url, "skipped": True},
            }
        warnings: list[str] = []
        if not settings.fleetbase_api_key:
            warnings.append("Fleetbase API key not configured — outbound sync may fail")
        return {
            "status": status if status != "critical" else "warning",
            "latency_ms": latency,
            "errors": [err] if err else [],
            "warnings": warnings,
            "details": {"url": settings.fleetbase_api_url, "authenticated": bool(settings.fleetbase_api_key)},
        }

    def _probe_google_maps(
        self, platform: PlatformSettings, *, live: bool = False, app_env: str | None = None
    ) -> dict[str, Any]:
        if not platform.google_maps_api_key:
            if (app_env or "").lower() == "local":
                return {"status": "healthy", "details": {"skipped": True, "note": "Optional locally"}}
            return {"status": "warning", "warnings": ["API key not configured"]}
        if live:
            url = (
                "https://maps.googleapis.com/maps/api/geocode/json"
                f"?address=Toronto&key={platform.google_maps_api_key}"
            )
            status, latency, err = _probe_http(url)
            return {"status": status, "latency_ms": latency, "errors": [err] if err else []}
        return {"status": "healthy", "details": {"routing_engine": platform.routing_engine}}

    def _probe_osrm(self, platform: PlatformSettings, *, live: bool = False) -> dict[str, Any]:
        if not platform.osrm_url:
            if (platform.routing_engine or "valhalla").lower() == "valhalla":
                return {"status": "healthy", "details": {"role": "fallback_unused", "primary": "valhalla"}}
            return {"status": "warning", "warnings": ["OSRM URL not configured"]}
        if live:
            base = platform.osrm_url.rstrip("/")
            status, latency, err = _probe_http(f"{base}/route/v1/driving/-79.38,43.65;-79.40,43.66")
            return {"status": status, "latency_ms": latency, "errors": [err] if err else []}
        return {"status": "healthy"}

    def _probe_valhalla(self, platform: PlatformSettings, *, live: bool = False) -> dict[str, Any]:
        base = platform.valhalla_url.rstrip("/")
        url = f"{base}/status" if not base.endswith("/status") else base
        if live:
            status, latency, err = _probe_http(url)
            return {"status": status, "latency_ms": latency, "errors": [err] if err else []}
        status, latency, err = _probe_http(url, timeout=3.0)
        return {
            "status": status if status != "critical" else "warning",
            "latency_ms": latency,
            "warnings": [err] if err else [],
        }

    def _probe_clerk(self, settings: Settings, platform: PlatformSettings) -> dict[str, Any]:
        if settings.clerk_dev_bypass and not is_clerk_configured(settings):
            return {"status": "warning", "warnings": ["Clerk dev bypass active"], "details": {"dev_bypass": True}}
        jwks_entries = clerk_jwks_urls(settings)
        if not jwks_entries and platform.clerk_jwks_url:
            jwks_entries = [("legacy", platform.clerk_jwks_url)]
        if jwks_entries:
            errors: list[str] = []
            latencies: list[int] = []
            for kind, jwks in jwks_entries:
                status, latency, err = _probe_http(jwks)
                latencies.append(latency)
                if err:
                    errors.append(f"{kind}: {err}")
            overall = "healthy" if not errors else ("warning" if len(errors) < len(jwks_entries) else "critical")
            return {
                "status": overall,
                "latency_ms": max(latencies) if latencies else None,
                "errors": errors,
                "details": {"jwks_apps": len(jwks_entries)},
            }
        if is_clerk_secret_configured(settings):
            return {"status": "healthy", "details": {"configured": True}}
        return {"status": "critical", "errors": ["Clerk not configured"]}

    def _probe_stripe(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        if settings.stripe_mock or not settings.stripe_secret:
            return {
                "status": "warning",
                "warnings": ["Stripe mock or unconfigured"],
                "details": {"mock_mode": settings.stripe_mock},
            }
        if live:
            start = time.monotonic()
            try:
                import stripe

                stripe.api_key = settings.stripe_secret
                stripe.Balance.retrieve()
                latency = (time.monotonic() - start) * 1000
                return {"status": "healthy", "latency_ms": latency, "details": {"live": True}}
            except Exception as exc:  # noqa: BLE001
                return {"status": "critical", "errors": [str(exc)]}
        return {"status": "healthy", "details": {"configured": True}}

    def _probe_firebase(self, platform: PlatformSettings) -> dict[str, Any]:
        from porterchain_api.notification_engine.fcm_service import (
            firebase_credentials_configured,
            firebase_production_ready,
        )

        ready, reason = firebase_production_ready()
        if not platform.firebase_project_id:
            return {"status": "warning", "warnings": ["Firebase project not configured"]}
        if not ready:
            return {"status": "critical", "errors": [reason or "Firebase not production-ready"]}
        if not firebase_credentials_configured():
            return {
                "status": "warning",
                "warnings": ["Firebase project set but credentials missing — push is log-only"],
                "details": {"project_id": platform.firebase_project_id},
            }
        return {"status": "healthy", "details": {"project_id": platform.firebase_project_id, "credentials": True}}

    def _probe_websockets(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        ws_url = f"{settings.porterchain_api_url.rstrip('/')}/v1/admin/operations/live-map/ws"
        warnings = ["WebSocket requires Clerk JWT — route registered at operations/live-map/ws"]
        if live:
            warnings.append(f"Endpoint: {ws_url}")
        return {"status": "healthy", "warnings": warnings, "details": {"endpoint": ws_url}}

    def _probe_workers(self, platform: PlatformSettings) -> dict[str, Any]:
        depths = queue_depths()
        total = sum(depths.values()) if depths else 0
        status: HealthClass = "healthy"
        warnings: list[str] = []
        if total > 1000:
            status = "warning"
            warnings.append(f"High queue depth: {total}")
        if not ping_redis() and platform.app_env != "local":
            status = "critical"
            warnings.append("Redis unavailable — workers cannot consume")
        return {"status": status, "warnings": warnings, "details": {"queue_depths": depths}}

    def _probe_scheduled_jobs(self, db: Session) -> dict[str, Any]:
        from porterchain_api.fleetbase_engine import ErrorQueue

        stats = ErrorQueue.stats(db)
        pending = stats.get("pending", 0) + stats.get("retrying", 0)
        return {
            "status": "healthy" if pending < 500 else "warning",
            "details": {"fleetbase_retry_pending": pending},
            "warnings": ["High retry queue"] if pending >= 500 else [],
        }

    def _probe_event_bus(self, platform: PlatformSettings, *, smoke_test: bool = False) -> dict[str, Any]:
        from porterchain_event_bus import get_event_bus

        bus = get_event_bus()
        redis_active = bus._redis_client is not None  # noqa: SLF001
        status: HealthClass = "healthy" if redis_active or platform.app_env == "local" else "warning"
        warnings: list[str] = []
        if not redis_active:
            warnings.append("In-memory event bus (local dev fallback)")
        if smoke_test:
            try:
                from porterchain_api.platform.bus import publish_domain_event

                publish_domain_event(
                    event_type="diagnostics.ping",
                    aggregate_type="system",
                    aggregate_id="diagnostics",
                    payload={"probe": True},
                )
            except Exception as exc:  # noqa: BLE001
                return {"status": "critical", "errors": [str(exc)]}
        return {"status": status, "warnings": warnings, "details": {"redis_streams": redis_active}}

    def _read_dlq(self, platform: PlatformSettings) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        try:
            if platform.redis_url and ping_redis():
                import redis

                client = redis.from_url(platform.redis_url, decode_responses=True)
                entries = client.xrevrange("porterchain:events:dlq", count=20)
                for _mid, fields in entries:
                    items.append(dict(fields))
            else:
                from porterchain_event_bus import get_event_bus

                bus = get_event_bus()
                if hasattr(bus.dlq, "items"):
                    items = bus.dlq.items()[-20:]
        except Exception as exc:  # noqa: BLE001
            items = [{"error": str(exc)}]
        return items

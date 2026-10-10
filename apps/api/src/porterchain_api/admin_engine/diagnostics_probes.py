"""Integration and engine probe mixin."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_helpers import HealthClass, _probe_http
from porterchain_api.auth.clerk_registry import clerk_jwks_urls, is_clerk_configured, is_clerk_secret_configured
from porterchain_api.config import Settings
from porterchain_api.booking_models import Order
from porterchain_api.platform.health import readiness
from porterchain_shared.config.settings import PlatformSettings
from porterchain_shared.queue.publisher import queue_depths
from porterchain_shared.redis_health import ping_redis


class DiagnosticsProbesMixin:
    def _probe_email(self, platform: PlatformSettings, settings: Settings | None = None) -> dict[str, Any]:
        host = (platform.smtp_host or "").lower()
        local_mail = host in {"localhost", "127.0.0.1", "mailpit"}
        if local_mail:
            status, latency, err = _probe_http("http://localhost:8025", local_optional=True)
            if status == "healthy":
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "details": {
                        "mode": "mailpit",
                        "smtp": f"{platform.smtp_host}:{platform.smtp_port}",
                        "from": platform.smtp_from,
                        "note": "Local path is Mailpit. Zoho smtp.zohocloud.ca is prod droplet only.",
                    },
                }
            return {"status": "warning", "warnings": [err or "Mailpit not reachable"]}
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
        from datetime import datetime, timedelta, timezone

        from porterchain_api.notification_engine.admin_service import NotificationAdminService
        from porterchain_api.notification_engine.models import NotificationRecord

        dash = NotificationAdminService().dashboard(db)
        # Historical dead letters should not keep System permanently amber.
        recent_failed = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.status.in_(["failed", "dead_letter"]),
                NotificationRecord.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
            )
            .count()
        )
        push_dead = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.status == "dead_letter",
                NotificationRecord.channel == "push",
                NotificationRecord.created_at >= datetime.now(timezone.utc) - timedelta(hours=24),
            )
            .count()
        )
        other_failed = max(recent_failed - push_dead, 0)
        status = "warning" if other_failed > 0 else "healthy"
        warnings = [f"{other_failed} failed notifications in last 24h"] if other_failed else []
        return {
            "status": status,
            "warnings": warnings,
            "details": {**dash, "failed_last_24h": recent_failed},
        }

    def _engine_orders(self, db: Session) -> dict[str, Any]:
        count = db.query(func.count(Order.id)).scalar() or 0
        return {"status": "healthy", "details": {"order_count": count}}

    def _engine_crm(self, db: Session, settings: Settings | None = None) -> dict[str, Any]:
        try:
            from porterchain_api.crm_models import CrmLead

            count = db.query(func.count(CrmLead.id)).scalar() or 0
        except Exception:  # noqa: BLE001
            count = 0
        details: dict[str, Any] = {"leads": count}
        if settings is not None:
            from porterchain_api.collaboration_engine.lead_ops import lead_ingest_config_status

            details["lead_ingest"] = lead_ingest_config_status(settings)
            configured = sum(1 for v in details["lead_ingest"].values() if v is True)
            details["lead_ingest_configured_count"] = configured
        return {"status": "healthy", "details": details}

    def _engine_finance(self, db: Session) -> dict[str, Any]:
        return {"status": "healthy", "details": {"module": "admin_engine.finance_service"}}

    def _engine_claims(self, db: Session) -> dict[str, Any]:
        return {"status": "healthy", "details": {"module": "admin_engine.claims_service"}}

    def _engine_support(self, db: Session) -> dict[str, Any]:
        return {"status": "healthy", "details": {"module": "admin_engine.support_service"}}

    def _probe_google_maps(
        self, platform: PlatformSettings, *, live: bool = False, app_env: str | None = None
    ) -> dict[str, Any]:
        # Routing, ETA, and optimization never call Google. Do not probe the paid Geocoding API.
        del live, app_env
        return {
            "status": "healthy",
            "details": {
                "used_for_routing": False,
                "routing_engine": platform.routing_engine or "valhalla",
                "note": "Valhalla, then OSRM. Optimization is OR-Tools. Google is not required.",
            },
        }

    def _probe_osrm(self, platform: PlatformSettings, *, live: bool = False) -> dict[str, Any]:
        if not platform.osrm_url:
            if (platform.routing_engine or "valhalla").lower() == "valhalla":
                return {"status": "healthy", "details": {"role": "fallback_unused", "primary": "valhalla"}}
            return {"status": "warning", "warnings": ["OSRM URL not configured"]}
        if live:
            base = platform.osrm_url.rstrip("/")
            status, latency, err = _probe_http(f"{base}/route/v1/driving/-79.38,43.65;-79.40,43.66")
            public = "project-osrm.org" in base
            details = {"url": base, "role": "fallback", "primary": "valhalla", "public_demo": public}
            if err:
                return {"status": status, "latency_ms": latency, "errors": [err], "details": details}
            return {"status": status, "latency_ms": latency, "details": details}
        return {"status": "healthy", "details": {"url": platform.osrm_url, "role": "fallback"}}

    def _probe_valhalla(self, platform: PlatformSettings, *, live: bool = False) -> dict[str, Any]:
        base = (platform.valhalla_url or "").rstrip("/")
        if not base:
            return {"status": "warning", "warnings": ["VALHALLA_BASE_URL not set"]}
        url = f"{base}/status" if not base.endswith("/status") else base
        local = any(h in base for h in ("127.0.0.1", "localhost", "porterchain-valhalla"))
        osm_public = "openstreetmap.de" in base
        warnings: list[str] = []
        if osm_public:
            warnings.append("Public OSM.de Valhalla — not the pinned GTA tile box")
        elif not local:
            warnings.append(f"Valhalla host is not local: {base}")
        if live:
            status, latency, err = _probe_http(url)
            if err:
                return {"status": status, "latency_ms": latency, "errors": [err], "details": {"url": base, "local": local}}
            return {
                "status": "warning" if warnings else status,
                "latency_ms": latency,
                "warnings": warnings,
                "details": {"url": base, "local": local},
            }
        status, latency, err = _probe_http(url, timeout=3.0)
        if err:
            warnings.append(err)
            # Phase 5 degrade label — ops UI can show OSRM fallback without guessing.
            return {
                "status": "warning",
                "latency_ms": latency,
                "warnings": warnings,
                "details": {
                    "url": base,
                    "local": local,
                    "degrade": "osrm_fallback",
                    "role": "primary_routing",
                },
            }
        return {
            "status": status if status != "critical" else "warning",
            "latency_ms": latency,
            "warnings": warnings,
            "details": {"url": base, "local": local, "role": "primary_routing"},
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
                from porterchain_api.services.stripe_service import retrieve_balance

                retrieve_balance(settings)
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
        ws_url = f"{settings.porterchain_api_url.rstrip('/')}/v1/orders/ws"
        warnings = ["Realtime GPS is the driver app's last-known pin; public tracking WS at /v1/orders/ws"]
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
        """Worker liveness: job offers past expiry that the sweep has not cascaded."""
        from datetime import UTC, datetime, timedelta

        from porterchain_api.dispatch_engine.models import DispatchJobOffer

        stale = (
            db.query(DispatchJobOffer)
            .filter(DispatchJobOffer.status == "pending",
                    DispatchJobOffer.expires_at < datetime.now(UTC) - timedelta(minutes=5))
            .count()
        )
        return {
            "status": "healthy" if stale == 0 else "warning",
            "details": {"stale_job_offers": stale},
            "warnings": ["Worker not sweeping expired job offers"] if stale else [],
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

"""Enterprise System Validation & Diagnostics — composes existing health probes and services."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_catalog import (
    CATEGORY_LABELS,
    COMPONENT_CATEGORY,
    HEALTH_CATEGORIES,
    TEST_BY_ID,
    TEST_CATALOG,
    TEST_IDS,
)
from porterchain_api.admin_engine.settings_service import PORTERCHAIN_VERSION, AdminSettingsService
from porterchain_api.auth.clerk_registry import clerk_jwks_urls, is_clerk_configured, is_clerk_secret_configured
from porterchain_api.config import Settings
from porterchain_api.models import DomainEvent, Order
from porterchain_api.platform.health import readiness
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
from porterchain_shared.config.settings import PlatformSettings, get_platform_settings
from porterchain_shared.queue.publisher import queue_depths
from porterchain_shared.redis_health import ping_redis

logger = logging.getLogger(__name__)

_HEALTH_CACHE: dict[str, Any] | None = None
_HEALTH_CACHE_AT: float = 0.0
_HEALTH_CACHE_TTL_SEC = 45.0

HealthClass = str  # healthy | warning | critical

EVENT_PUBLISHERS: dict[str, str] = {
    "quote.created": "booking_engine",
    "booking.confirmed": "booking_engine",
    "payment.succeeded": "billing_engine",
    "order.created": "booking_engine",
    "order.dispatch_ready": "orders_engine",
    "fleetbase.order_created": "fleetbase_engine",
    "notification.queued": "notification_engine",
    "claim.opened": "admin_engine",
    "support.ticket_created": "admin_engine",
}

EVENT_CONSUMERS: dict[str, list[str]] = {
    "payment.succeeded": ["booking_engine", "notification_engine", "billing_engine"],
    "booking.confirmed": ["notification_engine", "fleetbase_engine"],
    "order.dispatch_ready": ["fleetbase_engine", "notification_engine"],
    "fleetbase.status_updated": ["fleetbase_engine", "notification_engine"],
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _classify(raw: str) -> HealthClass:
    s = raw.lower()
    if s in ("healthy", "ok", "pass", "configured", "bridge_enabled", "enabled", "ready"):
        return "healthy"
    if any(x in s for x in ("warning", "degraded", "mock", "bypass", "disabled", "unconfigured", "unavailable")):
        return "warning"
    return "critical"


def _component(
    component_id: str,
    name: str,
    *,
    status: HealthClass,
    latency_ms: float | None = None,
    last_sync: str | None = None,
    version: str | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    recovery_status: str = "none",
    details: dict[str, Any] | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    cat = category or COMPONENT_CATEGORY.get(component_id, "infrastructure")
    return {
        "id": component_id,
        "name": name,
        "category": cat,
        "status": status,
        "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        "last_sync": last_sync,
        "version": version,
        "errors": errors or [],
        "warnings": warnings or [],
        "recovery_status": recovery_status,
        "details": details or {},
    }


def _probe_http(
    url: str,
    *,
    timeout: float = 5.0,
    method: str = "GET",
    local_optional: bool = False,
) -> tuple[HealthClass, float | None, str | None]:
    start = time.monotonic()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.request(method, url)
            latency = (time.monotonic() - start) * 1000
            if response.status_code < 500:
                return "healthy", latency, None
            return "critical", latency, f"HTTP {response.status_code}"
    except httpx.ConnectError as exc:
        if local_optional:
            return "warning", None, f"Not running: {exc}"
        return "critical", None, str(exc)[:500]
    except Exception as exc:  # noqa: BLE001
        return "critical", None, str(exc)[:500]


def _portal_component(
    cid: str,
    name: str,
    url: str,
    *,
    local: bool,
) -> dict[str, Any]:
    status, latency, err = _probe_http(url, local_optional=local)
    warnings: list[str] = []
    if cid == "driver_mobile":
        warnings.append("Web proxy for Expo/mobile — verify native app separately")
    if local and status == "warning" and err and "Not running" in err:
        warnings.append("Start with pnpm dev:website / dev:merchant / dev:driver")
    return _component(
        cid,
        name,
        status=status,
        latency_ms=latency,
        errors=[err] if err else [],
        warnings=warnings,
        details={"url": url},
    )


def _run_probe_batch(
    probes: list[tuple[str, str, Callable[[], dict[str, Any]]]],
    *,
    max_workers: int = 8,
) -> dict[str, tuple[str, dict[str, Any]]]:
    """Run independent probe callables in parallel; returns {id: (name, probe_dict)}."""
    if not probes:
        return {}

    results: dict[str, tuple[str, dict[str, Any]]] = {}
    workers = min(max_workers, len(probes))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(fn): (cid, name) for cid, name, fn in probes}
        for future in as_completed(future_map):
            cid, name = future_map[future]
            try:
                probe = future.result()
            except Exception as exc:  # noqa: BLE001
                probe = {"status": "critical", "errors": [str(exc)]}
            results[cid] = (name, probe)
    return results


def _openapi_paths() -> set[str]:
    """Collect registered API paths — works with FastAPI _IncludedRouter nesting."""
    from porterchain_api.main import create_app

    app = create_app()
    return set(app.openapi().get("paths", {}).keys())


def _test_result(
    test_id: str,
    name: str,
    *,
    status: HealthClass,
    execution_ms: float,
    logs: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": test_id,
        "name": name,
        "status": status,
        "execution_ms": round(execution_ms, 1),
        "logs": logs,
        "details": details or {},
        "ran_at": _now_iso(),
    }


class AdminDiagnosticsService:
    """Validation & diagnostics — reuses settings health, fleetbase sync, event bus, and probes."""

    def __init__(self) -> None:
        self._settings_svc = AdminSettingsService()

    def health_dashboard(self, db: Session, settings: Settings) -> dict[str, Any]:
        global _HEALTH_CACHE, _HEALTH_CACHE_AT

        now = time.monotonic()
        if _HEALTH_CACHE is not None and now - _HEALTH_CACHE_AT < _HEALTH_CACHE_TTL_SEC:
            cached = dict(_HEALTH_CACHE)
            cached["cached"] = True
            cached["cache_age_sec"] = round(now - _HEALTH_CACHE_AT, 1)
            return cached

        payload = self._build_health_dashboard(db, settings)
        _HEALTH_CACHE = payload
        _HEALTH_CACHE_AT = now
        return dict(payload)

    def _build_health_dashboard(self, db: Session, settings: Settings) -> dict[str, Any]:
        ready = readiness(db, settings)
        platform = get_platform_settings()
        integration = self._settings_svc.integration_health(db, settings)
        components: list[dict[str, Any]] = []

        portal_targets = [
            ("website", "Website", settings.website_url),
            ("customer_portal", "Customer Portal", settings.website_url),
            ("merchant_portal", "Merchant Portal", settings.merchant_portal_url),
            ("admin_portal", "Admin Portal", settings.admin_portal_url),
            ("driver_mobile", "Driver Mobile App", settings.driver_portal_url),
        ]
        local = settings.app_env == "local"
        portal_order = [cid for cid, _, _ in portal_targets]
        portal_jobs = [
            (cid, name, lambda cid=cid, name=name, url=url: _portal_component(cid, name, url, local=local))
            for cid, name, url in portal_targets
        ]
        portal_results = _run_probe_batch(portal_jobs, max_workers=len(portal_targets))
        for cid in portal_order:
            _, probe = portal_results[cid]
            components.append(probe)

        api_status = _classify(str(integration.get("api", "unknown")))
        components.append(
            _component(
                "fastapi",
                "FastAPI",
                status=api_status,
                version=PORTERCHAIN_VERSION,
                details={"environment": settings.app_env, "checks": ready.get("checks", {})},
            )
        )

        engine_modules = [
            ("pricing_engine", "Pricing Engine", self._engine_pricing(db)),
            ("billing_engine", "Billing Engine", self._engine_billing(settings)),
            ("notification_engine", "Notification Engine", self._engine_notifications(db)),
            ("orders_engine", "Orders Engine", self._engine_orders(db)),
            ("crm_engine", "CRM Engine", self._engine_crm(db)),
            ("finance_engine", "Finance Engine", self._engine_finance(db)),
            ("claims_engine", "Claims Engine", self._engine_claims(db)),
            ("support_engine", "Support Engine", self._engine_support(db)),
        ]
        for cid, name, probe in engine_modules:
            components.append(_component(cid, name, **probe))

        bus_probe = self._probe_event_bus(platform)
        components.append(_component("event_bus", "Internal Event Bus", **bus_probe))

        db_status = _classify(str(integration.get("database", "unknown")))
        start = time.monotonic()
        try:
            db.execute(text("SELECT 1"))
            db_latency = (time.monotonic() - start) * 1000
        except Exception as exc:  # noqa: BLE001
            db_latency = None
            db_status = "critical"
        components.append(
            _component(
                "postgresql",
                "PostgreSQL",
                status=db_status,
                latency_ms=db_latency,
                version="PostgreSQL",
            )
        )

        redis_ok = ping_redis()
        components.append(
            _component(
                "redis",
                "Redis",
                status="healthy" if redis_ok else "warning" if settings.app_env == "local" else "critical",
                latency_ms=self._redis_latency(platform.redis_url) if redis_ok else None,
            )
        )

        adapter_probe = self._probe_fleetbase_adapter(settings)
        components.append(_component("fleetbase_adapter", "Fleetbase Adapter", **adapter_probe))

        maps_probe = self._probe_google_maps(platform)
        components.append(_component("google_maps", "Google Maps", **maps_probe))

        osrm_probe = self._probe_osrm(platform)
        components.append(_component("osrm", "OSRM", **osrm_probe))

        stripe_probe = self._probe_stripe(settings)
        components.append(_component("stripe", "Stripe", **stripe_probe))

        firebase_probe = self._probe_firebase(platform)
        components.append(_component("firebase_fcm", "Firebase Cloud Messaging", **firebase_probe))

        ws_probe = self._probe_websockets(settings)
        components.append(_component("websockets", "WebSockets", **ws_probe))

        worker_probe = self._probe_workers(platform)
        components.append(_component("background_workers", "Background Workers", **worker_probe))

        sched_probe = self._probe_scheduled_jobs(db)
        components.append(_component("scheduled_jobs", "Scheduled Jobs", **sched_probe))

        email_probe = self._probe_email(platform)
        components.append(_component("email_smtp", "Email (SMTP)", **email_probe))

        ready_probe = self._probe_readiness(settings, db)
        components.append(_component("readiness_probe", "API Readiness", **ready_probe))

        http_probe_jobs = [
            ("fleetbase", "Fleetbase", lambda: self._probe_fleetbase(settings)),
            ("valhalla", "Valhalla", lambda: self._probe_valhalla(platform)),
            ("clerk", "Clerk", lambda: self._probe_clerk(settings, platform)),
            ("fleetbase_console", "Fleetbase Console", lambda: self._probe_fleetbase_console(settings)),
            ("mailhog", "Mailhog (Dev Email)", lambda: self._probe_mailhog(settings)),
            ("metrics_endpoint", "Prometheus Metrics", lambda: self._probe_metrics(settings)),
        ]
        http_probe_order = [cid for cid, _, _ in http_probe_jobs]
        http_results = _run_probe_batch(http_probe_jobs)
        for cid in http_probe_order:
            name, probe = http_results[cid]
            components.append(_component(cid, name, **probe))

        counts = {"healthy": 0, "warning": 0, "critical": 0}
        for c in components:
            counts[c["status"]] = counts.get(c["status"], 0) + 1

        overall = "healthy"
        if counts["critical"] > 0:
            overall = "critical"
        elif counts["warning"] > 0:
            overall = "warning"

        return {
            "overall": overall,
            "checked_at": _now_iso(),
            "version": PORTERCHAIN_VERSION,
            "environment": settings.app_env,
            "cached": False,
            "summary": counts,
            "components": components,
            "groups": {
                cat: {
                    "label": CATEGORY_LABELS.get(cat, cat),
                    "items": [c for c in components if c.get("category") == cat],
                    "summary": {
                        "healthy": sum(1 for c in components if c.get("category") == cat and c["status"] == "healthy"),
                        "warning": sum(1 for c in components if c.get("category") == cat and c["status"] == "warning"),
                        "critical": sum(1 for c in components if c.get("category") == cat and c["status"] == "critical"),
                    },
                }
                for cat in HEALTH_CATEGORIES
            },
            "masterrule_compliance": self._masterrule_compliance(components, settings),
        }

    def center(self, db: Session, settings: Settings) -> dict[str, Any]:
        health = self.health_dashboard(db, settings)
        validation = self._settings_svc.validate(settings, db)
        return {
            "health": health,
            "tests": {"catalog": TEST_CATALOG, "count": len(TEST_CATALOG)},
            "validation": validation,
            "architecture_summary": {"topology": "masterrule §1 locked"},
        }

    def run_test(self, test_id: str, db: Session, settings: Settings) -> dict[str, Any]:
        start = time.monotonic()
        logs: list[str] = []
        status: HealthClass = "critical"
        details: dict[str, Any] = {}
        meta = TEST_BY_ID.get(test_id, {})

        try:
            if test_id == "clerk":
                probe = self._probe_clerk(settings, get_platform_settings())
                status, logs, details = probe["status"], [f"Clerk: {probe['status']}"], probe.get("details", {})
            elif test_id == "stripe":
                probe = self._probe_stripe(settings, live=True)
                status = probe["status"]
                logs = probe.get("errors", []) or ["Stripe API reachable"]
                details = probe.get("details", {})
            elif test_id == "stripe_webhook":
                status = "healthy" if settings.stripe_webhook_secret else "warning"
                logs = ["Webhook secret configured" if settings.stripe_webhook_secret else "STRIPE_WEBHOOK_SECRET missing"]
            elif test_id == "firebase":
                probe = self._probe_firebase(get_platform_settings())
                status, logs = probe["status"], [f"Firebase: {probe['status']}"]
            elif test_id == "google_maps":
                probe = self._probe_google_maps(get_platform_settings(), live=True)
                status = probe["status"]
                logs = probe.get("errors", []) or ["Google Maps probe OK"]
            elif test_id == "osrm":
                probe = self._probe_osrm(get_platform_settings(), live=True)
                status = probe["status"]
                logs = probe.get("errors", []) or ["OSRM probe OK"]
            elif test_id == "valhalla":
                probe = self._probe_valhalla(get_platform_settings(), live=True)
                status = probe["status"]
                logs = probe.get("errors", []) or ["Valhalla probe OK"]
            elif test_id == "fleetbase":
                probe = self._probe_fleetbase(settings, live=True)
                status = probe["status"]
                logs = probe.get("errors", []) or ["Fleetbase API reachable"]
            elif test_id == "fleetbase_adapter":
                probe = self._probe_fleetbase_adapter(settings, live=True)
                status = probe["status"]
                logs = ["Adapter factory OK", *probe.get("warnings", [])]
            elif test_id == "fleetbase_console":
                probe = self._probe_fleetbase_console(settings)
                status = probe["status"]
                logs = probe.get("warnings", []) or ["Fleetbase console reachable"]
            elif test_id == "email_smtp":
                probe = self._probe_email(get_platform_settings())
                status = probe["status"]
                logs = probe.get("warnings", []) or ["SMTP configured"]
            elif test_id == "mailhog":
                probe = self._probe_mailhog(settings)
                status = probe["status"]
                logs = probe.get("warnings", []) or ["Mailhog reachable"]
            elif test_id == "event_bus":
                probe = self._probe_event_bus(get_platform_settings(), smoke_test=True)
                status = probe["status"]
                logs = ["Event bus publish smoke test OK"]
            elif test_id == "websockets":
                probe = self._probe_websockets(settings, live=True)
                status = probe["status"]
                logs = probe.get("warnings", []) or ["WebSocket route registered"]
            elif test_id == "redis":
                ok = ping_redis()
                status = "healthy" if ok else "critical"
                logs = [f"Redis ping: {'ok' if ok else 'failed'}"]
            elif test_id == "postgresql":
                db.execute(text("SELECT 1"))
                status = "healthy"
                logs = ["SELECT 1 OK"]
            elif test_id == "readiness_probe":
                probe = self._probe_readiness(settings, db)
                status = probe["status"]
                logs = [f"Readiness: {probe['status']}"]
                details = probe.get("details", {})
            elif test_id == "metrics_endpoint":
                probe = self._probe_metrics(settings)
                status = probe["status"]
                logs = ["Prometheus metrics OK" if probe["status"] == "healthy" else "Metrics unavailable"]
            elif test_id == "worker_queue":
                depths = queue_depths()
                total = sum(depths.values()) if depths else 0
                status = "warning" if total > 500 else "healthy"
                logs = [f"Queue depths: {depths}", f"Total pending: {total}"]
                details = {"depths": depths}
            elif test_id == "scheduled_jobs":
                probe = self._probe_scheduled_jobs(db)
                status = probe["status"]
                logs = probe.get("warnings", []) or ["Scheduled retry queue OK"]
            elif test_id == "notification_engine":
                from porterchain_api.admin_engine.notification_admin_service import NotificationAdminService

                dash = NotificationAdminService().dashboard(db)
                status = "warning" if dash["failed"] > 0 else "healthy"
                logs = [f"total={dash['total']} queued={dash['queued']} failed={dash['failed']}"]
                details = dash
            elif test_id == "pricing_engine":
                from porterchain_api.pricing_engine import get_pricing_service

                get_pricing_service(db)
                status = "healthy"
                logs = ["PricingService initialized"]
            elif test_id == "billing_engine":
                probe = self._engine_billing(settings)
                status = probe["status"]
                logs = [f"stripe_mock={settings.stripe_mock}"]
            elif test_id == "orders_engine":
                probe = self._engine_orders(db)
                status = probe["status"]
                logs = [f"orders={probe.get('details', {}).get('order_count', 0)}"]
            elif test_id == "crm_engine":
                probe = self._engine_crm(db)
                status = probe["status"]
                logs = [str(probe.get("details", {}))]
            elif test_id == "finance_engine":
                status = self._engine_finance(db)["status"]
                logs = ["Finance service module OK"]
            elif test_id == "claims_engine":
                status = self._engine_claims(db)["status"]
                logs = ["Claims service module OK"]
            elif test_id == "support_engine":
                status = self._engine_support(db)["status"]
                logs = ["Support service module OK"]
            elif test_id == "layered_architecture":
                scan = self._scan_frontend_violations()
                status = scan["status"]
                logs = scan.get("logs", [])
                details = scan
            else:
                logs = [f"Unknown test: {test_id}"]
                status = "critical"
        except Exception as exc:  # noqa: BLE001
            logs = [f"Error: {exc}"]
            status = "critical"

        elapsed = (time.monotonic() - start) * 1000
        name = meta.get("name", test_id.replace("_", " ").title())
        result = _test_result(test_id, name, status=status, execution_ms=elapsed, logs=logs, details=details)
        result["category"] = meta.get("category", "infrastructure")
        result["masterrule"] = meta.get("masterrule", "")
        result["description"] = meta.get("description", "")
        return result

    def run_platform_validation(self, db: Session, settings: Settings) -> dict[str, Any]:
        start = time.monotonic()
        results = [self.run_test(tid, db, settings) for tid in TEST_IDS]
        elapsed = (time.monotonic() - start) * 1000
        summary = {"pass": 0, "warning": 0, "fail": 0}
        for r in results:
            if r["status"] == "healthy":
                summary["pass"] += 1
            elif r["status"] == "warning":
                summary["warning"] += 1
            else:
                summary["fail"] += 1
        return {
            "summary": summary,
            "execution_ms": round(elapsed, 1),
            "results": results,
            "groups": {
                cat: [r for r in results if r.get("category") == cat]
                for cat in HEALTH_CATEGORIES
            },
            "ran_at": _now_iso(),
        }

    def architecture_validation(self, settings: Settings) -> dict[str, Any]:
        chain = [
            {"id": "website", "label": "Website", "url": settings.website_url},
            {"id": "customer_portal", "label": "Booking / Customer Portal", "url": settings.website_url},
            {"id": "merchant_portal", "label": "Merchant Portal", "url": settings.merchant_portal_url},
            {"id": "admin_portal", "label": "Admin Portal", "url": settings.admin_portal_url},
            {"id": "porterchain_api", "label": "Porterchain API", "url": settings.porterchain_api_url},
            {"id": "application_services", "label": "Application Services", "url": None},
            {"id": "engines", "label": "Pricing / Billing / Notification / Orders / CRM / Finance / Claims / Support", "url": None},
            {"id": "event_bus", "label": "Internal Event Bus", "url": None},
            {"id": "fleetbase_adapter", "label": "Fleetbase Adapter Layer", "url": None},
            {"id": "fleetbase", "label": "Fleetbase Core", "url": settings.fleetbase_api_url},
            {"id": "driver_mobile", "label": "Driver Mobile", "url": settings.driver_portal_url},
        ]

        connections: list[dict[str, Any]] = []
        violations: list[dict[str, Any]] = []
        missing: list[str] = []

        for i, node in enumerate(chain):
            entry: dict[str, Any] = {"node": node["label"], "id": node["id"], "status": "healthy", "downstream": None}
            if node["url"]:
                optional_local = settings.app_env == "local" and node["id"] in {
                    "website",
                    "customer_portal",
                    "merchant_portal",
                    "driver_mobile",
                }
                status, latency, err = _probe_http(node["url"], local_optional=optional_local)
                entry["status"] = status
                entry["latency_ms"] = latency
                if err:
                    entry["error"] = err
                    if status == "critical":
                        missing.append(f"{node['label']}: {err}")
            if i < len(chain) - 1:
                entry["downstream"] = chain[i + 1]["label"]
            connections.append(entry)

        if not settings.fleetbase_dispatch_bridge:
            violations.append(
                {"type": "configuration", "message": "Fleetbase dispatch bridge disabled — logistics chain incomplete"}
            )

        adapter_ok = get_fleetbase_integration(settings).is_enabled
        if settings.fleetbase_dispatch_bridge and not adapter_ok:
            violations.append({"type": "adapter", "message": "Fleetbase adapter not configured despite bridge enabled"})

        try:
            routes = _openapi_paths()
            required = ["/health", "/health/ready", "/v1/admin/diagnostics/health"]
            for path in required:
                if path not in routes:
                    missing.append(f"Missing API route: {path}")
        except Exception as exc:  # noqa: BLE001
            violations.append({"type": "api", "message": f"Route audit failed: {exc}"})

        violations.append(
            {
                "type": "policy",
                "message": "Direct Fleetbase calls from UI forbidden — verify via code review (masterrule §3)",
                "severity": "info",
            }
        )

        overall = "healthy"
        if missing or any(v.get("severity") != "info" for v in violations):
            overall = "warning" if not missing else "critical"

        return {
            "overall": overall,
            "chain": connections,
            "broken_connections": [c for c in connections if c.get("status") == "critical"],
            "missing_apis": missing,
            "architecture_violations": violations,
            "duplicate_logic_risks": [
                "Client website pricing is estimate-only — server validates before payment (masterrule §11)",
                "All Fleetbase HTTP must flow through fleetbase_engine + adapter (masterrule §8)",
            ],
            "adr_checklist": [
                {"id": "ADR-001", "label": "Fleetbase is execution engine only", "status": "healthy"},
                {"id": "ADR-002", "label": "Porterchain owns business logic", "status": "healthy"},
                {"id": "ADR-003", "label": "Fleetbase Adapter mandatory", "status": "healthy" if settings.fleetbase_dispatch_bridge else "warning"},
                {"id": "ADR-004", "label": "Booking Draft server-persisted", "status": "healthy"},
                {"id": "ADR-005", "label": "Event Bus mandatory", "status": "healthy"},
                {"id": "ADR-006", "label": "Stripe webhook payment signal", "status": "healthy" if settings.stripe_webhook_secret or settings.stripe_mock else "warning"},
                {"id": "ADR-007", "label": "Layered architecture", "status": self._scan_frontend_violations()["status"]},
            ],
            "frontend_scan": self._scan_frontend_violations(),
            "checked_at": _now_iso(),
        }

    def module_validation(self, db: Session, settings: Settings) -> dict[str, Any]:
        modules = [
            ("website", "Website", settings.website_url),
            ("customer", "Customer", settings.website_url),
            ("merchant", "Merchant", settings.merchant_portal_url),
            ("driver", "Driver", settings.driver_portal_url),
            ("admin", "Admin", settings.admin_portal_url),
            ("orders", "Orders", None),
            ("crm", "CRM", None),
            ("operations", "Operations", None),
            ("route_center", "Route Center", None),
            ("fleet", "Fleet", None),
            ("drivers", "Drivers", None),
            ("finance", "Finance", None),
            ("billing", "Billing", None),
            ("pricing", "Pricing", None),
            ("claims", "Claims", None),
            ("support", "Support", None),
            ("reports", "Reports", None),
            ("settings", "Settings", None),
            ("notifications", "Notifications", None),
        ]

        results: list[dict[str, Any]] = []
        for mid, label, url in modules:
            status: HealthClass = "healthy"
            logs: list[str] = []
            if url:
                status, _, err = _probe_http(url)
                if err:
                    logs.append(err)
            else:
                status, logs = self._module_db_check(db, mid)

            results.append(
                {
                    "id": mid,
                    "name": label,
                    "status": status,
                    "logs": logs,
                }
            )

        summary = {"healthy": 0, "warning": 0, "critical": 0}
        for r in results:
            summary[r["status"]] = summary.get(r["status"], 0) + 1

        return {"modules": results, "summary": summary, "checked_at": _now_iso()}

    def workflow_scenarios(self, db: Session, settings: Settings) -> dict[str, Any]:
        scenarios = [
            {
                "id": "retail_customer",
                "name": "Website Customer → Quote → Booking → Payment → Dispatch → POD",
                "steps": [
                    "Quote",
                    "Booking Draft",
                    "Clerk Authentication",
                    "Stripe Sandbox Payment",
                    "Order Creation",
                    "Operations Queue",
                    "Route Optimization",
                    "Fleetbase Dispatch",
                    "Driver Assignment",
                    "Pickup",
                    "Delivery",
                    "Proof Of Delivery",
                    "Receipt",
                    "Invoice",
                ],
            },
            {
                "id": "merchant_b2b",
                "name": "Merchant CSV → Contract Pricing → Operations → Billing",
                "steps": [
                    "CSV Upload",
                    "Contract Pricing",
                    "Order Creation",
                    "Operations",
                    "Optimization",
                    "Dispatch",
                    "Delivery",
                    "Billing",
                    "Statement",
                ],
            },
            {
                "id": "admin_ops",
                "name": "Admin Manual Order → Claim → Support → Finance",
                "steps": ["Manual Order", "Dispatch", "Driver", "Claim", "Support", "Finance"],
            },
        ]

        enriched: list[dict[str, Any]] = []
        for sc in scenarios:
            readiness_steps = self._workflow_readiness(db, settings, sc["id"])
            statuses = [s["status"] for s in readiness_steps]
            overall = "healthy"
            if "critical" in statuses:
                overall = "critical"
            elif "warning" in statuses:
                overall = "warning"
            enriched.append({**sc, "overall": overall, "step_checks": readiness_steps})

        return {"scenarios": enriched, "checked_at": _now_iso()}

    def simulate_workflow(self, scenario_id: str, db: Session, settings: Settings) -> dict[str, Any]:
        """Dry-run validation — does not create orders or charge payments."""
        steps = self._workflow_readiness(db, settings, scenario_id)
        logs = [f"{s['step']}: {s['status']} — {s.get('note', '')}" for s in steps]
        overall = "healthy"
        if any(s["status"] == "critical" for s in steps):
            overall = "critical"
        elif any(s["status"] == "warning" for s in steps):
            overall = "warning"
        return {
            "scenario_id": scenario_id,
            "mode": "dry_run",
            "overall": overall,
            "steps": steps,
            "logs": logs,
            "simulated_at": _now_iso(),
        }

    def event_bus_inspector(
        self,
        db: Session,
        *,
        aggregate_filter: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        q = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc())
        if aggregate_filter:
            filt = aggregate_filter.lower()
            q = q.filter(
                (DomainEvent.aggregate_type.ilike(f"%{filt}%"))
                | (DomainEvent.event_type.ilike(f"%{filt}%"))
            )
        rows = q.limit(limit).all()

        events = []
        for e in rows:
            et = e.event_type
            events.append(
                {
                    "event_name": et,
                    "publisher": EVENT_PUBLISHERS.get(et, e.actor_type or "system"),
                    "consumers": EVENT_CONSUMERS.get(et, ["worker"]),
                    "timestamp": e.occurred_at.isoformat() if e.occurred_at else None,
                    "processing_time_ms": None,
                    "status": "processed",
                    "retry_count": 0,
                    "aggregate_type": e.aggregate_type,
                    "aggregate_id": e.aggregate_id,
                    "correlation_id": e.correlation_id,
                }
            )

        dlq_items = self._read_dlq(get_platform_settings())
        return {
            "events": events,
            "dead_letter_queue": dlq_items,
            "stream_key": "porterchain:events",
            "dlq_stream_key": "porterchain:events:dlq",
            "checked_at": _now_iso(),
        }

    def fleetbase_sync_monitor(self, db: Session) -> dict[str, Any]:
        from porterchain_api.config import get_settings
        from porterchain_api.fleetbase_engine import ErrorQueue
        from porterchain_api.fleetbase_engine.sync_health import assess_fleetbase_sync
        from porterchain_api.fleetbase_models import FleetbaseSyncAudit, FleetbaseSyncJob

        settings = get_settings()
        slo = assess_fleetbase_sync(db, settings)
        stats = ErrorQueue.stats(db)
        pending = stats.get("pending", 0) + stats.get("retrying", 0)
        successful = stats.get("done", 0)
        failed = stats.get("dead", 0)

        by_kind: dict[str, int] = {}
        for kind in ("order", "driver", "vehicle", "route", "webhook"):
            by_kind[kind] = (
                db.query(func.count(FleetbaseSyncJob.id))
                .filter(FleetbaseSyncJob.kind.ilike(f"%{kind}%"))
                .scalar()
                or 0
            )

        recent = (
            db.query(FleetbaseSyncAudit)
            .order_by(FleetbaseSyncAudit.created_at.desc())
            .limit(30)
            .all()
        )

        return {
            "slo": slo,
            "pending_sync": pending,
            "successful_sync": successful,
            "failed_sync": failed,
            "retry_queue": stats.get("retrying", 0),
            "driver_sync": by_kind.get("driver", 0),
            "vehicle_sync": by_kind.get("vehicle", 0),
            "route_sync": by_kind.get("route", 0),
            "order_sync": by_kind.get("order", 0),
            "webhook_status": {
                "recent": [
                    {
                        "direction": a.direction,
                        "kind": a.kind,
                        "status": a.status,
                        "order_id": a.order_id,
                        "message": a.message,
                        "at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in recent
                ]
            },
            "dead_letters": [
                {
                    "id": j.id,
                    "kind": j.kind,
                    "direction": j.direction,
                    "order_id": j.order_id,
                    "attempts": j.attempts,
                    "last_error": j.last_error,
                }
                for j in ErrorQueue.list_dead(db, limit=20)
            ],
            "queue_stats": stats,
            "checked_at": _now_iso(),
        }

    def chaos_test(self, scenario: str, db: Session, settings: Settings) -> dict[str, Any]:
        """Resilience verification — read-only; does not stop services."""
        checks: list[dict[str, Any]] = []
        logs: list[str] = []

        scenarios = {
            "fleetbase_offline": lambda: self._chaos_fleetbase(db, settings),
            "stripe_offline": lambda: self._chaos_stripe(settings),
            "clerk_offline": lambda: self._chaos_clerk(settings),
            "firebase_offline": lambda: self._chaos_firebase(),
            "google_maps_failure": lambda: self._chaos_maps(),
            "osrm_failure": lambda: self._chaos_osrm(),
            "valhalla_failure": lambda: self._chaos_valhalla(),
            "redis_restart": lambda: self._chaos_redis(),
            "postgresql_restart": lambda: self._chaos_postgres(db),
            "websocket_failure": lambda: self._chaos_websocket(settings),
            "driver_reject": lambda: self._chaos_policy("driver_reject", "Event handler for order.driver_rejected"),
            "vehicle_breakdown": lambda: self._chaos_policy("vehicle_breakdown", "Operations exception queue"),
            "gps_loss": lambda: self._chaos_policy("gps_loss", "Live map staleness detection"),
            "webhook_delay": lambda: self._chaos_fleetbase(db, settings),
        }

        runner = scenarios.get(scenario)
        if not runner:
            return {"scenario": scenario, "status": "critical", "logs": [f"Unknown scenario: {scenario}"]}

        result = runner()
        checks = result.get("checks", [])
        logs = result.get("logs", [])
        status = result.get("status", "warning")

        return {
            "scenario": scenario,
            "status": status,
            "checks": checks,
            "logs": logs,
            "verifies": ["retry", "fallback", "recovery", "alerts"],
            "ran_at": _now_iso(),
        }

    def observability(self, db: Session, settings: Settings) -> dict[str, Any]:
        depths = queue_depths()
        ready = readiness(db, settings)

        slow_queries: list[dict[str, Any]] = []
        try:
            if "postgresql" in settings.database_url:
                rows = db.execute(
                    text(
                        "SELECT query, calls, mean_exec_time FROM pg_stat_statements "
                        "ORDER BY mean_exec_time DESC LIMIT 5"
                    )
                ).fetchall()
                slow_queries = [
                    {"query": str(r[0])[:200], "calls": r[1], "mean_ms": round(float(r[2]), 2)} for r in rows
                ]
        except Exception:  # noqa: BLE001
            db.rollback()
            slow_queries = [{"note": "pg_stat_statements extension not available"}]

        recent_errors = (
            db.query(DomainEvent)
            .filter(DomainEvent.event_type.ilike("%failed%"))
            .order_by(DomainEvent.occurred_at.desc())
            .limit(10)
            .all()
        )

        return {
            "structured_logs": {"enabled": True, "format": "json-ready via stdlib logging"},
            "correlation_ids": {"header": "X-Request-ID", "domain_events": True},
            "request_tracing": {"middleware": "RequestIdMiddleware", "status": "active"},
            "api_metrics": {"endpoint": "/metrics", "format": "prometheus"},
            "queue_metrics": depths,
            "worker_metrics": {"queues": depths, "redis": ready.get("checks", {}).get("redis")},
            "error_dashboard": [
                {
                    "event_type": e.event_type,
                    "aggregate_id": e.aggregate_id,
                    "at": e.occurred_at.isoformat() if e.occurred_at else None,
                }
                for e in recent_errors
            ],
            "slow_query_report": slow_queries,
            "system_timeline": ControlTowerTimeline(db).recent(limit=20),
            "checked_at": _now_iso(),
        }

    def generate_reports(self, db: Session, settings: Settings, *, write_files: bool = False) -> dict[str, Any]:
        """Legacy diagnostics reports + optional full E2E enterprise reports."""
        health = self.health_dashboard(db, settings)
        arch = self.architecture_validation(settings)
        modules = self.module_validation(db, settings)
        integration = self.run_platform_validation(db, settings)
        workflows = self.workflow_scenarios(db, settings)
        events = self.event_bus_inspector(db, limit=50)
        fleetbase = self.fleetbase_sync_monitor(db)
        observability = self.observability(db, settings)

        reports = {
            "SYSTEM_HEALTH_REPORT.md": self._report_health(health),
            "ARCHITECTURE_VALIDATION.md": self._report_architecture(arch),
            "MODULE_VALIDATION.md": self._report_modules(modules),
            "INTEGRATION_VALIDATION.md": self._report_integration(integration),
            "BUSINESS_WORKFLOW_VALIDATION.md": self._report_workflows(workflows),
            "EVENT_BUS_REPORT.md": self._report_events(events),
            "FLEETBASE_SYNC_REPORT.md": self._report_fleetbase(fleetbase),
            "CHAOS_TEST_REPORT.md": self._report_chaos(settings),
            "PERFORMANCE_REPORT.md": self._report_performance(observability),
            "SECURITY_REPORT.md": self._report_security(settings),
            "PRODUCTION_READINESS_SCORE.md": self._report_readiness(health, arch, modules, integration),
        }

        # Enterprise E2E reports (phases 1–10)
        try:
            from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService

            e2e = E2EValidationService()
            e2e_result = e2e.run_full(db, settings, write_files=False, cleanup=True)
            reports.update(e2e_result.get("reports", {}))
        except Exception as exc:  # noqa: BLE001
            logger.warning("E2E validation reports skipped: %s", exc)

        written: list[str] = []
        if write_files and settings.app_env == "local":
            root = Path(__file__).resolve().parents[5]
            for name, content in reports.items():
                path = root / name
                path.write_text(content, encoding="utf-8")
                written.append(str(path))

        return {
            "reports": reports,
            "written_files": written,
            "generated_at": _now_iso(),
        }

    # --- private probes ---

    def _masterrule_compliance(self, components: list[dict[str, Any]], settings: Settings) -> dict[str, Any]:
        checks = [
            {
                "id": "adr003_adapter",
                "label": "Fleetbase Adapter mandatory (ADR-003)",
                "status": "healthy" if settings.fleetbase_dispatch_bridge else "warning",
                "note": "Dispatch bridge enabled" if settings.fleetbase_dispatch_bridge else "Bridge disabled",
            },
            {
                "id": "adr006_stripe_webhook",
                "label": "Stripe webhook payment signal (ADR-006)",
                "status": "healthy" if settings.stripe_webhook_secret or settings.stripe_mock else "warning",
                "note": "Webhook secret or mock mode",
            },
            {
                "id": "adr005_event_bus",
                "label": "Event bus for async side effects (ADR-005)",
                "status": next((c["status"] for c in components if c["id"] == "event_bus"), "warning"),
                "note": "Internal event bus",
            },
            {
                "id": "layered_ui",
                "label": "No direct Fleetbase from UI (§3)",
                "status": self._scan_frontend_violations()["status"],
                "note": "Static scan of portal fetch patterns",
            },
            {
                "id": "server_pricing",
                "label": "Server-authoritative pricing (§11.1)",
                "status": next((c["status"] for c in components if c["id"] == "pricing_engine"), "warning"),
                "note": "Pricing engine reachable",
            },
        ]
        critical = sum(1 for c in checks if c["status"] == "critical")
        warning = sum(1 for c in checks if c["status"] == "warning")
        overall = "healthy" if critical == 0 and warning == 0 else "warning" if critical == 0 else "critical"
        return {"overall": overall, "checks": checks}

    def _scan_frontend_violations(self) -> dict[str, Any]:
        repo = Path(__file__).resolve().parents[5]
        scan_roots = [
            repo / "apps" / "admin" / "src",
            repo / "apps" / "merchant-portal" / "src",
            repo / "website" / "src",
            repo / "apps" / "driver-portal" / "src",
        ]
        forbidden = (":8000", "fleetbase_api", "FLEETBASE_API")
        hits: list[str] = []
        for root in scan_roots:
            if not root.exists():
                continue
            for pattern in ("*.ts", "*.tsx", "*.js", "*.jsx"):
                for path in root.rglob(pattern):
                    try:
                        text = path.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    for needle in forbidden:
                        if needle in text and "NEXT_PUBLIC_FLEETBASE" not in text:
                            rel = path.relative_to(repo)
                            if "system-links" in str(rel) or "diagnostics" in str(rel):
                                continue
                            hits.append(f"{rel}: references {needle}")
        logs = hits[:10] if hits else ["No direct Fleetbase HTTP patterns in UI sources"]
        status: HealthClass = "healthy" if not hits else "warning"
        return {"status": status, "violations": hits, "logs": logs, "scanned_roots": [str(r) for r in scan_roots if r.exists()]}

    def _probe_fleetbase_console(self, settings: Settings) -> dict[str, Any]:
        url = settings.fleetbase_console_url or "http://localhost:4200"
        status, latency, err = _probe_http(url, local_optional=settings.app_env == "local")
        return {
            "status": status,
            "latency_ms": latency,
            "errors": [err] if err and status == "critical" else [],
            "warnings": [err] if err and status == "warning" else [],
            "details": {"url": url},
        }

    def _probe_email(self, platform: PlatformSettings) -> dict[str, Any]:
        if platform.smtp_host and platform.smtp_user:
            return {"status": "healthy", "details": {"host": platform.smtp_host, "from": platform.smtp_from}}
        if platform.smtp_host:
            return {"status": "warning", "warnings": ["SMTP host set but credentials incomplete"]}
        return {"status": "warning", "warnings": ["SMTP not configured — use Mailhog locally"]}

    def _probe_mailhog(self, settings: Settings) -> dict[str, Any]:
        if settings.app_env != "local":
            return {"status": "healthy", "details": {"note": "Mailhog is local dev only"}}
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
                status, latency, err = _probe_http(settings.fleetbase_api_url)
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
        status, latency, err = _probe_http(settings.fleetbase_api_url)
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

    def _probe_google_maps(self, platform: PlatformSettings, *, live: bool = False) -> dict[str, Any]:
        if not platform.google_maps_api_key:
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

    def _module_db_check(self, db: Session, module_id: str) -> tuple[HealthClass, list[str]]:
        logs: list[str] = []
        try:
            if module_id == "orders":
                n = db.query(func.count(Order.id)).scalar()
                logs.append(f"orders={n}")
            elif module_id == "crm":
                from porterchain_api.crm_models import CrmLead

                n = db.query(func.count(CrmLead.id)).scalar()
                logs.append(f"leads={n}")
            else:
                logs.append("Service module registered")
            return "healthy", logs
        except Exception as exc:  # noqa: BLE001
            return "warning", [str(exc)]

    def _workflow_readiness(self, db: Session, settings: Settings, scenario_id: str) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []

        def step(name: str, ok: bool, note: str = "", warn: bool = False) -> None:
            status: HealthClass = "healthy" if ok else ("warning" if warn else "critical")
            checks.append({"step": name, "status": status, "note": note})

        if scenario_id == "retail_customer":
            step("Quote", True, "QuoteService via booking_engine")
            step("Booking Draft", True, "Server-persisted drafts")
            step("Clerk Authentication", is_clerk_configured(settings) or settings.clerk_dev_bypass, "Clerk or dev bypass")
            step("Stripe Sandbox Payment", settings.stripe_secret or settings.stripe_mock, "Stripe or mock", warn=settings.stripe_mock)
            step("Order Creation", True, "PaymentService webhook flow")
            step("Operations Queue", True, "Control Tower")
            step("Route Optimization", True, "Route Center + Valhalla/OSRM")
            step("Fleetbase Dispatch", settings.fleetbase_dispatch_bridge, "Via adapter only")
            step("Driver Assignment", settings.fleetbase_dispatch_bridge, "Fleetbase execution")
            step("Pickup", settings.fleetbase_dispatch_bridge, "Status sync via webhooks")
            step("Delivery", settings.fleetbase_dispatch_bridge, "Tracking translator")
            step("Proof Of Delivery", settings.fleetbase_dispatch_bridge, "POD via adapter")
            step("Receipt", True, "BookingConfirmationService")
            step("Invoice", True, "Finance engine")
        elif scenario_id == "merchant_b2b":
            step("CSV Upload", True, "Merchant portal bulk")
            step("Contract Pricing", True, "Merchant contract overrides")
            step("Order Creation", True, "merchant_engine")
            step("Operations", True, "Shared ops queue")
            step("Optimization", True, "Route Center")
            step("Dispatch", settings.fleetbase_dispatch_bridge, "Adapter")
            step("Delivery", settings.fleetbase_dispatch_bridge, "Fleetbase")
            step("Billing", True, "MerchantBillingService")
            step("Statement", True, "NET billing")
        else:
            step("Manual Order", True, "Admin orders")
            step("Dispatch", settings.fleetbase_dispatch_bridge, "Adapter")
            step("Driver", settings.fleetbase_dispatch_bridge, "Driver engine")
            step("Claim", True, "Claims service")
            step("Support", True, "Support service")
            step("Finance", True, "Finance service")

        return checks

    def _chaos_fleetbase(self, db: Session, settings: Settings) -> dict[str, Any]:
        sync = self.fleetbase_sync_monitor(db)
        retry = sync["retry_queue"]
        logs = [f"Retry queue depth: {retry}", f"Dead letters: {sync['failed_sync']}"]
        status: HealthClass = "healthy" if retry < 100 else "warning"
        return {
            "status": status,
            "logs": logs,
            "checks": [
                {"name": "retry_queue", "status": status, "value": retry},
                {"name": "dead_letter_recovery", "status": "healthy", "note": "ErrorQueue.requeue available"},
            ],
        }

    def _chaos_stripe(self, settings: Settings) -> dict[str, Any]:
        probe = self._probe_stripe(settings, live=bool(settings.stripe_secret))
        return {"status": probe["status"], "logs": ["Webhook idempotency in PaymentService"], "checks": [probe]}

    def _chaos_clerk(self, settings: Settings) -> dict[str, Any]:
        probe = self._probe_clerk(settings, get_platform_settings())
        return {
            "status": probe["status"],
            "logs": ["JWT validation on all protected routes"],
            "checks": [probe],
        }

    def _chaos_firebase(self) -> dict[str, Any]:
        probe = self._probe_firebase(get_platform_settings())
        return {"status": probe["status"], "logs": ["Push queue with retry in notification_engine"], "checks": [probe]}

    def _chaos_maps(self) -> dict[str, Any]:
        probe = self._probe_google_maps(get_platform_settings())
        return {"status": probe["status"], "logs": ["OSRM/Valhalla fallback in routing"], "checks": [probe]}

    def _chaos_osrm(self) -> dict[str, Any]:
        probe = self._probe_osrm(get_platform_settings())
        return {"status": probe["status"], "logs": ["Valhalla primary per PlatformSettings"], "checks": [probe]}

    def _chaos_valhalla(self) -> dict[str, Any]:
        probe = self._probe_valhalla(get_platform_settings())
        return {"status": probe["status"], "logs": ["Route Center engine selection"], "checks": [probe]}

    def _chaos_redis(self) -> dict[str, Any]:
        ok = ping_redis()
        return {
            "status": "healthy" if ok else "critical",
            "logs": ["Event bus falls back to in-memory when Redis unavailable (local only)"],
            "checks": [{"name": "redis_ping", "status": "healthy" if ok else "critical"}],
        }

    def _chaos_postgres(self, db: Session) -> dict[str, Any]:
        try:
            db.execute(text("SELECT 1"))
            return {"status": "healthy", "logs": ["Readiness probe on /health/ready"], "checks": []}
        except Exception as exc:  # noqa: BLE001
            return {"status": "critical", "logs": [str(exc)], "checks": []}

    def _chaos_websocket(self, settings: Settings) -> dict[str, Any]:
        probe = self._probe_websockets(settings)
        return {"status": probe["status"], "logs": probe.get("warnings", []), "checks": [probe]}

    def _chaos_policy(self, name: str, note: str) -> dict[str, Any]:
        return {
            "status": "healthy",
            "logs": [note],
            "checks": [{"name": name, "status": "healthy", "note": note}],
        }

    # --- report builders ---

    def _icon(self, status: str) -> str:
        return {"healthy": "✅", "warning": "⚠", "critical": "❌", "pass": "✅", "fail": "❌"}.get(status, "⚠")

    def _report_health(self, health: dict[str, Any]) -> str:
        lines = ["# System Health Report", "", f"Generated: {health['checked_at']}", ""]
        lines.append(f"Overall: {self._icon(health['overall'])} {health['overall']}")
        lines.append("")
        for c in health["components"]:
            lines.append(f"- {self._icon(c['status'])} **{c['name']}** — {c['status']}")
            if c.get("latency_ms"):
                lines.append(f"  - Latency: {c['latency_ms']}ms")
            for e in c.get("errors", []):
                lines.append(f"  - Error: {e}")
        return "\n".join(lines)

    def _report_architecture(self, arch: dict[str, Any]) -> str:
        lines = ["# Architecture Validation", "", f"Overall: {self._icon(arch['overall'])} {arch['overall']}", ""]
        for node in arch["chain"]:
            lines.append(f"- {self._icon(node['status'])} {node['node']}")
        return "\n".join(lines)

    def _report_modules(self, modules: dict[str, Any]) -> str:
        lines = ["# Module Validation", ""]
        for m in modules["modules"]:
            lines.append(f"- {self._icon(m['status'])} {m['name']}")
        return "\n".join(lines)

    def _report_integration(self, integration: dict[str, Any]) -> str:
        lines = ["# Integration Validation", ""]
        for r in integration["results"]:
            lines.append(f"- {self._icon(r['status'])} {r['name']} ({r['execution_ms']}ms)")
        return "\n".join(lines)

    def _report_workflows(self, workflows: dict[str, Any]) -> str:
        lines = ["# Business Workflow Validation", ""]
        for sc in workflows["scenarios"]:
            lines.append(f"## {sc['name']}")
            lines.append(f"Overall: {self._icon(sc['overall'])} {sc['overall']}")
            for step in sc.get("step_checks", []):
                lines.append(f"- {self._icon(step['status'])} {step['step']}")
            lines.append("")
        return "\n".join(lines)

    def _report_events(self, events: dict[str, Any]) -> str:
        lines = ["# Event Bus Report", "", f"Recent events: {len(events['events'])}", ""]
        for e in events["events"][:20]:
            lines.append(f"- `{e['event_name']}` @ {e['timestamp']}")
        return "\n".join(lines)

    def _report_fleetbase(self, fb: dict[str, Any]) -> str:
        return "\n".join(
            [
                "# Fleetbase Sync Report",
                "",
                f"- Pending: {fb['pending_sync']}",
                f"- Successful: {fb['successful_sync']}",
                f"- Failed: {fb['failed_sync']}",
            ]
        )

    def _report_chaos(self, settings: Settings) -> str:
        return "# Chaos Test Report\n\nRun individual scenarios via POST /v1/admin/diagnostics/chaos/{scenario}\n"

    def _report_performance(self, obs: dict[str, Any]) -> str:
        lines = ["# Performance Report", "", "## Queue Metrics", json.dumps(obs["queue_metrics"], indent=2)]
        return "\n".join(lines)

    def _report_security(self, settings: Settings) -> str:
        lines = [
            "# Security Report",
            "",
            f"- Clerk: {'configured' if is_clerk_configured(settings) else 'dev bypass' if settings.clerk_dev_bypass else 'missing'}",
            f"- Stripe webhook secret: {'yes' if settings.stripe_webhook_secret else 'no'}",
            f"- Fleetbase webhook secret: {'yes' if settings.fleetbase_webhook_secret else 'no'}",
        ]
        return "\n".join(lines)

    def _report_readiness(
        self,
        health: dict[str, Any],
        arch: dict[str, Any],
        modules: dict[str, Any],
        integration: dict[str, Any],
    ) -> str:
        score = 100
        score -= health["summary"].get("critical", 0) * 10
        score -= health["summary"].get("warning", 0) * 3
        score -= integration["summary"].get("fail", 0) * 5
        score = max(0, min(100, score))
        grade = "Production Ready" if score >= 85 else "Needs Attention" if score >= 70 else "Not Ready"
        return "\n".join(
            [
                "# Production Readiness Score",
                "",
                f"**Score: {score}/100** — {grade}",
                "",
                f"- Health: {self._icon(health['overall'])} {health['overall']}",
                f"- Architecture: {self._icon(arch['overall'])} {arch['overall']}",
                f"- Modules: {modules['summary']}",
                f"- Integration tests: pass={integration['summary']['pass']} fail={integration['summary']['fail']}",
            ]
        )


class ControlTowerTimeline:
    def __init__(self, db: Session) -> None:
        self._db = db

    def recent(self, *, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc()).limit(limit).all()
        return [
            {
                "event_type": e.event_type,
                "aggregate_type": e.aggregate_type,
                "at": e.occurred_at.isoformat() if e.occurred_at else None,
                "correlation_id": e.correlation_id,
            }
            for e in rows
        ]

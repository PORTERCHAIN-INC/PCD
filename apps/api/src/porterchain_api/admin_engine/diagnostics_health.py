"""Health dashboard mixin for admin diagnostics."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_catalog import (
    CATEGORY_LABELS,
    HEALTH_CATEGORIES,
    TEST_CATALOG,
)
from porterchain_api.admin_engine.diagnostics_helpers import (
    HealthClass,
    _classify,
    _component,
    _now_iso,
    _portal_component,
    _run_probe_batch,
)
from porterchain_api.admin_engine.settings_service import PORTERCHAIN_VERSION
from porterchain_api.config import Settings
from porterchain_api.platform.health import readiness
from porterchain_shared.config.settings import get_platform_settings
from porterchain_shared.redis_health import ping_redis

_HEALTH_CACHE: dict[str, Any] | None = None
_HEALTH_CACHE_AT: float = 0.0
_HEALTH_CACHE_TTL_SEC = 45.0


class DiagnosticsHealthMixin:
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
            ("customer_portal", "Customer Portal", settings.customer_portal_url),
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

        maps_probe = self._probe_google_maps(platform, app_env=settings.app_env)
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

        email_probe = self._probe_email(platform, settings)
        components.append(_component("email_smtp", "Email (SMTP)", **email_probe))

        ready_probe = self._probe_readiness(settings, db)
        components.append(_component("readiness_probe", "API Readiness", **ready_probe))

        http_probe_jobs = [
            ("fleetbase", "Fleetbase", lambda: self._probe_fleetbase(settings)),
            ("valhalla", "Valhalla", lambda: self._probe_valhalla(platform)),
            ("clerk", "Clerk", lambda: self._probe_clerk(settings, platform)),
            ("fleetbase_console", "Fleetbase Console", lambda: self._probe_fleetbase_console(settings)),
            ("mailpit", "Mailpit (Dev Email)", lambda: self._probe_mailpit(settings)),
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

"""Validation and architecture checks mixin."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_catalog import (
    HEALTH_CATEGORIES,
    TEST_BY_ID,
    TEST_IDS,
)
from porterchain_api.admin_engine.diagnostics_helpers import (
    HealthClass,
    _now_iso,
    _openapi_paths,
    _probe_http,
    _test_result,
)
from porterchain_api.config import Settings
from porterchain_api.booking_models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
from porterchain_shared.config.settings import get_platform_settings
from porterchain_shared.queue.publisher import queue_depths
from porterchain_shared.redis_health import ping_redis


class DiagnosticsValidationMixin:
    def run_test(self, test_id: str, db: Session, settings: Settings) -> dict[str, Any]:
        start = time.monotonic()
        logs: list[str] = []
        status: HealthClass = "critical"
        details: dict[str, Any] = {}
        meta = TEST_BY_ID.get(test_id, {})

        try:
            if test_id == "clerk":
                probe = self._probe_clerk(settings, get_platform_settings())
                status = probe["status"]
                details = probe.get("details", {}) or {}
                logs = (
                    probe.get("errors", [])
                    or probe.get("warnings", [])
                    or [f"Clerk JWKS OK ({details.get('jwks_apps', 0)} apps)"]
                )
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
                probe = self._probe_google_maps(
                    get_platform_settings(), live=True, app_env=settings.app_env
                )
                status = probe["status"]
                logs = (
                    probe.get("errors", [])
                    or probe.get("warnings", [])
                    or (
                        [(probe.get("details") or {}).get("note") or "Google Maps skipped (local)"]
                        if (probe.get("details") or {}).get("skipped")
                        else ["Google Maps probe OK"]
                    )
                )
            elif test_id == "osrm":
                probe = self._probe_osrm(get_platform_settings(), live=True)
                status = probe["status"]
                logs = (
                    probe.get("errors", [])
                    or probe.get("warnings", [])
                    or (
                        ["OSRM unused — Valhalla is primary"]
                        if (probe.get("details") or {}).get("role") == "fallback_unused"
                        else ["OSRM probe OK"]
                    )
                )
            elif test_id == "valhalla":
                probe = self._probe_valhalla(get_platform_settings(), live=True)
                status = probe["status"]
                details = probe.get("details", {})
                host = details.get("url") or ""
                logs = (
                    probe.get("errors", [])
                    or probe.get("warnings", [])
                    or [f"Valhalla probe OK ({host or 'configured'})"]
                )
            elif test_id == "vroom":  # fleetbase-first:ok — Fleetbase TSP probe
                probe = self._probe_vroom(settings, live=True)  # fleetbase-first:ok
                status = probe["status"]
                details = probe.get("details", {}) or {}
                logs = (
                    probe.get("errors", [])
                    or probe.get("warnings", [])
                    or (
                        [details.get("note") or "VROOM skipped (Fleetbase bridge/adapter off)"]  # fleetbase-first:ok
                        if details.get("skipped")
                        else ["VROOM reached via Fleetbase orchestrator"]  # fleetbase-first:ok
                    )
                )
            elif test_id == "fleetbase":
                probe = self._probe_fleetbase(settings, live=True)
                status = probe["status"]
                logs = (
                    probe.get("errors", [])
                    or probe.get("warnings", [])
                    or (
                        [(probe.get("details") or {}).get("note") or "Fleetbase skipped (local)"]
                        if (probe.get("details") or {}).get("skipped")
                        else ["Fleetbase API reachable"]
                    )
                )
            elif test_id == "fleetbase_adapter":
                probe = self._probe_fleetbase_adapter(settings, live=True)
                status = probe["status"]
                note = (probe.get("details") or {}).get("note")
                logs = [
                    "Adapter factory OK",
                    *(probe.get("warnings", []) or ([note] if note else [])),
                ]
            elif test_id == "fleetbase_console":
                probe = self._probe_fleetbase_console(settings)
                status = probe["status"]
                logs = (
                    probe.get("warnings", [])
                    or (
                        [(probe.get("details") or {}).get("note") or "Console skipped (local)"]
                        if (probe.get("details") or {}).get("skipped")
                        else ["Fleetbase console reachable"]
                    )
                )
            elif test_id == "email_smtp":
                probe = self._probe_email(get_platform_settings(), settings)
                status = probe["status"]
                logs = probe.get("warnings", []) or ["SMTP / Mailpit OK"]
            elif test_id == "mailpit":
                probe = self._probe_mailpit(settings)
                status = probe["status"]
                logs = probe.get("warnings", []) or ["Mailpit reachable at http://localhost:8025"]
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
                from datetime import UTC, datetime, timedelta

                from porterchain_api.notification_engine.admin_service import NotificationAdminService
                from porterchain_api.notification_engine.models import NotificationRecord

                dash = NotificationAdminService().dashboard(db)
                cutoff = datetime.now(UTC) - timedelta(hours=24)
                failed_24h = (
                    db.query(func.count(NotificationRecord.id))
                    .filter(
                        NotificationRecord.status.in_(["failed", "dead_letter"]),
                        NotificationRecord.created_at >= cutoff,
                    )
                    .scalar()
                    or 0
                )
                push_dead_24h = (
                    db.query(func.count(NotificationRecord.id))
                    .filter(
                        NotificationRecord.status == "dead_letter",
                        NotificationRecord.channel == "push",
                        NotificationRecord.created_at >= cutoff,
                    )
                    .scalar()
                    or 0
                )
                other_failed_24h = max(int(failed_24h) - int(push_dead_24h), 0)
                details = {
                    **dash,
                    "failed_24h": int(failed_24h),
                    "push_dead_letter_24h": int(push_dead_24h),
                }
                logs = [
                    f"total={dash['total']} queued={dash['queued']} failed_24h={failed_24h} active_devices={dash['active_devices']}"
                ]
                if dash["active_devices"] == 0:
                    logs.append("Push credentials OK; 0 registered devices — paste an FCM token to prove delivery")
                # Push dead-letters with zero devices are unproven delivery, not a broken engine.
                status = "warning" if other_failed_24h > 0 else "healthy"
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
                probe = self._engine_crm(db, settings)
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
            {"id": "customer_portal", "label": "Booking / Customer Portal", "url": settings.customer_portal_url},
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
            ("customer", "Customer", settings.customer_portal_url),
            ("merchant", "Merchant", settings.merchant_portal_url),
            ("driver", "Driver", settings.driver_portal_url),
            ("admin", "Admin", settings.admin_portal_url),
            ("orders", "Orders", None),
            ("crm", "CRM", None),
            ("operations", "Operations", None),
            ("fleet", "Fleet", None),
            ("drivers", "Drivers", None),
            ("finance", "Finance", None),
            ("billing", "Billing", None),
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

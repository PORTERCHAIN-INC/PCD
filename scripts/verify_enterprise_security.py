#!/usr/bin/env python3
"""§11.1 enterprise security — dev-layer guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "privacy service": ROOT / "apps/api/src/porterchain_api/compliance_engine/privacy_service.py",
    "merchant privacy router": ROOT / "apps/api/src/porterchain_api/routers/merchant/privacy.py",
    "customers router": ROOT / "apps/api/src/porterchain_api/routers/customers.py",
    "webhooks router": ROOT / "apps/api/src/porterchain_api/routers/webhooks.py",
    "rate limit middleware": ROOT / "apps/api/src/porterchain_api/platform/rate_limit_middleware.py",
    "config": ROOT / "apps/api/src/porterchain_api/config.py",
    "domain event model": ROOT / "apps/api/src/porterchain_api/booking_models.py",
    "audit export": ROOT / "apps/api/src/porterchain_api/admin_engine/audit_export_service.py",
    "soc2 doc": ROOT / "docs/compliance/SOC2.md",
    "pipeda doc": ROOT / "docs/compliance/PIPEDA.md",
    "status page doc": ROOT / "docs/STATUS_PAGE.md",
    "security md": ROOT / "SECURITY.md",
    "test file": ROOT / "apps/api/tests/test_enterprise_security.py",
    "pen test doc": ROOT / "docs/compliance/PEN_TEST.md",
    "adr secrets": ROOT / "docs/architecture/ADR-013-secrets.md",
    "secrets md": ROOT / "infrastructure/deploy/SECRETS.md",
    "sync secrets": ROOT / "infrastructure/deploy/sync-secrets.sh",
    "deploy workflow": ROOT / ".github/workflows/deploy.yml",
    "prod compose": ROOT / "infrastructure/deploy/docker-compose.prod.yml",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if path.suffix == ".md" and not path.is_file():
            continue
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    privacy = PATHS["privacy service"].read_text(encoding="utf-8")
    for fn in ("export_merchant", "request_merchant_deletion", "export_customer", "request_customer_deletion"):
        if fn not in privacy:
            failures.append(f"privacy service missing {fn}")

    merchant_priv = PATHS["merchant privacy router"].read_text(encoding="utf-8")
    if "/privacy/export" not in merchant_priv or "/privacy/delete-request" not in merchant_priv:
        failures.append("merchant privacy router incomplete")

    customers = PATHS["customers router"].read_text(encoding="utf-8")
    if "/me/privacy/export" not in customers:
        failures.append("customers router missing privacy export")

    webhooks = PATHS["webhooks router"].read_text(encoding="utf-8")
    if "construct_webhook_event" not in webhooks:
        failures.append("webhooks missing Stripe signature verify")
    if "fleetbase_webhook" in webhooks:
        failures.append("webhooks still expose retired Fleetbase ingress")

    rate = PATHS["rate limit middleware"].read_text(encoding="utf-8")
    if "PortalRateLimitMiddleware" not in rate or "rate_limit_unavailable" not in rate:
        failures.append("rate limit middleware incomplete")

    config = PATHS["config"].read_text(encoding="utf-8")
    if "reject_dev_jwt_secret_in_production" not in config:
        failures.append("config missing jwt_secret prod guard")

    models = PATHS["domain event model"].read_text(encoding="utf-8")
    if "class DomainEvent" not in models:
        failures.append("DomainEvent model missing")

    audit = PATHS["audit export"].read_text(encoding="utf-8")
    if "domain_events" not in audit:
        failures.append("audit export missing domain_events")

    main_py = (ROOT / "apps/api/src/porterchain_api/main.py").read_text(encoding="utf-8")
    if "/health/status" not in main_py:
        failures.append("main.py missing /health/status")

    reports = (ROOT / "apps/api/src/porterchain_api/merchant_engine/reports_service.py").read_text(
        encoding="utf-8"
    )
    if 'report_type == "sla-history"' not in reports:
        failures.append("reports missing sla-history CSV export")

    catalog = (ROOT / "shared/python/porterchain_shared/events/catalog.py").read_text(encoding="utf-8")
    if "PRIVACY_DELETE_REQUESTED" not in catalog:
        failures.append("event catalog missing PRIVACY_DELETE_REQUESTED")

    deploy = PATHS["deploy workflow"].read_text(encoding="utf-8")
    if "DOPPLER_TOKEN" not in deploy or "sync-secrets.sh" not in deploy:
        failures.append("deploy.yml missing Doppler sync-secrets path (§11.1.14)")
    if 'echo "::error::DOPPLER_TOKEN is required' not in deploy:
        failures.append("deploy.yml must fail when DOPPLER_TOKEN missing")

    compose = PATHS["prod compose"].read_text(encoding="utf-8")
    if "JWT_SECRET: ${JWT_SECRET}" not in compose:
        failures.append("prod compose must reference JWT_SECRET from env, not hardcoded")

    pen_doc = PATHS["pen test doc"]
    if pen_doc.is_file():
        pen = pen_doc.read_text(encoding="utf-8")
        if "annual" not in pen.lower() or "penetration" not in pen.lower():
            failures.append("PEN_TEST.md incomplete")

    print("Enterprise security guard (§11.1 · §11.3.5)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — privacy APIs, webhook sig, rate limits, audit trail, status page")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Verify D2 surface contracts — customer + driver API alignment."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# D2 deletions — must stay absent (Appendix D2 accidental complexity).
FORBIDDEN_PATHS: tuple[Path, ...] = (
    ROOT / "apps/admin/src/app/(ops)/crm",
    ROOT / "apps/admin/src/app/(ops)/routes",
    ROOT / "apps/admin/src/app/(ops)/reports",
    ROOT / "apps/admin/src/components/routes",
    ROOT / "website/src/app/[locale]/portal/customer",
    ROOT / "apps/merchant",
    ROOT / "apps/driver",
    ROOT / "apps/api/src/porterchain_api/reporting_engine",
)

CRM_CLIENT = ROOT / "apps/admin/src/lib/crm.ts"

CUSTOMER_WEB = ROOT / "apps/customer/src/lib/api.ts"
DRIVER_WEB_PROXY = ROOT / "apps/driver-portal/src/app/api/driver/[...path]/route.ts"
DRIVER_WEB_API = ROOT / "apps/driver-portal/src/lib/api.ts"


def _customer_paths(path: Path) -> set[str]:
    text = path.read_text()
    paths = set(re.findall(r"/v1/customers/me/[a-z/_${}]+", text))
    paths |= {m.replace("${v1}", "/v1") for m in re.findall(r"\$\{v1\}/customers/me/[a-z/_${}-]+", text)}
    return paths



def _check_filesystem() -> list[str]:
    failures: list[str] = []
    for path in FORBIDDEN_PATHS:
        if path.exists():
            failures.append(f"forbidden path present: {path.relative_to(ROOT)}")
    if CRM_CLIENT.exists():
        text = CRM_CLIENT.read_text()
        if 'const B = "/v1/admin/crm"' in text or "export const crm" in text:
            failures.append("crm.ts still contains dead /v1/admin/crm client")
    return failures


def _check_engine_imports() -> list[str]:
    """§0.3.10 — merchant (and other engines) must not import admin_engine."""
    failures: list[str] = []
    api_src = ROOT / "apps/api/src/porterchain_api"
    forbidden = (
        ("merchant_engine", "admin_engine"),
        ("driver_engine", "admin_engine"),
        ("booking_engine", "admin_engine"),
    )
    for engine, upstream in forbidden:
        engine_dir = api_src / engine
        if not engine_dir.is_dir():
            continue
        for py in engine_dir.rglob("*.py"):
            text = py.read_text()
            if re.search(rf"from porterchain_api\.{upstream}|import porterchain_api\.{upstream}", text):
                failures.append(f"{engine} imports {upstream}: {py.relative_to(ROOT)}")
    return failures


_ENGINE_IMPORT_RE = re.compile(r"from porterchain_api\.([a-z_]+_engine)(?:\.|\s+import)")

# §3.2.9 — known cross-engine imports (shrink over time; no new coupling).
_LEGACY_CROSS_ENGINE_IMPORTS: frozenset[str] = frozenset(
    {
        "admin_engine->billing_engine:admin_engine/finance_service.py",
        "admin_engine->billing_engine:admin_engine/merchant_ar_service.py",
        "admin_engine->booking_engine:admin_engine/booking_draft_admin_service.py",
        "admin_engine->booking_engine:admin_engine/clerk_directory_service.py",
        "admin_engine->booking_engine:admin_engine/control_tower_service.py",
        "admin_engine->booking_engine:admin_engine/control_tower/exceptions.py",
        "admin_engine->booking_engine:admin_engine/control_tower/service.py",
        "admin_engine->booking_engine:admin_engine/control_tower/sla.py",
        "admin_engine->booking_engine:admin_engine/driver_service.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_forward.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_merchant.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_reverse.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_verifiers.py",
        "admin_engine->booking_engine:admin_engine/merchant_service.py",
        "admin_engine->booking_engine:admin_engine/notification_admin_service.py",
        "admin_engine->booking_engine:admin_engine/operations_service.py",
        "admin_engine->booking_engine:admin_engine/orders_service.py",
        "admin_engine->booking_engine:admin_engine/merchant_ar_service.py",
        "admin_engine->order_engine:admin_engine/business_metrics.py",
        "admin_engine->support_engine:admin_engine/business_metrics.py",
        "admin_engine->collaboration_engine:admin_engine/crm_sales_service.py",
        "admin_engine->fleetbase_engine:admin_engine/control_tower_service.py",
        "admin_engine->fleetbase_engine:admin_engine/control_tower/events.py",
        "admin_engine->fleetbase_engine:admin_engine/diagnostics_probes.py",
        "admin_engine->fleetbase_engine:admin_engine/diagnostics_workflows.py",
        "admin_engine->fleetbase_engine:admin_engine/driver_service.py",
        "admin_engine->fleetbase_engine:admin_engine/execution_metrics.py",
        "admin_engine->fleetbase_engine:admin_engine/operations_service.py",
        "admin_engine->fleetbase_engine:admin_engine/e2e_validation_consistency.py",
        "admin_engine->fleetbase_engine:admin_engine/e2e_validation_core.py",
        "admin_engine->merchant_engine:admin_engine/e2e_validation_merchant.py",
        "admin_engine->merchant_engine:admin_engine/merchant_ar_service.py",
        "admin_engine->merchant_engine:admin_engine/e2e_validation_verifiers.py",
        "admin_engine->merchant_engine:admin_engine/platform_user_authorize.py",
        "admin_engine->merchant_engine:admin_engine/diagnostics_workflows.py",
        "admin_engine->merchant_engine:admin_engine/execution_metrics.py",
        "admin_engine->notification_engine:admin_engine/diagnostics_probes.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_consistency.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_failures.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_forward.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_notifications.py",
        "admin_engine->notification_engine:admin_engine/notification_admin_service.py",
        "admin_engine->order_engine:admin_engine/control_tower_service.py",
        "admin_engine->order_engine:admin_engine/control_tower/_helpers.py",
        "admin_engine->order_engine:admin_engine/control_tower/assignment.py",
        "admin_engine->order_engine:admin_engine/control_tower/events.py",
        "admin_engine->order_engine:admin_engine/control_tower/service.py",
        "admin_engine->order_engine:admin_engine/control_tower/sla.py",
        "admin_engine->order_engine:admin_engine/dispatch_suggestions_service.py",
        "admin_engine->order_engine:admin_engine/live_map_service.py",
        "admin_engine->order_engine:admin_engine/operations_service.py",
        "admin_engine->order_engine:admin_engine/orders_service.py",
        "admin_engine->pricing_engine:admin_engine/diagnostics_probes.py",
        "admin_engine->pricing_engine:admin_engine/diagnostics_validation.py",
        "admin_engine->support_engine:admin_engine/claims_service.py",
        "admin_engine->support_engine:admin_engine/support_service.py",
        "booking_engine->fleetbase_engine:booking_engine/fleetbase_sync_handler.py",
        "booking_engine->fleetbase_engine:booking_engine/tracking_service.py",
        "booking_engine->fleetbase_engine:booking_engine/public_tracking_snapshot.py",
        "booking_engine->notification_engine:booking_engine/notification_handler.py",
        "booking_engine->notification_engine:booking_engine/medical_compliance.py",
        "booking_engine->notification_engine:booking_engine/notification_service.py",
        "booking_engine->pricing_engine:booking_engine/quote_service.py",
        "booking_engine->order_engine:booking_engine/public_tracking_snapshot.py",
        "booking_engine->collaboration_engine:booking_engine/crm_lead_mirror.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_activity.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_companies.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_contacts.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_contracts.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_dashboard.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_deals.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_helpers.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_import.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_leads.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_quotations.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_reports.py",
        "collaboration_engine->admin_engine:collaboration_engine/crm_tasks.py",
        "compliance_engine->booking_engine:compliance_engine/privacy_service.py",
        "fleetbase_engine->booking_engine:fleetbase_engine/booking_sync_service.py",
        "fleetbase_engine->booking_engine:fleetbase_engine/integration_bridge.py",
        "fleetbase_engine->booking_engine:fleetbase_engine/webhook_ingress_service.py",
        "fleetbase_engine->booking_engine:fleetbase_engine/webhook_processor.py",
        "gateway_engine->merchant_engine:gateway_engine/middleware.py",
        "merchant_engine->billing_engine:merchant_engine/billing_service.py",
        "merchant_engine->booking_engine:merchant_engine/api_key_service.py",
        "merchant_engine->booking_engine:merchant_engine/booking_flow_service.py",
        "merchant_engine->booking_engine:merchant_engine/booking_service.py",
        "merchant_engine->booking_engine:merchant_engine/bulk_service.py",
        "merchant_engine->booking_engine:merchant_engine/orders_service.py",
        "merchant_engine->booking_engine:merchant_engine/support_bridge_service.py",
        "merchant_engine->booking_engine:merchant_engine/tracking_service.py",
        "merchant_engine->fleetbase_engine:merchant_engine/booking_flow_service.py",
        "merchant_engine->fleetbase_engine:merchant_engine/booking_service.py",
        "merchant_engine->fleetbase_engine:merchant_engine/tracking_service.py",
        "merchant_engine->gateway_engine:merchant_engine/integrations_service.py",
        "merchant_engine->oauth_engine:merchant_engine/integrations_service.py",
        "merchant_engine->notification_engine:merchant_engine/dashboard_service.py",
        "merchant_engine->notification_engine:merchant_engine/tracking_service.py",
        "merchant_engine->order_engine:merchant_engine/orders_service.py",
        "merchant_engine->order_engine:merchant_engine/reporting_metrics.py",
        "merchant_engine->order_engine:merchant_engine/tracking_service.py",
        "merchant_engine->pricing_engine:merchant_engine/booking_flow_service.py",
        "merchant_engine->pricing_engine:merchant_engine/booking_service.py",
        "merchant_engine->collaboration_engine:merchant_engine/contacts_service.py",
        "merchant_engine->support_engine:merchant_engine/support_bridge_service.py",
        "notification_engine->booking_engine:notification_engine/delivery_service.py",
        "notification_engine->booking_engine:notification_engine/engine.py",
        "order_engine->admin_engine:order_engine/platform_service.py",
        "order_engine->billing_engine:order_engine/platform_detail.py",
        "order_engine->booking_engine:order_engine/buckets.py",
        "order_engine->booking_engine:order_engine/platform_service.py",
        "support_engine->admin_engine:support_engine/claims_mutations.py",
        "support_engine->admin_engine:support_engine/claims_smart.py",
        "support_engine->admin_engine:support_engine/support_context.py",
        "support_engine->admin_engine:support_engine/support_kb.py",
        "support_engine->admin_engine:support_engine/support_ticket_actions.py",
        "support_engine->admin_engine:support_engine/support_tickets.py",
        "support_engine->booking_engine:support_engine/claims_helpers.py",
        "support_engine->booking_engine:support_engine/claims_mutations.py",
        "support_engine->booking_engine:support_engine/support_ticket_actions.py",
        "support_engine->booking_engine:support_engine/support_tickets.py",
    }
)


def _check_cross_engine_imports() -> list[str]:
    """§3.2.9 — freeze cross-engine coupling; no new *_engine → other *_engine imports."""
    failures: list[str] = []
    api_src = ROOT / "apps/api/src/porterchain_api"
    seen: set[str] = set()
    for engine_dir in sorted(api_src.glob("*_engine")):
        if not engine_dir.is_dir():
            continue
        source = engine_dir.name
        for py in sorted(engine_dir.rglob("*.py")):
            rel = py.relative_to(api_src)
            text = py.read_text()
            for match in _ENGINE_IMPORT_RE.finditer(text):
                target = match.group(1)
                if target == source:
                    continue
                key = f"{source}->{target}:{rel}"
                if key in seen:
                    continue
                seen.add(key)
                if key not in _LEGACY_CROSS_ENGINE_IMPORTS:
                    failures.append(f"§3.2.9 new cross-engine import: {key}")
    return failures


def _check_service_modularity() -> list[str]:
    """§0.3.6 — no new 1000+ LOC *_service.py modules."""
    failures: list[str] = []
    api_src = ROOT / "apps/api/src/porterchain_api"
    for path in api_src.rglob("*_service.py"):
        lines = len(path.read_text().splitlines())
        if lines > 1000:
            failures.append(f"service >1000 LOC ({lines}): {path.relative_to(ROOT)}")
    return failures


def _check_router_raw_sql() -> list[str]:
    """§2.2.11 / DD-21 — routers must not execute raw SQL."""
    failures: list[str] = []
    routers = ROOT / "apps/api/src/porterchain_api/routers"
    patterns = (
        r"\.execute\s*\(",
        r"from sqlalchemy import text",
        r"from sqlalchemy\.sql import text",
    )
    for py in routers.rglob("*.py"):
        text = py.read_text()
        for pat in patterns:
            if re.search(pat, text):
                failures.append(f"raw SQL in router: {py.relative_to(ROOT)} ({pat})")
                break
    return failures


def _check_router_star_imports() -> list[str]:
    """§2.2.5 / DD-22 — router modules must not star-import from _deps."""
    failures: list[str] = []
    routers = ROOT / "apps/api/src/porterchain_api/routers"
    for py in routers.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        text = py.read_text()
        if "from porterchain_api.routers" in text and "import *" in text:
            failures.append(f"star import in router module: {py.relative_to(ROOT)}")
    return failures


# §0.3.3 — routers with known ORM/UoW debt (shrink over time; no new files).
_LEGACY_ROUTER_LOGIC: frozenset[str] = frozenset(
    {
        "auth.py",
        "admin/booking_drafts.py",
        "admin/claims.py",
        "oauth.py",
        "merchants.py",
    }
)

# §0.3.9 — route modules above 350 LOC (legacy); per-file caps shrink over time.
_LEGACY_ROUTER_LOC: dict[str, int] = {
    "admin/settings.py": 400,
    "merchant/integrations.py": 420,
    "merchants.py": 430,
}

MAX_NEW_ROUTER_LOC = 350
MAX_ENGINE_SERVICE_LOC = 500

# ENG-G2 — legacy services above 500 LOC (shrink over time; no new files may exceed 500).
_LEGACY_ENGINE_SERVICE_LOC: dict[str, int] = {
    "admin_engine/settings_service.py": 965,
    "booking_engine/booking_draft_service.py": 732,
    "admin_engine/merchant360_service.py": 670,
    "admin_engine/finance_service.py": 641,
    "admin_engine/booking_draft_admin_service.py": 544,
    "merchant_engine/tracking_service.py": 545,
    "admin_engine/driver360_service.py": 512,
}


def _router_scan_files() -> list[Path]:
    routers = ROOT / "apps/api/src/porterchain_api/routers"
    return [
        py
        for py in routers.rglob("*.py")
        if py.name not in ("__init__.py", "_deps.py")
    ]


def _rel_router(path: Path) -> str:
    base = ROOT / "apps/api/src/porterchain_api/routers"
    return str(path.relative_to(base))


def _check_router_business_logic() -> list[str]:
    """§0.3.3 — business logic stays in *_service.py; legacy routers allowlisted."""
    failures: list[str] = []
    patterns = (
        (r"\bdb\.query\s*\(", "db.query"),
        (r"\bdb\.commit\s*\(", "db.commit"),
        (r"\bdb\.(add|delete|merge|flush)\s*\(", "db mutation"),
        (
            r"from porterchain_api\.(models|merchant_models|admin_models|fleetbase_models)",
            "model import",
        ),
    )
    for py in _router_scan_files():
        rel = _rel_router(py)
        if rel in _LEGACY_ROUTER_LOGIC:
            continue
        text = py.read_text()
        for pat, label in patterns:
            if re.search(pat, text):
                failures.append(f"§0.3.3 {label} in router: {rel}")
                break
    return failures


def _check_router_thinness() -> list[str]:
    """§0.3.9 — new router modules stay thin (≤350 LOC)."""
    failures: list[str] = []
    for py in _router_scan_files():
        rel = _rel_router(py)
        lines = len(py.read_text().splitlines())
        limit = _LEGACY_ROUTER_LOC.get(rel, MAX_NEW_ROUTER_LOC)
        if lines > limit:
            failures.append(f"§0.3.9 router >{limit} LOC ({lines}): {rel}")
    return failures


def _check_service_loc() -> list[str]:
    """§2.2.1–2.2.4 — split modules must stay ≤400 LOC; facades thin."""
    failures: list[str] = []
    api_src = ROOT / "apps/api/src/porterchain_api"
    split_globs = (
        "collaboration_engine/crm_*.py",
        "admin_engine/diagnostics_*.py",
        "admin_engine/e2e_validation_*.py",
        "order_engine/platform_*.py",
        "support_engine/support_*.py",
        "support_engine/claims_*.py",
    )
    thin_facades = (
        api_src / "collaboration_engine/crm_service.py",
        api_src / "admin_engine/diagnostics_service.py",
        api_src / "admin_engine/e2e_validation_service.py",
        api_src / "order_engine/platform_service.py",
        api_src / "support_engine/support_service.py",
        api_src / "support_engine/claims_service.py",
    )
    for pattern in split_globs:
        for path in api_src.parent.glob(f"porterchain_api/{pattern}"):
            if not path.is_file():
                continue
            lines = len(path.read_text().splitlines())
            if lines > 400:
                failures.append(f"split module >400 LOC ({lines}): {path.relative_to(ROOT)}")
    for path in thin_facades:
        if path.is_file():
            lines = len(path.read_text().splitlines())
            if lines > 120:
                failures.append(f"service facade >120 LOC ({lines}): {path.relative_to(ROOT)}")
    return failures


def _check_engine_service_loc() -> list[str]:
    """ENG-G2 / §2.2.9 — engine *_service.py modules stay ≤500 LOC (legacy shrink list)."""
    failures: list[str] = []
    api_src = ROOT / "apps/api/src/porterchain_api"
    for engine_dir in sorted(api_src.glob("*_engine")):
        if not engine_dir.is_dir():
            continue
        for path in sorted(engine_dir.glob("*_service.py")):
            rel = f"{engine_dir.name}/{path.name}"
            lines = len(path.read_text().splitlines())
            legacy_cap = _LEGACY_ENGINE_SERVICE_LOC.get(rel)
            if lines > MAX_ENGINE_SERVICE_LOC:
                if legacy_cap is None:
                    failures.append(
                        f"§ENG-G2 engine service >{MAX_ENGINE_SERVICE_LOC} LOC ({lines}): {rel}"
                    )
                elif lines > legacy_cap:
                    failures.append(
                        f"§ENG-G2 legacy service grew ({lines} > {legacy_cap}): {rel}"
                    )
    return failures


def main() -> int:
    failures: list[str] = _check_filesystem()
    failures.extend(_check_engine_imports())
    failures.extend(_check_cross_engine_imports())
    failures.extend(_check_router_star_imports())
    failures.extend(_check_router_raw_sql())
    failures.extend(_check_router_business_logic())
    failures.extend(_check_router_thinness())
    failures.extend(_check_service_loc())
    failures.extend(_check_service_modularity())
    failures.extend(_check_engine_service_loc())

    web_customer = _customer_paths(CUSTOMER_WEB)

    for required in ("/v1/customers/me/dashboard", "/v1/customers/me/support"):
        if required not in web_customer:
            failures.append(f"customer web missing {required}")

    driver_proxy = DRIVER_WEB_PROXY.read_text()
    if "/driver-api/v1" not in driver_proxy:
        failures.append("driver-portal proxy missing /driver-api/v1")

    driver_web = DRIVER_WEB_API.read_text()
    required_driver = (
        "/v1/dashboard",
        "/v1/jobs",
    )
    for required in required_driver:
        if required not in driver_web:
            failures.append(f"driver web missing {required}")

    print("D2 verification (filesystem + contracts)")
    if not failures:
        print(f"  filesystem: {len(FORBIDDEN_PATHS)} forbidden paths absent")
    print(f"  customer web: {sorted(web_customer)}")
    print(f"  driver web api: checked {len(required_driver)} paths")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  PASS: customer + driver surfaces share Porterchain API contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

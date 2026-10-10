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
DRIVER_MOBILE_API = ROOT / "apps/mobile-driver/src/api.ts"
DRIVER_JOB_SCHEMA = ROOT / "apps/api/src/porterchain_api/schemas_driver.py"
DRIVER_WEB_JOBS = ROOT / "apps/driver-portal/src/lib/jobs.ts"
DRIVER_MOBILE_TYPES = ROOT / "apps/mobile-driver/src/types.ts"


def _customer_paths(path: Path) -> set[str]:
    text = path.read_text()
    paths = set(re.findall(r"/v1/customers/me/[a-z/_${}]+", text))
    paths |= {m.replace("${v1}", "/v1") for m in re.findall(r"\$\{v1\}/customers/me/[a-z/_${}-]+", text)}
    return paths


def _pydantic_model_fields(text: str, class_name: str) -> set[str]:
    """Field names on a BaseModel (or subclass) block (stops at next top-level class)."""
    match = re.search(
        rf"^class {re.escape(class_name)}\([^)]+\):\n(.*?)(?=^class |\Z)",
        text,
        flags=re.M | re.S,
    )
    if not match:
        return set()
    return set(re.findall(r"^    ([a-zA-Z_][a-zA-Z0-9_]*)\s*:", match.group(1), flags=re.M))


def _ts_interface_fields(text: str, type_name: str) -> set[str]:
    """Field names on `export interface|type Name = {{ ... }}` (one level / intersection)."""
    patterns = (
        rf"export (?:interface|type) {re.escape(type_name)}\s*=\s*[A-Za-z_][\w.]*\s*&\s*\{{(.*?)\n\}}",
        rf"export (?:interface|type) {re.escape(type_name)}\s*(?:=\s*)?\{{(.*?)\n\}}",
    )
    for pat in patterns:
        match = re.search(pat, text, flags=re.S)
        if match:
            return set(re.findall(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*[?]?:", match.group(1), flags=re.M))
    return set()


def _check_driver_job_summary_parity() -> list[str]:
    """Client DriverJobSummary fields must be a subset of the API schema (no silent drift)."""
    failures: list[str] = []
    api_fields = _pydantic_model_fields(DRIVER_JOB_SCHEMA.read_text(), "DriverJobSummary")
    if not api_fields:
        return ["DriverJobSummary missing from schemas_driver.py"]
    web_fields = _ts_interface_fields(DRIVER_WEB_JOBS.read_text(), "DriverJobSummary")
    mobile_fields = _ts_interface_fields(DRIVER_MOBILE_TYPES.read_text(), "DriverJobSummary")
    if not web_fields:
        failures.append("driver-portal DriverJobSummary type missing")
    if not mobile_fields:
        failures.append("mobile-driver DriverJobSummary type missing")
    for label, fields in (("web", web_fields), ("mobile", mobile_fields)):
        unknown = sorted(fields - api_fields)
        if unknown:
            failures.append(f"DriverJobSummary {label} fields not on API: {', '.join(unknown)}")
    # Web is the full desk mirror — require the API required-ish core set.
    core = {
        "order_id",
        "order_number",
        "tracking_number",
        "state",
        "status",
        "bucket",
        "pickup_address",
        "delivery_address",
    }
    missing_web = sorted(core - web_fields)
    if missing_web:
        failures.append(f"driver-portal DriverJobSummary missing core fields: {', '.join(missing_web)}")
    missing_mobile = sorted({"order_id", "order_number", "tracking_number"} - mobile_fields)
    if missing_mobile:
        failures.append(f"mobile-driver DriverJobSummary missing core fields: {', '.join(missing_mobile)}")

    # Detail + offline request shapes — clients may be subsets, but must not invent fields.
    detail_api = _pydantic_model_fields(DRIVER_JOB_SCHEMA.read_text(), "DriverJobDetailResponse")
    detail_mobile = _ts_interface_fields(DRIVER_MOBILE_TYPES.read_text(), "DriverJobDetail")
    # DriverJobDetail is an intersection type on mobile — also accept type alias fields via Summary.
    if detail_mobile:
        unknown_detail = sorted(detail_mobile - detail_api - api_fields)
        if unknown_detail:
            failures.append(
                f"DriverJobDetail mobile fields not on API: {', '.join(unknown_detail)}"
            )
    for required in ("otp_required", "scan_pickup", "scan_delivery"):
        if required not in detail_api:
            failures.append(f"DriverJobDetailResponse missing {required}")

    offline_api = _pydantic_model_fields(DRIVER_JOB_SCHEMA.read_text(), "OfflineActionRequest")
    if not offline_api:
        failures.append("OfflineActionRequest missing from schemas_driver.py")
    elif "action_type" not in offline_api:
        failures.append("OfflineActionRequest missing action_type")
    mobile_types = DRIVER_MOBILE_TYPES.read_text()
    if "OfflineStatus" not in mobile_types:
        failures.append("mobile-driver missing OfflineStatus type")
    if "OfflineSyncResult" not in mobile_types:
        failures.append("mobile-driver missing OfflineSyncResult type")
    return failures




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



# §0.3.10 — legacy upward imports into admin_engine (shrink; no new files).
_LEGACY_UPWARD_ADMIN_IMPORTS: frozenset[str] = frozenset(
    {
        "booking_engine/confirmation_service.py",
        "booking_engine/invoice_service.py",
        "booking_engine/quote_service.py",
        "driver_engine/abstract_service.py",
        "driver_engine/background_check_service.py",
        "driver_engine/compliance_expiry_service.py",
        "driver_engine/verification_service.py",
    }
)


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
            rel = f"{engine}/{py.relative_to(engine_dir)}"
            body = py.read_text()
            if re.search(rf"from porterchain_api\.{upstream}|import porterchain_api\.{upstream}", body):
                if rel in _LEGACY_UPWARD_ADMIN_IMPORTS:
                    continue
                failures.append(f"{engine} imports {upstream}: {py.relative_to(ROOT)}")
    return failures


_ENGINE_IMPORT_RE = re.compile(r"from porterchain_api\.([a-z_]+_engine)(?:\.|\s+import)")

# §3.2.9 — known cross-engine imports (shrink over time; no new coupling).
_LEGACY_CROSS_ENGINE_IMPORTS: frozenset[str] = frozenset(
    {
        "admin_engine->billing_engine:admin_engine/driver360_service.py",
        "admin_engine->billing_engine:admin_engine/finance_service.py",
        "admin_engine->billing_engine:admin_engine/finance_refund.py",
        "admin_engine->billing_engine:admin_engine/merchant360_service.py",
        "admin_engine->billing_engine:admin_engine/merchant_ar_service.py",
        "admin_engine->billing_engine:admin_engine/merchant_service.py",
        "admin_engine->booking_engine:admin_engine/booking_draft_admin_service.py",
        "admin_engine->booking_engine:admin_engine/customer_booking_admin_service.py",
        "admin_engine->booking_engine:admin_engine/control_tower/events.py",
        "admin_engine->booking_engine:admin_engine/control_tower/exceptions.py",
        "admin_engine->booking_engine:admin_engine/control_tower/scoring.py",
        "admin_engine->booking_engine:admin_engine/control_tower/service.py",
        "admin_engine->booking_engine:admin_engine/control_tower/sla.py",
        "admin_engine->booking_engine:admin_engine/dispatcher_copilot_service.py",
        "admin_engine->booking_engine:admin_engine/driver_service.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_forward.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_merchant.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_reverse.py",
        "admin_engine->booking_engine:admin_engine/e2e_validation_verifiers.py",
        "admin_engine->booking_engine:admin_engine/merchant_ar_service.py",
        "admin_engine->booking_engine:admin_engine/merchant_service.py",
        "admin_engine->booking_engine:admin_engine/operations_service.py",
        "admin_engine->booking_engine:admin_engine/order_assist_service.py",
        "admin_engine->booking_engine:admin_engine/order_builder_service.py",
        "admin_engine->booking_engine:admin_engine/orders_service.py",
        "admin_engine->booking_engine:admin_engine/settings_service.py",
        "admin_engine->booking_engine:admin_engine/shopify_control_service.py",
        "admin_engine->collaboration_engine:admin_engine/crm_sales_service.py",
        "admin_engine->merchant_engine:admin_engine/clerk_directory_service.py",
        "admin_engine->merchant_engine:admin_engine/control_tower/exceptions.py",
        "admin_engine->merchant_engine:admin_engine/diagnostics_workflows.py",
        "admin_engine->merchant_engine:admin_engine/e2e_validation_merchant.py",
        "admin_engine->merchant_engine:admin_engine/e2e_validation_verifiers.py",
        "admin_engine->merchant_engine:admin_engine/execution_metrics.py",
        "admin_engine->merchant_engine:admin_engine/impersonation_service.py",
        "admin_engine->merchant_engine:admin_engine/merchant_ar_service.py",
        "admin_engine->merchant_engine:admin_engine/merchant_service.py",
        "admin_engine->merchant_engine:admin_engine/platform_user_authorize.py",
        "admin_engine->merchant_engine:admin_engine/shopify_control_service.py",
        "admin_engine->notification_engine:admin_engine/diagnostics_probes.py",
        "admin_engine->notification_engine:admin_engine/diagnostics_validation.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_consistency.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_failures.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_forward.py",
        "admin_engine->notification_engine:admin_engine/e2e_validation_notifications.py",
        "admin_engine->notification_engine:admin_engine/order_assist_service.py",
        "admin_engine->order_engine:admin_engine/business_metrics.py",
        "admin_engine->order_engine:admin_engine/control_tower/_helpers.py",
        "admin_engine->order_engine:admin_engine/control_tower/assignment.py",
        "admin_engine->order_engine:admin_engine/control_tower/events.py",
        "admin_engine->order_engine:admin_engine/control_tower/scoring.py",
        "admin_engine->order_engine:admin_engine/control_tower/service.py",
        "admin_engine->order_engine:admin_engine/control_tower/sla.py",
        "admin_engine->order_engine:admin_engine/dispatcher_copilot_service.py",
        "admin_engine->order_engine:admin_engine/live_map_service.py",
        "admin_engine->order_engine:admin_engine/operations_service.py",
        "admin_engine->order_engine:admin_engine/orders_service.py",
        "admin_engine->order_engine:admin_engine/utilization_service.py",
        "admin_engine->pricing_engine:admin_engine/diagnostics_probes.py",
        "admin_engine->pricing_engine:admin_engine/diagnostics_validation.py",
        "admin_engine->pricing_engine:admin_engine/order_builder_service.py",
        "admin_engine->support_engine:admin_engine/business_metrics.py",
        "admin_engine->support_engine:admin_engine/claims_service.py",
        "admin_engine->support_engine:admin_engine/driver360_service.py",
        "admin_engine->support_engine:admin_engine/support_service.py",
        "booking_engine->collaboration_engine:booking_engine/crm_lead_mirror.py",
        "booking_engine->notification_engine:booking_engine/invoice_service.py",
        "booking_engine->order_engine:booking_engine/public_tracking_snapshot.py",
        "booking_engine->pricing_engine:booking_engine/quote_service.py",
        "collaboration_engine->merchant_engine:collaboration_engine/crm_contracts.py",
        "compliance_engine->booking_engine:compliance_engine/privacy_service.py",
        "compliance_engine->notification_engine:compliance_engine/privacy_service.py",
        "gateway_engine->merchant_engine:gateway_engine/middleware.py",
        "merchant_engine->billing_engine:merchant_engine/billing_service.py",
        "merchant_engine->billing_engine:merchant_engine/billing_views.py",
        "merchant_engine->billing_engine:merchant_engine/offboard.py",
        "merchant_engine->booking_engine:merchant_engine/api_key_service.py",
        "merchant_engine->booking_engine:merchant_engine/booking_flow_service.py",
        "merchant_engine->booking_engine:merchant_engine/booking_service.py",
        "merchant_engine->booking_engine:merchant_engine/bulk_service.py",
        "merchant_engine->booking_engine:merchant_engine/orders_service.py",
        "merchant_engine->booking_engine:merchant_engine/support_bridge_service.py",
        "merchant_engine->booking_engine:merchant_engine/tracking_service.py",
        "merchant_engine->collaboration_engine:merchant_engine/contacts_service.py",
        "merchant_engine->gateway_engine:merchant_engine/integrations_service.py",
        "merchant_engine->notification_engine:merchant_engine/consignee_notify.py",
        "merchant_engine->notification_engine:merchant_engine/dashboard_service.py",
        "merchant_engine->notification_engine:merchant_engine/settings_service.py",
        "merchant_engine->notification_engine:merchant_engine/tracking_service.py",
        "merchant_engine->oauth_engine:merchant_engine/integrations_service.py",
        "merchant_engine->order_engine:merchant_engine/offboard.py",
        "merchant_engine->order_engine:merchant_engine/orders_service.py",
        "merchant_engine->order_engine:merchant_engine/reporting_metrics.py",
        "merchant_engine->order_engine:merchant_engine/tracking_service.py",
        "merchant_engine->pricing_engine:merchant_engine/booking_flow_service.py",
        "merchant_engine->pricing_engine:merchant_engine/booking_service.py",
        "merchant_engine->pricing_engine:merchant_engine/import_quote.py",
        "merchant_engine->support_engine:merchant_engine/support_bridge_service.py",
        "notification_engine->admin_engine:notification_engine/staff_fanout.py",
        "notification_engine->booking_engine:notification_engine/delivery_service.py",
        "notification_engine->booking_engine:notification_engine/engine.py",
        "notification_engine->booking_engine:notification_engine/retry_sweeper.py",
        "order_engine->admin_engine:order_engine/platform_service.py",
        "order_engine->billing_engine:order_engine/platform_detail.py",
        "order_engine->booking_engine:order_engine/buckets.py",
        "order_engine->booking_engine:order_engine/platform_detail.py",
        "order_engine->booking_engine:order_engine/platform_service.py",
        "order_engine->notification_engine:order_engine/platform_detail.py",
        "support_engine->booking_engine:support_engine/claims_helpers.py",
        "support_engine->booking_engine:support_engine/claims_mutations.py",
        "support_engine->booking_engine:support_engine/support_ticket_actions.py",
        "support_engine->booking_engine:support_engine/support_tickets.py",
        # arch-refactor-baseline freeze (in-progress coupling; shrink later)
        "admin_engine->dispatch_engine:admin_engine/control_tower/assignment.py",
        # Dispatch Phase 1: admin orchestration over the dispatch domain (same pattern as above).
        "admin_engine->dispatch_engine:admin_engine/dispatch_board_service.py",
        "admin_engine->dispatch_engine:admin_engine/job_offers_service.py",
        "admin_engine->dispatch_engine:admin_engine/fleet_capacity_service.py",
        "admin_engine->dispatch_engine:admin_engine/diagnostics_probes.py",  # read-only worker liveness probe (stale job offers)
        # Driver stop check-ins: order transitions via booking API, POD files + live position via driver_engine.
        "dispatch_engine->booking_engine:dispatch_engine/driver_route.py",
        "dispatch_engine->driver_engine:dispatch_engine/driver_route.py",
        # Dispatch Phase 2: fleet plans, partners/legs, retention (admin orchestration).
        "admin_engine->dispatch_engine:admin_engine/fleet_plan_service.py",
        "admin_engine->dispatch_engine:admin_engine/logistics_partners_service.py",
        "admin_engine->driver_engine:admin_engine/logistics_partners_service.py",
        "admin_engine->booking_engine:admin_engine/job_offers_service.py",
        # Integration (6 branches combined): dispatch probes + driver PIN reuse driver_engine.
        "admin_engine->dispatch_engine:admin_engine/diagnostics_probes.py",
        "dispatch_engine->driver_engine:dispatch_engine/driver_pin.py",
        # Dispatch Round 4: admin-approved exception fixes (re-plan, reschedule transition, order.delayed event).
        "admin_engine->dispatch_engine:admin_engine/exception_fixes_service.py",
        "admin_engine->booking_engine:admin_engine/exception_fixes_service.py",
        "admin_engine->dispatch_engine:admin_engine/control_tower/scoring.py",
        "admin_engine->dispatch_engine:admin_engine/live_map_service.py",
        "admin_engine->dispatch_engine:admin_engine/operations_service.py",
        "admin_engine->dispatch_engine:admin_engine/orchestrator_ops_service.py",
        "admin_engine->dispatch_engine:admin_engine/utilization_service.py",
        "booking_engine->dispatch_engine:booking_engine/public_tracking_snapshot.py",
        "booking_engine->dispatch_engine:booking_engine/tracking_normalize.py",
        "collaboration_engine->notification_engine:collaboration_engine/lead_ops.py",
        "collaboration_engine->notification_engine:collaboration_engine/lead_outbound_email.py",
        "dispatch_engine->driver_engine:dispatch_engine/driver_pin.py",
        "driver_engine->dispatch_engine:driver_engine/last_known.py",
        "merchant_engine->dispatch_engine:merchant_engine/route_import_service.py",
        "merchant_engine->dispatch_engine:merchant_engine/tracking_service.py",
        "notification_engine->merchant_engine:notification_engine/context.py",
        "notification_engine->merchant_engine:notification_engine/preference_service.py",
        "admin_engine->billing_engine:admin_engine/merchant_lifecycle.py",
        "admin_engine->booking_engine:admin_engine/merchant_lifecycle.py",
        "admin_engine->driver_engine:admin_engine/control_tower/scoring.py",
        "admin_engine->driver_engine:admin_engine/live_map_service.py",
        "admin_engine->merchant_engine:admin_engine/booking_draft_admin_service.py",
        "admin_engine->merchant_engine:admin_engine/finance_service.py",
        "admin_engine->merchant_engine:admin_engine/merchant360_service.py",
        "admin_engine->merchant_engine:admin_engine/merchant_lifecycle.py",
        "admin_engine->merchant_engine:admin_engine/merchant_org.py",
        "admin_engine->merchant_engine:admin_engine/orders_service.py",
        "admin_engine->notification_engine:admin_engine/diagnostics_validation.py",
        "billing_engine->booking_engine:billing_engine/settlement_service.py",
        "billing_engine->merchant_engine:billing_engine/stripe_cod_service.py",
        "booking_engine->billing_engine:booking_engine/stripe_webhook_service.py",
        "booking_engine->merchant_engine:booking_engine/stripe_webhook_service.py",
        "booking_engine->merchant_engine:booking_engine/tracking_service.py",
        "collaboration_engine->merchant_engine:collaboration_engine/crm_companies.py",
        "compliance_engine->admin_engine:compliance_engine/privacy_service.py",
        "compliance_engine->merchant_engine:compliance_engine/privacy_service.py",
        "gateway_engine->oauth_engine:gateway_engine/middleware.py",
        "merchant_engine->booking_engine:merchant_engine/activation_service.py",
        "merchant_engine->booking_engine:merchant_engine/invoice_reminder.py",
        "merchant_engine->booking_engine:merchant_engine/parcel_amend_service.py",
        "merchant_engine->booking_engine:merchant_engine/reporting_metrics.py",
        "merchant_engine->compliance_engine:merchant_engine/settings_service.py",
        "merchant_engine->gateway_engine:merchant_engine/booking_service.py",
        "merchant_engine->notification_engine:merchant_engine/invoice_reminder.py",
        "merchant_engine->order_engine:merchant_engine/parcel_amend_service.py",
        "merchant_engine->pricing_engine:merchant_engine/rate_card_view.py",
        "order_engine->merchant_engine:order_engine/platform_detail.py",
        "admin_engine->collaboration_engine:admin_engine/merchant_lifecycle.py",
        "admin_engine->merchant_engine:admin_engine/control_tower/service.py",
        "admin_engine->merchant_engine:admin_engine/order_assist_service.py",
        "admin_engine->merchant_engine:admin_engine/order_builder_service.py",
        "admin_engine->merchant_engine:admin_engine/settings_service.py",
        "billing_engine->admin_engine:billing_engine/driver_finance_service.py",
        "billing_engine->driver_engine:billing_engine/driver_finance_service.py",
        "booking_engine->merchant_engine:booking_engine/invoice_service.py",
        "booking_engine->support_engine:booking_engine/customer_service.py",
        "compliance_engine->support_engine:compliance_engine/privacy_service.py",
        "gateway_engine->merchant_engine:gateway_engine/merchant_api.py",
        "merchant_engine->booking_engine:merchant_engine/privacy.py",
        "merchant_engine->collaboration_engine:merchant_engine/activation_service.py",
        "merchant_engine->collaboration_engine:merchant_engine/organization_sync.py",
        "merchant_engine->support_engine:merchant_engine/orders_service.py",
        "support_engine->merchant_engine:support_engine/support_context.py",
        "support_engine->merchant_engine:support_engine/support_tickets.py",
        "admin_engine->intelligence_engine:admin_engine/control_tower/events.py",
        "admin_engine->collaboration_engine:admin_engine/crm_service.py",
        "admin_engine->collaboration_engine:admin_engine/diagnostics_probes.py",
        "admin_engine->intelligence_engine:admin_engine/dispatcher_copilot_service.py",
        "admin_engine->driver_engine:admin_engine/driver360_board.py",
        "admin_engine->driver_engine:admin_engine/driver360_service.py",
        "admin_engine->driver_engine:admin_engine/driver_documents.py",
        "admin_engine->driver_engine:admin_engine/driver_service.py",
        "admin_engine->intelligence_engine:admin_engine/merchant360_board.py",
        "admin_engine->gateway_engine:admin_engine/merchant360_board.py",
        "admin_engine->merchant_engine:admin_engine/merchant360_board.py",
        "admin_engine->intelligence_engine:admin_engine/orchestrator_ops_service.py",
        "admin_engine->intelligence_engine:admin_engine/order_assist_service.py",
        "admin_engine->merchant_engine:admin_engine/platform_settings.py",
        "admin_engine->intelligence_engine:admin_engine/settings_service.py",
        "booking_engine->admin_engine:booking_engine/confirmation_service.py",
        "booking_engine->billing_engine:booking_engine/confirmation_service.py",
        "booking_engine->admin_engine:booking_engine/invoice_service.py",
        "booking_engine->billing_engine:booking_engine/invoice_service.py",
        "booking_engine->admin_engine:booking_engine/quote_service.py",
        "booking_engine->driver_engine:booking_engine/stripe_webhook_service.py",
        "collaboration_engine->intelligence_engine:collaboration_engine/lead_metrics.py",
        "driver_engine->admin_engine:driver_engine/abstract_service.py",
        "driver_engine->admin_engine:driver_engine/background_check_service.py",
        "driver_engine->admin_engine:driver_engine/compliance_expiry_service.py",
        "driver_engine->admin_engine:driver_engine/verification_service.py",
        "intelligence_engine->billing_engine:intelligence_engine/tools.py",
        "intelligence_engine->admin_engine:intelligence_engine/tools.py",
        "merchant_engine->booking_engine:merchant_engine/profile_service.py",
        "merchant_engine->booking_engine:merchant_engine/sandbox_simulator.py",
        "order_engine->driver_engine:order_engine/platform_detail.py",
        "support_engine->admin_engine:support_engine/claims_mutations.py",
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


# §0.3.6 — legacy services above 1000 LOC (shrink; no new files).
_LEGACY_SERVICE_OVER_1000: frozenset[str] = frozenset(
    {
        "admin_engine/settings_service.py",
    }
)


def _check_service_modularity() -> list[str]:
    """§0.3.6 — no new 1000+ LOC *_service.py modules."""
    failures: list[str] = []
    api_src = ROOT / "apps/api/src/porterchain_api"
    for path in api_src.rglob("*_service.py"):
        rel = str(path.relative_to(api_src))
        lines = len(path.read_text().splitlines())
        if lines > 1000 and rel not in _LEGACY_SERVICE_OVER_1000:
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
        "operations.py",
        "driver/profile.py",
        "admin/leads.py",
    }
)

# §0.3.9 — route modules above 350 LOC (legacy); per-file caps shrink over time.
_LEGACY_ROUTER_LOC: dict[str, int] = {
    "merchants.py": 693,  # integration
    "auth.py": 407,
    "operations.py": 415,  # integration
    "driver/jobs.py": 400,
    "admin/leads.py": 632,
    "admin/settings.py": 464,
    "admin/orders.py": 380,  # integration
    "notifications.py": 370,  # integration
    "merchant/orders_tracking.py": 354,  # integration
}

MAX_NEW_ROUTER_LOC = 350
MAX_ENGINE_SERVICE_LOC = 500

# ENG-G2 — legacy services above 500 LOC (shrink over time; no new files may exceed 500).
_LEGACY_ENGINE_SERVICE_LOC: dict[str, int] = {
    "admin_engine/settings_service.py": 1298,  # integration
    "admin_engine/finance_service.py": 561,  # integration
    "admin_engine/merchant_service.py": 536,  # integration
    "admin_engine/orchestrator_ops_service.py": 677,
    "merchant_engine/shopify_service.py": 852,  # integration
    "merchant_engine/billing_service.py": 914,
    "merchant_engine/booking_flow_service.py": 551,  # integration
    "merchant_engine/integrations_service.py": 548,
    "notification_engine/admin_service.py": 600,
    "notification_engine/delivery_service.py": 628,
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
            r"from porterchain_api\.(models|merchant_models|admin_models)",
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
            rel = str(path.relative_to(api_src))
            # Legacy split modules above 400 LOC (shrink; no new oversized splits).
            if lines > 400 and rel not in {
                "order_engine/platform_detail.py",
                "admin_engine/diagnostics_validation.py",
                "collaboration_engine/crm_companies.py",
                "support_engine/support_tickets.py",
                "admin_engine/diagnostics_probes.py",  # integration
                "support_engine/claims_mutations.py",  # integration
            }:
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
    failures.extend(_check_driver_job_summary_parity())

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

    if not DRIVER_MOBILE_API.is_file():
        failures.append("mobile-driver api.ts missing")
    else:
        mobile = DRIVER_MOBILE_API.read_text()
        required_mobile = (
            "/driver-api/v1",
            "/push/register",
            "/push/unregister",
            "/jobs",
            "/support/hub",
            "/support/knowledge-base",
            "/communications/notifications",
            "/communications/notifications/history",
            "/communications/offline/retry",
            "/earnings/statements/",
            "/download",
            "/offline/sync",
            "/navigation/route",
        )
        for required in required_mobile:
            if required not in mobile:
                failures.append(f"mobile-driver api.ts missing {required}")

    print("D2 verification (filesystem + contracts)")
    if not failures:
        print(f"  filesystem: {len(FORBIDDEN_PATHS)} forbidden paths absent")
    print(f"  customer web: {sorted(web_customer)}")
    print(f"  driver web api: checked {len(required_driver)} paths")
    print("  driver mobile api: checked required field paths")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  PASS: customer + driver surfaces share Porterchain API contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

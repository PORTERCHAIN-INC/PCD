#!/usr/bin/env python3
"""Appendix C documentation simplification — process all 39 groups."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "masterrule.md"
VERIFIED = "2026-07-05"
MASTERRULE_LINK = "[§21](./masterrule.md#21-simplification--essential-complexity)"
MASTERRULE_LINK_NESTED = lambda depth: f"[§21]({'../' * depth}masterrule.md#21-simplification--essential-complexity)"

# --- Appendix C groups (39 × 5, G39 has 1 file) ---
GROUPS: dict[str, list[str]] = {
    "G01": [
        "ALEMBIC_VALIDATION.md",
        "API_DEPENDENCY_GRAPH.md",
        "API_FLOW_DIAGRAM.md",
        "API_FLOW_REPORT.md",
        "API_TRACE_REPORT.md",
    ],
    "G02": [
        "ARCHITECTURE_ALIGNMENT_REPORT.md",
        "ARCHITECTURE_AUDIT.md",
        "AUTHENTICATION.md",
        "AUTHENTICATION_ARCHITECTURE.md",
        "AUTHENTICATION_AUDIT.md",
    ],
    "G03": [
        "AUTHENTICATION_CLEANUP.md",
        "AUTHENTICATION_FLOW.md",
        "BOOKING_WORKFLOW_AUDIT.md",
        "BUSINESS_GLOSSARY.md",
        "BUSINESS_WORKFLOW.md",
    ],
    "G04": [
        "CLERK_INTEGRATION_REPORT.md",
        "CONNECTIONS.md",
        "CONTRIBUTING_GUIDE.md",
        "CTO_AUDIT_REPORT.md",
        "DATABASE_ARCHITECTURE.md",
    ],
    "G05": [
        "DATABASE_AUDIT.md",
        "DATABASE_CONFIGURATION_REPORT.md",
        "DATABASE_MIGRATION_PLAN.md",
        "DATABASE_OWNERSHIP_MATRIX.md",
        "DATABASE_VALIDATION_REPORT.md",
    ],
    "G06": [
        "DATA_CONSISTENCY_REPORT.md",
        "DEPENDENCY_REPORT.md",
        "DOCKER_ARCHITECTURE.md",
        "DOCKER_SETUP.md",
        "DOMAIN_MODEL.md",
    ],
    "G07": [
        "DRIVER_ARCHITECTURE_REPORT.md",
        "DRIVER_AUDIT.md",
        "DRIVER_INTEGRATION_MATRIX.md",
        "DRIVER_PERFORMANCE_REPORT.md",
        "DRIVER_PLATFORM.md",
    ],
    "G08": [
        "DRIVER_PRODUCTION_READINESS.md",
        "DRIVER_SECURITY_REPORT.md",
        "ENTITY_RELATIONSHIP_MODEL.md",
        "ENVIRONMENT_VARIABLES.md",
        "EVENT_BUS.md",
    ],
    "G09": [
        "EVENT_BUS_AUDIT.md",
        "EVENT_BUS_REPORT.md",
        "EVENT_CATALOG.md",
        "EVENT_FLOW.md",
        "EVENT_FLOW_DIAGRAM.md",
    ],
    "G10": [
        "EVENT_MATRIX.md",
        "EXCEPTION_WORKFLOWS.md",
        "EXTENSION_GUIDE.md",
        "FAILURE_SCENARIOS_REPORT.md",
        "FLEETBASE_ADAPTER_ARCHITECTURE.md",
    ],
    "G11": [
        "FLEETBASE_ANALYSIS.md",
        "FLEETBASE_APIS.md",
        "FLEETBASE_DATABASE.md",
        "FLEETBASE_EVENTS.md",
        "FLEETBASE_EXTENSION_POINTS.md",
    ],
    "G12": [
        "FLEETBASE_INSTALL.md",
        "FLEETBASE_INTEGRATION.md",
        "FLEETBASE_MODULES.md",
        "FLEETBASE_SERVICE_STATUS.md",
        "FLEETBASE_USAGE.md",
    ],
    "G13": [
        "FLEETBASE_WEBHOOKS.md",
        "FOLDER_STRUCTURE.md",
        "FORWARD_LOGISTICS_REPORT.md",
        "GAP_ANALYSIS.md",
        "GOOGLE_MAPS_REPORT.md",
    ],
    "G14": [
        "GOOGLE_MAPS_USAGE.md",
        "GOOGLE_MAPS_USAGE_REPORT.md",
        "INTEGRATIONS.md",
        "INTEGRATION_AUDIT.md",
        "INVITATION_WORKFLOW.md",
    ],
    "G15": [
        "MAPS_ARCHITECTURE_AUDIT.md",
        "MASTERULE_COMPLIANCE_GAPS.md",
        "MERCHANT_ARCHITECTURE_REPORT.md",
        "MERCHANT_AUDIT.md",
        "MERCHANT_COMPONENT_MATRIX.md",
    ],
    "G16": [
        "MERCHANT_GAP_ANALYSIS.md",
        "MERCHANT_INTEGRATION_MATRIX.md",
        "MERCHANT_PERFORMANCE_REPORT.md",
        "MERCHANT_PRODUCTION_READINESS.md",
        "MERCHANT_SECURITY_REPORT.md",
    ],
    "G17": [
        "MISSING_INTEGRATIONS.md",
        "MOBILE_ARCHITECTURE.md",
        "MOBILE_ARCHITECTURE_REPORT.md",
        "MOBILE_DESIGN_SYSTEM.md",
        "MOBILE_PERFORMANCE_REPORT.md",
    ],
    "G18": [
        "MOBILE_PRODUCTION_READINESS.md",
        "MOBILE_SECURITY_REPORT.md",
        "MOBILE_UI_REPORT.md",
        "MODULE_BREAKDOWN.md",
        "MODULE_DEPENDENCY_GRAPH.md",
    ],
    "G19": [
        "MODULE_INTEGRATION_MATRIX.md",
        "MODULE_SCORECARD.md",
        "NOTIFICATION_REPORT.md",
        "ORDER_LIFECYCLE.md",
        "ORDER_LIFECYCLE_REPORT.md",
    ],
    "G20": [
        "OSRM_REPORT.md",
        "OSRM_USAGE.md",
        "PERFORMANCE_AUDIT.md",
        "PLATFORM_FOUNDATION.md",
        "PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md",
    ],
    "G21": [
        "PORT_CONFIGURATION.md",
        "POSTGRESQL_COMPATIBILITY_REPORT.md",
        "POSTGRESQL_PERFORMANCE.md",
        "PRICING_ENGINE.md",
        "PRODUCTION_DATABASE_SCORE.md",
    ],
    "G22": [
        "PRODUCTION_READINESS_REPORT.md",
        "PRODUCT_REQUIREMENTS.md",
        "RBAC.md",
        "RBAC_MATRIX.md",
        "README.md",
    ],
    "G23": [
        "REALTIME_COMMUNICATION_REPORT.md",
        "REPOSITORY_STRUCTURE.md",
        "REVERSE_LOGISTICS_REPORT.md",
        "ROADMAP.md",
        "ROLE_PERMISSIONS.md",
    ],
    "G24": [
        "ROUTE_CENTER_ARCHITECTURE.md",
        "ROUTE_CENTER_AUDIT.md",
        "ROUTE_CENTER_INTEGRATION.md",
        "ROUTE_CENTER_PERFORMANCE.md",
        "ROUTING_ENGINE_AUDIT.md",
    ],
    "G25": [
        "RUNBOOK.md",
        "SECURITY.md",
        "SECURITY_AUDIT.md",
        "SERVICE_STATUS.md",
        "SQLITE_AUDIT.md",
    ],
    "G26": [
        "SSO.md",
        "SYSTEM_ARCHITECTURE.md",
        "SYSTEM_SEQUENCE_DIAGRAMS.md",
        "SYSTEM_VALIDATION_REPORT.md",
        "TECH_STACK.md",
    ],
    "G27": [
        "UPGRADE_GUIDE.md",
        "USER_JOURNEYS.md",
        "VALHALLA_REPORT.md",
        "VALHALLA_USAGE.md",
        "apps/admin/README.md",
    ],
    "G28": [
        "apps/api/README.md",
        "apps/api/alembic/README.md",
        "apps/customer/README.md",
        "apps/driver/README.md",
        "apps/merchant-portal/README.md",
    ],
    "G29": [
        "apps/merchant/README.md",
        "apps/mobile-customer/.expo/README.md",
        "apps/mobile-customer/README.md",
        "apps/mobile-driver/README.md",
        "apps/website/README.md",
    ],
    "G30": [
        "apps/worker/README.md",
        "docs/README.md",
        "docs/architecture/ADMIN_CONTROL_TOWER.md",
        "docs/architecture/API_DEPENDENCY.md",
        "docs/architecture/APPLICATION_FLOW.md",
    ],
    "G31": [
        "docs/architecture/ARCHITECTURE_VALIDATION_REPORT.md",
        "docs/architecture/AUTHENTICATION_FLOW.md",
        "docs/architecture/BOOKING_FLOW.md",
        "docs/architecture/DATABASE_RELATIONSHIP.md",
        "docs/architecture/DISPATCH_FLOW.md",
    ],
    "G32": [
        "docs/architecture/EVENT_BUS_FLOW.md",
        "docs/architecture/FLEETBASE_FLOW.md",
        "docs/architecture/GOOGLE_MAPS_FLOW.md",
        "docs/architecture/MERCHANT_FLOW.md",
        "docs/architecture/MODULE_DEPENDENCY.md",
    ],
    "G33": [
        "docs/architecture/NOTIFICATION_FLOW.md",
        "docs/architecture/ORDER_LIFECYCLE.md",
        "docs/architecture/OSRM_FLOW.md",
        "docs/architecture/PAYMENT_FLOW.md",
        "docs/architecture/README.md",
    ],
    "G34": [
        "docs/architecture/REALTIME_FLOW.md",
        "docs/architecture/REPORTING_FLOW.md",
        "docs/architecture/SYSTEM_ARCHITECTURE.md",
        "docs/architecture/VALHALLA_FLOW.md",
        "docs/notifications/DEVICE_REGISTRATION_FLOW.md",
    ],
    "G35": [
        "docs/notifications/FCM_CONFIGURATION.md",
        "docs/notifications/NOTIFICATION_ARCHITECTURE.md",
        "docs/notifications/NOTIFICATION_DELIVERY_FLOW.md",
        "docs/notifications/NOTIFICATION_EVENT_MATRIX.md",
        "docs/notifications/NOTIFICATION_TEMPLATE_CATALOG.md",
    ],
    "G36": [
        "docs/notifications/PUSH_NOTIFICATION_REPORT.md",
        "env/README.md",
        "infrastructure/deploy/README.md",
        "masterrule.md",
        "packages/config/README.md",
    ],
    "G37": [
        "packages/shared/README.md",
        "services/README.md",
        "services/fleetbase-adapter/README.md",
        "services/pricing-engine/README.md",
        "shared/README.md",
    ],
    "G38": [
        "shared/config/README.md",
        "shared/maps/MAP_MODULE.md",
        "vendor/fleetbase/README.md",
        "website/AGENTS.md",
        "website/CLAUDE.md",
    ],
    "G39": ["website/README.md"],
}

ALL_FILES = [f for files in GROUPS.values() for f in files]


@dataclass
class PointerSpec:
    title: str
    canonical: str  # relative from file dir
    blurb: str
    related: str | None = None
    archive: str | None = None


def rel_link(from_path: Path, to_path: str) -> str:
    target = ROOT / to_path
    rel = Path(os_path_relpath(from_path.parent, target))
    return rel.as_posix()


def os_path_relpath(from_dir: Path, to_file: Path) -> str:
    import os

    return os.path.relpath(to_file, start=from_dir)


def masterrule_for(path: Path) -> str:
    depth = len(path.relative_to(ROOT).parts) - 1
    if depth == 0:
        return MASTERRULE_LINK
    prefix = "../" * depth
    return f"[§21]({prefix}masterrule.md#21-simplification--essential-complexity)"


def header_block(doc_type: str, path: Path) -> str:
    return (
        f"**Type:** {doc_type}\n"
        f"**masterrule:** {masterrule_for(path)}\n"
        f"**Last verified:** {VERIFIED}\n"
    )


def write_pointer(path: Path, spec: PointerSpec) -> None:
    canon = spec.canonical
    lines = [
        f"# {spec.title}",
        "",
        header_block("POINTER", path).rstrip(),
        "",
        f"Pointer to **[{Path(canon).name}]({canon})** — {spec.blurb}",
    ]
    if spec.related:
        lines.append(f"See also: {spec.related}")
    if spec.archive:
        lines.append(f"Archive: [{Path(spec.archive).name}]({spec.archive})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def report_banner(canonical: str, label: str = "canonical doc") -> str:
    return f"> **Snapshot report** — point-in-time audit. Current truth: [{Path(canonical).name}]({canonical}) ({label}).\n"


def canonical_footer(path: Path, extras: list[tuple[str, str]] | None = None) -> str:
    depth = len(path.relative_to(ROOT).parts) - 1
    prefix = "../" * depth
    rows = [
        (f"{prefix}masterrule.md", "Architecture SSOT"),
        (f"{prefix}CTO_AUDIT_REPORT.md", "Doc vs code audit"),
    ]
    if extras:
        rows.extend(extras)
    if "api" in str(path) or path.name in {"INTEGRATIONS.md", "CONNECTIONS.md"}:
        rows.append(("http://localhost:8001/docs", "OpenAPI (local)"))
    body = "\n".join(f"| [{Path(t).name if not t.startswith('http') else 'OpenAPI'}]({t}) | {d} |" for t, d in rows)
    return f"\n---\n\n## Governance\n\n| Document | Role |\n| -------- | ---- |\n{body}\n"


def ensure_report_banner(content: str, canonical: str) -> str:
    banner = report_banner(canonical)
    if "Snapshot report" in content:
        return content
    # insert after header block (after Last verified line)
    m = re.search(r"(\*\*Last verified:\*\* [^\n]+\n)", content)
    if m:
        insert_at = m.end()
        return content[:insert_at] + "\n" + banner + content[insert_at:]
    return banner + content


def ensure_canonical_footer(content: str, path: Path, extras: list[tuple[str, str]] | None = None) -> str:
    footer = canonical_footer(path, extras)
    if "## Governance" in content:
        # replace existing governance section
        content = re.sub(r"\n---\n\n## Governance\n[\s\S]*$", "", content.rstrip())
    return content.rstrip() + footer


def normalize_supporting_to_pointer(path: Path, spec: PointerSpec) -> None:
    write_pointer(path, spec)


# Pointer registry: path -> PointerSpec (relative canonical from file's directory)
def pointer_specs() -> dict[str, PointerSpec]:
    P = PointerSpec
    return {
        "API_DEPENDENCY_GRAPH.md": P("API Dependency Graph", "docs/architecture/API_DEPENDENCY.md", "module dependency map"),
        "API_FLOW_DIAGRAM.md": P("API Flow Diagram", "docs/architecture/APPLICATION_FLOW.md", "request flow diagrams"),
        "API_FLOW_REPORT.md": P("API Flow Report", "docs/architecture/APPLICATION_FLOW.md", "API request flows", archive="docs/archive/API_FLOW_REPORT.md"),
        "API_TRACE_REPORT.md": P("API Trace Report", "apps/api/README.md", "route surfaces; use OpenAPI `/docs`"),
        "ARCHITECTURE_ALIGNMENT_REPORT.md": P("Architecture Alignment Report", "CTO_AUDIT_REPORT.md", "doc vs code alignment"),
        "ARCHITECTURE_AUDIT.md": P("Architecture Audit", "docs/architecture/SYSTEM_ARCHITECTURE.md", "platform topology", archive="docs/archive/ARCHITECTURE_AUDIT.md"),
        "AUTHENTICATION.md": P("Authentication", "AUTHENTICATION_ARCHITECTURE.md", "Clerk topology and security"),
        "AUTHENTICATION_AUDIT.md": P("Authentication Audit", "AUTHENTICATION_ARCHITECTURE.md", "auth architecture", archive="docs/archive/AUTHENTICATION_AUDIT.md"),
        "AUTHENTICATION_CLEANUP.md": P("Authentication Cleanup", "AUTHENTICATION_ARCHITECTURE.md", "auth consolidation notes"),
        "AUTHENTICATION_FLOW.md": P("Authentication Flow", "docs/architecture/AUTHENTICATION_FLOW.md", "sequence diagrams"),
        "BOOKING_WORKFLOW_AUDIT.md": P("Booking Workflow Audit", "docs/architecture/BOOKING_FLOW.md", "booking flow"),
        "DATABASE_AUDIT.md": P("Database Audit", "DATABASE_ARCHITECTURE.md", "schema and ownership"),
        "DATABASE_CONFIGURATION_REPORT.md": P("Database Configuration Report", "ENVIRONMENT_VARIABLES.md", "database env vars"),
        "DATABASE_VALIDATION_REPORT.md": P("Database Validation Report", "ALEMBIC_VALIDATION.md", "migration validation"),
        "CLERK_INTEGRATION_REPORT.md": P("Clerk Integration Report", "AUTHENTICATION_ARCHITECTURE.md", "Clerk apps and flows"),
        "DRIVER_ARCHITECTURE_REPORT.md": P("Driver Architecture Report", "DRIVER_PLATFORM.md", "driver platform design"),
        "DRIVER_AUDIT.md": P("Driver Audit", "DRIVER_PLATFORM.md", "driver module audit"),
        "DRIVER_INTEGRATION_MATRIX.md": P("Driver Integration Matrix", "DRIVER_PLATFORM.md", "driver integrations"),
        "DRIVER_PERFORMANCE_REPORT.md": P("Driver Performance Report", "DRIVER_PLATFORM.md", "driver performance"),
        "DRIVER_SECURITY_REPORT.md": P("Driver Security Report", "SECURITY.md", "security baseline"),
        "EVENT_BUS_AUDIT.md": P("Event Bus Audit", "EVENT_BUS.md", "event bus design"),
        "EVENT_BUS_REPORT.md": P("Event Bus Report", "EVENT_CATALOG.md", "event catalog"),
        "EVENT_FLOW.md": P("Event Flow", "docs/architecture/EVENT_BUS_FLOW.md", "event bus flow"),
        "EVENT_FLOW_DIAGRAM.md": P("Event Flow Diagram", "docs/architecture/EVENT_BUS_FLOW.md", "event diagrams"),
        "EVENT_MATRIX.md": P("Event Matrix", "EVENT_CATALOG.md", "published events"),
        "FLEETBASE_ANALYSIS.md": P("Fleetbase Analysis", "FLEETBASE_INTEGRATION.md", "integration overview"),
        "FLEETBASE_APIS.md": P("Fleetbase APIs", "services/fleetbase-adapter/README.md", "adapter API boundary"),
        "FLEETBASE_DATABASE.md": P("Fleetbase Database", "FLEETBASE_INTEGRATION.md", "data ownership"),
        "FLEETBASE_EVENTS.md": P("Fleetbase Events", "FLEETBASE_WEBHOOKS.md", "webhook events"),
        "FLEETBASE_USAGE.md": P("Fleetbase Usage", "FLEETBASE_INTEGRATION.md", "operational usage"),
        "FLEETBASE_WEBHOOKS.md": P("Fleetbase Webhooks", "FLEETBASE_INTEGRATION.md", "ingress and verification"),
        "FOLDER_STRUCTURE.md": P("Folder Structure", "REPOSITORY_STRUCTURE.md", "monorepo layout"),
        "GOOGLE_MAPS_REPORT.md": P("Google Maps Report", "GOOGLE_MAPS_USAGE.md", "maps usage policy"),
        "GOOGLE_MAPS_USAGE_REPORT.md": P("Google Maps Usage Report", "GOOGLE_MAPS_USAGE.md", "maps integration"),
        "INTEGRATION_AUDIT.md": P("Integration Audit", "INTEGRATIONS.md", "external systems matrix"),
        "MAPS_ARCHITECTURE_AUDIT.md": P("Maps Architecture Audit", "GOOGLE_MAPS_USAGE.md", "maps architecture"),
        "MASTERULE_COMPLIANCE_GAPS.md": P("Masterrule Compliance Gaps", "CTO_AUDIT_REPORT.md", "compliance gaps"),
        "MERCHANT_AUDIT.md": P("Merchant Audit", "docs/architecture/MERCHANT_FLOW.md", "merchant flows"),
        "MERCHANT_COMPONENT_MATRIX.md": P("Merchant Component Matrix", "docs/architecture/MERCHANT_FLOW.md", "merchant UI map"),
        "MERCHANT_GAP_ANALYSIS.md": P("Merchant Gap Analysis", "GAP_ANALYSIS.md", "platform gaps"),
        "MERCHANT_PERFORMANCE_REPORT.md": P("Merchant Performance Report", "docs/architecture/MERCHANT_FLOW.md", "merchant performance"),
        "MERCHANT_SECURITY_REPORT.md": P("Merchant Security Report", "SECURITY.md", "security baseline"),
        "MOBILE_PERFORMANCE_REPORT.md": P("Mobile Performance Report", "MOBILE_ARCHITECTURE.md", "mobile architecture"),
        "MOBILE_SECURITY_REPORT.md": P("Mobile Security Report", "MOBILE_ARCHITECTURE.md", "mobile security"),
        "MOBILE_UI_REPORT.md": P("Mobile UI Report", "MOBILE_DESIGN_SYSTEM.md", "mobile design system"),
        "ORDER_LIFECYCLE_REPORT.md": P("Order Lifecycle Report", "ORDER_LIFECYCLE.md", "order state machine"),
        "OSRM_REPORT.md": P("OSRM Report", "OSRM_USAGE.md", "OSRM routing usage"),
        "POSTGRESQL_COMPATIBILITY_REPORT.md": P("PostgreSQL Compatibility Report", "DATABASE_ARCHITECTURE.md", "PostgreSQL compatibility"),
        "POSTGRESQL_PERFORMANCE.md": P("PostgreSQL Performance", "DATABASE_ARCHITECTURE.md", "database performance"),
        "PRODUCTION_DATABASE_SCORE.md": P("Production Database Score", "PRODUCTION_READINESS_REPORT.md", "go/no-go database"),
        "RBAC.md": P("RBAC", "RBAC_MATRIX.md", "roles and permissions matrix"),
        "ROUTE_CENTER_AUDIT.md": P("Route Center Audit", "ROUTE_CENTER_ARCHITECTURE.md", "route center design"),
        "ROUTE_CENTER_INTEGRATION.md": P("Route Center Integration", "ROUTE_CENTER_ARCHITECTURE.md", "Fleetbase route integration"),
        "ROUTE_CENTER_PERFORMANCE.md": P("Route Center Performance", "ROUTE_CENTER_ARCHITECTURE.md", "route center performance"),
        "ROUTING_ENGINE_AUDIT.md": P("Routing Engine Audit", "VALHALLA_USAGE.md", "Valhalla/OSRM routing"),
        "SECURITY_AUDIT.md": P("Security Audit", "SECURITY.md", "security architecture"),
        "SERVICE_STATUS.md": P("Service Status", "RUNBOOK.md", "operational runbook"),
        "SQLITE_AUDIT.md": P("SQLite Audit", "DATABASE_ARCHITECTURE.md", "SQLite removed — PostgreSQL only"),
        "SYSTEM_ARCHITECTURE.md": P("System Architecture", "docs/architecture/SYSTEM_ARCHITECTURE.md", "platform topology"),
        "SYSTEM_VALIDATION_REPORT.md": P("System Validation Report", "CTO_AUDIT_REPORT.md", "validation audit"),
        "VALHALLA_REPORT.md": P("Valhalla Report", "VALHALLA_USAGE.md", "Valhalla routing"),
        "PERFORMANCE_AUDIT.md": P("Performance Audit", "CTO_AUDIT_REPORT.md", "performance findings"),
    }


REPORT_CANONICAL: dict[str, str] = {
    "FAILURE_SCENARIOS_REPORT.md": "RUNBOOK.md",
    "FORWARD_LOGISTICS_REPORT.md": "ORDER_LIFECYCLE.md",
    "REVERSE_LOGISTICS_REPORT.md": "ORDER_LIFECYCLE.md",
    "DATA_CONSISTENCY_REPORT.md": "DATABASE_ARCHITECTURE.md",
    "DEPENDENCY_REPORT.md": "INTEGRATIONS.md",
    "MERCHANT_ARCHITECTURE_REPORT.md": "docs/architecture/MERCHANT_FLOW.md",
    "MOBILE_ARCHITECTURE_REPORT.md": "MOBILE_ARCHITECTURE.md",
    "MODULE_INTEGRATION_MATRIX.md": "INTEGRATIONS.md",
    "MODULE_SCORECARD.md": "PRODUCTION_READINESS_REPORT.md",
    "NOTIFICATION_REPORT.md": "docs/notifications/NOTIFICATION_ARCHITECTURE.md",
    "REALTIME_COMMUNICATION_REPORT.md": "docs/architecture/REALTIME_FLOW.md",
    "docs/architecture/ARCHITECTURE_VALIDATION_REPORT.md": "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/architecture/REPORTING_FLOW.md": "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/notifications/NOTIFICATION_EVENT_MATRIX.md": "EVENT_CATALOG.md",
    "docs/notifications/PUSH_NOTIFICATION_REPORT.md": "docs/notifications/NOTIFICATION_ARCHITECTURE.md",
}

# Files that should be CANONICAL (normalize Type header only + footer)
CANONICAL_FILES = {
    "ALEMBIC_VALIDATION.md",
    "AUTHENTICATION_ARCHITECTURE.md",
    "BUSINESS_GLOSSARY.md",
    "CONNECTIONS.md",
    "CONTRIBUTING_GUIDE.md",
    "CTO_AUDIT_REPORT.md",
    "DATABASE_ARCHITECTURE.md",
    "DATABASE_OWNERSHIP_MATRIX.md",
    "DOCKER_ARCHITECTURE.md",
    "DOCKER_SETUP.md",
    "DOMAIN_MODEL.md",
    "DRIVER_PLATFORM.md",
    "ENVIRONMENT_VARIABLES.md",
    "EVENT_BUS.md",
    "EVENT_CATALOG.md",
    "FLEETBASE_ADAPTER_ARCHITECTURE.md",
    "FLEETBASE_INSTALL.md",
    "FLEETBASE_INTEGRATION.md",
    "GAP_ANALYSIS.md",
    "GOOGLE_MAPS_USAGE.md",
    "INTEGRATIONS.md",
    "INVITATION_WORKFLOW.md",
    "MERCHANT_INTEGRATION_MATRIX.md",
    "MISSING_INTEGRATIONS.md",
    "ORDER_LIFECYCLE.md",
    "OSRM_USAGE.md",
    "PORT_CONFIGURATION.md",
    "PRODUCTION_READINESS_REPORT.md",
    "RBAC_MATRIX.md",
    "README.md",
    "REPOSITORY_STRUCTURE.md",
    "ROLE_PERMISSIONS.md",
    "ROUTE_CENTER_ARCHITECTURE.md",
    "RUNBOOK.md",
    "SSO.md",
    "TECH_STACK.md",
    "VALHALLA_USAGE.md",
    "docs/README.md",
    "docs/architecture/BOOKING_FLOW.md",
    "docs/architecture/DISPATCH_FLOW.md",
    "docs/architecture/FLEETBASE_FLOW.md",
    "docs/architecture/PAYMENT_FLOW.md",
    "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/notifications/NOTIFICATION_ARCHITECTURE.md",
    "env/README.md",
    "infrastructure/deploy/README.md",
    "masterrule.md",
}

# Flow/supporting docs → CANONICAL
FLOW_CANONICAL = {
    "docs/architecture/ADMIN_CONTROL_TOWER.md",
    "docs/architecture/API_DEPENDENCY.md",
    "docs/architecture/APPLICATION_FLOW.md",
    "docs/architecture/AUTHENTICATION_FLOW.md",
    "docs/architecture/DATABASE_RELATIONSHIP.md",
    "docs/architecture/EVENT_BUS_FLOW.md",
    "docs/architecture/GOOGLE_MAPS_FLOW.md",
    "docs/architecture/MERCHANT_FLOW.md",
    "docs/architecture/MODULE_DEPENDENCY.md",
    "docs/architecture/NOTIFICATION_FLOW.md",
    "docs/architecture/ORDER_LIFECYCLE.md",
    "docs/architecture/OSRM_FLOW.md",
    "docs/architecture/REALTIME_FLOW.md",
    "docs/architecture/VALHALLA_FLOW.md",
    "docs/notifications/DEVICE_REGISTRATION_FLOW.md",
    "docs/notifications/FCM_CONFIGURATION.md",
    "docs/notifications/NOTIFICATION_DELIVERY_FLOW.md",
    "docs/notifications/NOTIFICATION_TEMPLATE_CATALOG.md",
}

# Supporting docs kept as CANONICAL (topic guides)
SUPPORTING_CANONICAL = {
    "BUSINESS_WORKFLOW.md",
    "DATABASE_MIGRATION_PLAN.md",
    "DRIVER_PRODUCTION_READINESS.md",
    "ENTITY_RELATIONSHIP_MODEL.md",
    "EXCEPTION_WORKFLOWS.md",
    "EXTENSION_GUIDE.md",
    "FLEETBASE_EXTENSION_POINTS.md",
    "FLEETBASE_MODULES.md",
    "FLEETBASE_SERVICE_STATUS.md",
    "MERCHANT_PRODUCTION_READINESS.md",
    "MOBILE_ARCHITECTURE.md",
    "MOBILE_DESIGN_SYSTEM.md",
    "MOBILE_PRODUCTION_READINESS.md",
    "MODULE_BREAKDOWN.md",
    "MODULE_DEPENDENCY_GRAPH.md",
    "PLATFORM_FOUNDATION.md",
    "PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md",
    "PRICING_ENGINE.md",
    "PRODUCT_REQUIREMENTS.md",
    "ROADMAP.md",
    "SECURITY.md",
    "SYSTEM_SEQUENCE_DIAGRAMS.md",
    "UPGRADE_GUIDE.md",
    "USER_JOURNEYS.md",
    "shared/maps/MAP_MODULE.md",
    "website/AGENTS.md",
    "website/CLAUDE.md",
}

README_FILES = {f for f in ALL_FILES if f.endswith("README.md") or f.endswith("AGENTS.md") or f.endswith("CLAUDE.md")}


def fix_type_header(content: str, doc_type: str) -> str:
    content = re.sub(r"\*\*Type:\*\* [^\n]+", f"**Type:** {doc_type}", content, count=1)
    if "**Last verified:**" not in content:
        content = re.sub(
            r"(\*\*masterrule:\*\* [^\n]+\n)",
            rf"\1**Last verified:** {VERIFIED}\n",
            content,
            count=1,
        )
    else:
        content = re.sub(r"\*\*Last verified:\*\* [^\n]+", f"**Last verified:** {VERIFIED}", content, count=1)
    return content


def process_file(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return f"MISSING {rel}"

    pointers = pointer_specs()
    rel_key = rel

    if rel in pointers or rel_key in pointers:
        spec = pointers.get(rel) or pointers.get(rel_key)
        # fix relative canonical from file location
        canon_path = (path.parent / spec.canonical).as_posix()
        # recompute relative from path.parent
        import os

        canon_rel = os.path.relpath(ROOT / spec.canonical, path.parent)
        archive_rel = None
        if spec.archive:
            archive_rel = os.path.relpath(ROOT / spec.archive, path.parent)
        write_pointer(
            path,
            PointerSpec(spec.title, canon_rel, spec.blurb, spec.related, archive_rel),
        )
        return "POINTER"

    if rel in REPORT_CANONICAL:
        content = path.read_text(encoding="utf-8")
        content = fix_type_header(content, "REPORT")
        content = ensure_report_banner(content, os_path_relpath(path.parent, ROOT / REPORT_CANONICAL[rel]))
        content = ensure_canonical_footer(content, path)
        path.write_text(content, encoding="utf-8")
        return "REPORT"

    if rel in CANONICAL_FILES or rel in FLOW_CANONICAL or rel in SUPPORTING_CANONICAL:
        if rel == "masterrule.md":
            return "SKIP_MASTERRULE"
        content = path.read_text(encoding="utf-8")
        content = fix_type_header(content, "CANONICAL")
        content = ensure_canonical_footer(content, path)
        path.write_text(content, encoding="utf-8")
        return "CANONICAL"

    if rel in README_FILES or rel.endswith("/README.md"):
        content = path.read_text(encoding="utf-8")
        content = fix_type_header(content, "README")
        if "## Governance" not in content:
            depth = len(path.relative_to(ROOT).parts) - 1
            prefix = "../" * depth
            gov = (
                f"\n---\n\n## Governance\n\n"
                f"| Document | Role |\n| -------- | ---- |\n"
                f"| [{prefix}masterrule.md]({prefix}masterrule.md) | Architecture SSOT |\n"
                f"| [{prefix}REPOSITORY_STRUCTURE.md]({prefix}REPOSITORY_STRUCTURE.md) | Monorepo layout |\n"
            )
            content = content.rstrip() + gov + "\n"
        path.write_text(content, encoding="utf-8")
        return "README"

    # fallback: read type from file
    content = path.read_text(encoding="utf-8")
    m = re.search(r"\*\*Type:\*\* (\S+)", content)
    doc_type = m.group(1) if m else "CANONICAL"
    if doc_type == "POINTER":
        return "POINTER_OK"
    content = fix_type_header(content, doc_type if doc_type != "SUPPORTING" else "CANONICAL")
    if doc_type == "REPORT":
        content = ensure_report_banner(content, "../CTO_AUDIT_REPORT.md")
    content = ensure_canonical_footer(content, path)
    path.write_text(content, encoding="utf-8")
    return f"FALLBACK_{doc_type}"


def update_masterrule_groups() -> None:
    text = MASTER.read_text(encoding="utf-8")
    text = re.sub(
        r"\*\*Phase 0 \(done\):\*\*[^\n]+\n",
        "**Phase 0 (done):** §21.4 headers on all 191 files.  \n**Phase 1 (done):** All 39 groups processed (2026-07-05).  \n",
        text,
    )
    text = re.sub(
        r"\*\*Status:\*\* rollout in progress \(July 2026\)",
        "**Status:** Phase 1 complete (July 2026)",
        text,
    )
    text = re.sub(r"\| (G\d{2}) \| ([^|]+) \| (?:Pending|In progress) \|", r"| \1 | \2 | Done |", text)
    MASTER.write_text(text, encoding="utf-8")


def main() -> None:
    stats: dict[str, int] = {}
    for rel in ALL_FILES:
        action = process_file(rel)
        stats[action] = stats.get(action, 0) + 1
        print(f"{action:16} {rel}")
    update_masterrule_groups()
    print("\n--- Summary ---")
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"Total: {len(ALL_FILES)}")


if __name__ == "__main__":
    main()

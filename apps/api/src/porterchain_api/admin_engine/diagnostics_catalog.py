"""Diagnostics catalog — component categories, test definitions, masterrule references."""

from __future__ import annotations

HEALTH_CATEGORIES: tuple[str, ...] = (
    "portals",
    "engines",
    "integrations",
    "infrastructure",
    "observability",
)

CATEGORY_LABELS: dict[str, str] = {
    "portals": "Applications & Portals",
    "engines": "Application Engines",
    "integrations": "External Integrations",
    "infrastructure": "Infrastructure",
    "observability": "Observability & Workers",
}

COMPONENT_CATEGORY: dict[str, str] = {
    "website": "portals",
    "customer_portal": "portals",
    "merchant_portal": "portals",
    "admin_portal": "portals",
    "driver_mobile": "portals",
    "porterchain_api": "infrastructure",
    "pricing_engine": "engines",
    "billing_engine": "engines",
    "notification_engine": "engines",
    "orders_engine": "engines",
    "crm_engine": "engines",
    "finance_engine": "engines",
    "claims_engine": "engines",
    "support_engine": "engines",
    "event_bus": "infrastructure",
    "postgresql": "infrastructure",
    "redis": "infrastructure",
    "fleetbase_adapter": "integrations",
    "fleetbase": "integrations",
    "fleetbase_console": "integrations",
    "google_maps": "integrations",
    "osrm": "integrations",
    "valhalla": "integrations",
    "vroom": "integrations",  # fleetbase-first:ok — catalog id, not a PC solver
    "clerk": "integrations",
    "stripe": "integrations",
    "firebase_fcm": "integrations",
    "email_smtp": "integrations",
    "mailpit": "integrations",
    "websockets": "observability",
    "background_workers": "observability",
    "scheduled_jobs": "observability",
    "readiness_probe": "observability",
    "metrics_endpoint": "observability",
}

TEST_CATALOG: list[dict[str, str]] = [
    {"id": "clerk", "name": "Clerk", "category": "integrations", "description": "JWKS + auth configuration", "masterrule": "§15"},
    {"id": "stripe", "name": "Stripe", "category": "integrations", "description": "Live API + checkout config", "masterrule": "§14"},
    {"id": "firebase", "name": "Firebase FCM", "category": "integrations", "description": "Push notification project", "masterrule": "§11.3"},
    {"id": "google_maps", "name": "Google Maps", "category": "integrations", "description": "Geocoding API probe", "masterrule": "Appendix B"},
    {"id": "osrm", "name": "OSRM", "category": "integrations", "description": "Routing fallback", "masterrule": "Appendix B"},
    {"id": "valhalla", "name": "Valhalla", "category": "integrations", "description": "Primary routing engine", "masterrule": "Appendix B"},
    {"id": "vroom", "name": "VROOM (Fleetbase orchestrator)", "category": "integrations", "description": "Multi-stop TSP inside Fleetbase", "masterrule": "Appendix B"},  # fleetbase-first:ok
    {"id": "fleetbase", "name": "Fleetbase", "category": "integrations", "description": "Execution engine HTTP", "masterrule": "§13"},
    {"id": "fleetbase_adapter", "name": "Fleetbase Adapter", "category": "integrations", "description": "Mandatory adapter boundary", "masterrule": "§8, ADR-003"},
    {"id": "fleetbase_console", "name": "Fleetbase Console", "category": "integrations", "description": "Dispatch console (SSO)", "masterrule": "Appendix B"},
    {"id": "email_smtp", "name": "Email (SMTP)", "category": "integrations", "description": "Transactional email config", "masterrule": "§11.3"},
    {"id": "mailpit", "name": "Mailpit", "category": "integrations", "description": "Local dev email inbox", "masterrule": "Appendix B"},
    {"id": "event_bus", "name": "Event Bus", "category": "infrastructure", "description": "Publish smoke test + Redis streams", "masterrule": "§12, ADR-005"},
    {"id": "websockets", "name": "WebSockets", "category": "observability", "description": "Live map WS route", "masterrule": "§16"},
    {"id": "redis", "name": "Redis", "category": "infrastructure", "description": "Cache, queues, event bus", "masterrule": "Appendix B"},
    {"id": "postgresql", "name": "PostgreSQL", "category": "infrastructure", "description": "Primary database ping", "masterrule": "Appendix B"},
    {"id": "readiness_probe", "name": "Readiness Probe", "category": "observability", "description": "/health/ready deep check", "masterrule": "§16"},
    {"id": "metrics_endpoint", "name": "Metrics", "category": "observability", "description": "Prometheus /metrics", "masterrule": "§16"},
    {"id": "worker_queue", "name": "Worker Queues", "category": "observability", "description": "Redis queue depths", "masterrule": "§16"},
    {"id": "notification_engine", "name": "Notification Engine", "category": "engines", "description": "Queue + delivery stats", "masterrule": "§11.3"},
    {"id": "pricing_engine", "name": "Pricing Engine", "category": "engines", "description": "Authoritative server pricing", "masterrule": "§11.1"},
    {"id": "billing_engine", "name": "Billing Engine", "category": "engines", "description": "Stripe billing lifecycle", "masterrule": "§11.2"},
    {"id": "orders_engine", "name": "Orders Engine", "category": "engines", "description": "Order mirror + lifecycle", "masterrule": "§10"},
    {"id": "crm_engine", "name": "CRM Engine", "category": "engines", "description": "Leads and pipeline", "masterrule": "§6"},
    {"id": "finance_engine", "name": "Finance Engine", "category": "engines", "description": "Invoices and payments admin", "masterrule": "§6"},
    {"id": "claims_engine", "name": "Claims Engine", "category": "engines", "description": "Claims workflow", "masterrule": "§6"},
    {"id": "support_engine", "name": "Support Engine", "category": "engines", "description": "Support tickets", "masterrule": "§6"},
    {"id": "layered_architecture", "name": "Layered Architecture", "category": "infrastructure", "description": "No direct Fleetbase from UI", "masterrule": "§3, ADR-007"},
    {"id": "stripe_webhook", "name": "Stripe Webhook Config", "category": "integrations", "description": "Webhook secret configured", "masterrule": "§14, ADR-006"},
    {"id": "scheduled_jobs", "name": "Scheduled Jobs", "category": "observability", "description": "Fleetbase retry queue health", "masterrule": "§16"},
]

TEST_IDS: tuple[str, ...] = tuple(t["id"] for t in TEST_CATALOG)

TEST_BY_ID: dict[str, dict[str, str]] = {t["id"]: t for t in TEST_CATALOG}

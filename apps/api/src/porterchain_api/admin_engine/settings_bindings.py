"""Settings binding registry — Wired vs Env vs Decorative (honesty over theater).

A control is editable in Admin Settings only when effect == "wired" or
"policy" (stored, explicitly not enforced yet). Env-owned and decorative
keys are status/deep-link only.
"""

from __future__ import annotations

from typing import Any, Literal

Effect = Literal["wired", "env", "policy", "decorative", "identity", "status"]

# Field-level search terms for Settings search index
FIELD_SEARCH: list[dict[str, str]] = [
    {"q": "sla instant delivery", "section": "booking", "label": "Instant delivery SLA (hours)"},
    {"q": "quote ttl", "section": "booking", "label": "Quote TTL (env)"},
    {"q": "downtown fee", "section": "pricing", "label": "Downtown surcharge"},
    {"q": "upper zone", "section": "pricing", "label": "Upper zone surcharge"},
    {"q": "hst tax", "section": "pricing", "label": "HST percent"},
    {"q": "fuel surcharge", "section": "pricing", "label": "Fuel surcharge"},
    {"q": "cargo van sprinter", "section": "vehicles", "label": "Vehicle classes"},
    {"q": "mfa clerk", "section": "authentication", "label": "MFA (Clerk)"},
    {"q": "fleetbase sso", "section": "fleetbase", "label": "Fleetbase SSO"},
    {"q": "stripe payments", "section": "stripe", "label": "Stripe"},
    {"q": "places google maps", "section": "google_maps", "label": "Google Places / tiles"},
]


SETTINGS_BINDINGS: list[dict[str, Any]] = [
    {
        "id": "dashboard",
        "storage_key": None,
        "effect": "status",
        "readers": ["AdminSettingsService.dashboard"],
        "ui_editable": False,
        "summary": "Readiness and recent audit — not a config store.",
    },
    {
        "id": "general",
        "storage_key": "settings_general",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Company identity stored for ops reference — not all fields bind portals yet.",
        "fields": [
            {"key": "company_name", "effect": "policy"},
            {"key": "support_email", "effect": "policy"},
            {"key": "timezone", "effect": "policy"},
        ],
    },
    {
        "id": "users",
        "storage_key": None,
        "effect": "identity",
        "readers": ["AdminSettingsService.list_platform_users", "StaffIdpService"],
        "ui_editable": True,
        "summary": "Staff / driver / merchant / customer directory and enrollment.",
    },
    {
        "id": "roles",
        "storage_key": None,
        "effect": "identity",
        "readers": ["permissions_catalog", "SpiceDB"],
        "ui_editable": False,
        "summary": "Read-only role → module catalog. SpiceDB is SoT.",
    },
    {
        "id": "authentication",
        "storage_key": None,
        "effect": "env",
        "readers": ["Clerk"],
        "ui_editable": False,
        "summary": "Session and MFA are owned by Clerk / staff IdP — not SystemConfig.",
    },
    {
        "id": "security",
        "storage_key": None,
        "effect": "env",
        "readers": ["portal_rate_limit_per_minute env", "Clerk"],
        "ui_editable": False,
        "summary": "Rate limits and password policy come from env / Clerk.",
    },
    {
        "id": "vehicles",
        "storage_key": "vehicle_types",
        "effect": "wired",
        "readers": ["quote eligibility", "pricing matrix keys"],
        "ui_editable": True,
        "summary": "Quote vehicle catalog — enabled flags gate retail quotes.",
        "fields": [
            {"key": "id", "effect": "wired"},
            {"key": "booking_enabled", "effect": "wired"},
            {"key": "retail_enabled", "effect": "wired"},
            {"key": "capacity_kg", "effect": "wired"},
        ],
    },
    {
        "id": "pricing",
        "storage_key": "pricing_gta_rate",
        "effect": "wired",
        "readers": ["PricingRepository._load_gta_rate_config", "porterchain_pricing.gta_rate"],
        "ui_editable": True,
        "summary": "GTA rate matrix — affects retail quotes immediately.",
        "related_keys": ["pricing_tax", "pricing_fuel", "pricing_rate_card"],
    },
    {
        "id": "coverage",
        "storage_key": "settings_coverage",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Service areas and delivery zones (policy store).",
    },
    {
        "id": "booking",
        "storage_key": "settings_booking",
        "effect": "wired",
        "readers": ["SlaMixin._instant_sla_hours"],
        "ui_editable": True,
        "summary": "Instant SLA is wired. Quote/draft TTL are env-owned (shown read-only).",
        "fields": [
            {"key": "instant_delivery_sla_hours", "effect": "wired"},
            {"key": "default_vehicle_class", "effect": "wired"},
            {"key": "default_currency", "effect": "policy"},
            {"key": "quote_ttl_minutes", "effect": "env"},
            {"key": "booking_draft_ttl_minutes", "effect": "env"},
        ],
    },
    {
        "id": "merchant",
        "storage_key": "settings_merchant",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Partner defaults — not enforced in onboarding runtime yet.",
    },
    {
        "id": "driver",
        "storage_key": "settings_driver",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Driver compliance policy — not enforced in runtime yet.",
    },
    {
        "id": "customer",
        "storage_key": "settings_customer",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Customer portal policy — not enforced in runtime yet.",
    },
    {
        "id": "finance",
        "storage_key": "settings_finance",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Invoice prefixes and tax defaults (policy).",
    },
    {
        "id": "documents",
        "storage_key": "settings_documents",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Upload limits policy.",
    },
    {
        "id": "claims",
        "storage_key": "settings_claims",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Claims SLA policy.",
    },
    {
        "id": "fleetbase",
        "storage_key": None,
        "effect": "status",
        "readers": ["fleetbase-adapter", "SSO"],
        "ui_editable": False,
        "summary": "Execution via adapter — open console with staff SSO.",
    },
    {
        "id": "stripe",
        "storage_key": None,
        "effect": "env",
        "readers": ["stripe_service"],
        "ui_editable": False,
        "summary": "Stripe secrets in Doppler/env only.",
    },
    {
        "id": "google_maps",
        "storage_key": None,
        "effect": "env",
        "readers": ["@porterchain/maps Places/tiles"],
        "ui_editable": False,
        "summary": "Places autocomplete and map tiles only — not a routing engine.",
    },
    {
        "id": "firebase",
        "storage_key": None,
        "effect": "env",
        "readers": ["notification_engine FCM"],
        "ui_editable": False,
        "summary": "FCM project via env.",
    },
    {
        "id": "storage",
        "storage_key": None,
        "effect": "env",
        "readers": [],
        "ui_editable": False,
        "summary": "Document storage via deployment volume / env.",
    },
    {
        "id": "channels",
        "storage_key": None,
        "effect": "status",
        "readers": ["SMTP env", "FCM", "/notifications"],
        "ui_editable": False,
        "summary": "Email / SMS / push status — templates live under Notifications.",
    },
    {
        "id": "automation",
        "storage_key": "settings_automation",
        "effect": "policy",
        "readers": [],
        "ui_editable": True,
        "summary": "Sync retry policy (policy store).",
    },
    {
        "id": "audit",
        "storage_key": None,
        "effect": "identity",
        "readers": ["AdminAuditLog"],
        "ui_editable": False,
        "summary": "Settings change audit trail.",
    },
    {
        "id": "backup",
        "storage_key": None,
        "effect": "identity",
        "readers": ["export/import"],
        "ui_editable": True,
        "summary": "Export/import Settings-owned SystemConfig keys.",
    },
]

# Logical section id → may write these SystemConfig keys via PUT
WRITABLE_LOGICAL_KEYS: frozenset[str] = frozenset(
    {
        "general",
        "vehicles",
        "pricing",
        "pricing_tax",
        "pricing_fuel",
        "pricing_rate_card",
        "coverage",
        "booking",
        "merchant",
        "driver",
        "customer",
        "finance",
        "documents",
        "claims",
        "automation",
    }
)

SECTION_ALIASES: dict[str, str] = {
    "service_areas": "coverage",
    "delivery_zones": "coverage",
    "email": "channels",
    "sms": "channels",
    "push": "channels",
    "notifications": "channels",
    "api_keys": "dashboard",
    "integrations": "dashboard",
    "branding": "general",
    "feature_flags": "dashboard",
    "logs": "backup",
    "developer": "backup",
    "maintenance": "backup",
    "operations": "dashboard",
    "support": "dashboard",
    "reports": "dashboard",
}


def bindings_payload() -> dict[str, Any]:
    return {
        "bindings": SETTINGS_BINDINGS,
        "aliases": SECTION_ALIASES,
        "writable": sorted(WRITABLE_LOGICAL_KEYS),
    }


def binding_for(section_id: str) -> dict[str, Any] | None:
    for b in SETTINGS_BINDINGS:
        if b["id"] == section_id:
            return b
    return None

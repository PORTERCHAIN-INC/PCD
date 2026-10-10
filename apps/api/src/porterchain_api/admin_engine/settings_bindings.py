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
    {"q": "liftgate weight extra stop rate card", "section": "pricing", "label": "Liftgate and weight card"},
    {"q": "price book parcel tiers small parcel handling", "section": "pricing", "label": "Price book"},
    {"q": "dedicated vehicle half day hourly retail fixed price", "section": "pricing", "label": "Price book"},
    {"q": "driver pay hourly wave block per stop", "section": "pricing", "label": "Driver pay plan"},
    {"q": "cargo van sprinter", "section": "vehicles", "label": "Vehicle classes"},
    {"q": "mfa passkey staff idp", "section": "authentication", "label": "Staff IdP (passkeys)"},
    {"q": "merchant approval auto activate", "section": "merchant", "label": "Merchant approval"},
    {"q": "alert budget staff push sla", "section": "channels", "label": "Staff push alert budget"},
    {"q": "dispatch day plan valhalla", "section": "dispatch", "label": "Dispatch"},
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
        "effect": "wired",
        "readers": [
            "booking_engine.invoice_service._invoice_event_payload",
            "billing_engine.driver_finance_service.statement_csv",
        ],
        "ui_editable": True,
        "summary": "Company name and support email appear on invoice events and driver statements. Timezone / hours remain ops reference.",
        "fields": [
            {"key": "company_name", "effect": "wired"},
            {"key": "support_email", "effect": "wired"},
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
        "readers": ["StaffIdpService", "staff_session", "Clerk portals"],
        "ui_editable": False,
        "summary": "Staff: first-party IdP (magic link + WebAuthn). Driver/merchant/customer: Clerk apps. Not SystemConfig.",
    },
    {
        "id": "security",
        "storage_key": None,
        "effect": "env",
        "readers": ["portal_rate_limit_per_minute env", "StaffIdpService", "Clerk portals"],
        "ui_editable": False,
        "summary": "API rate limits from env/Doppler. Staff session TTL in IdP; portal password policy in Clerk.",
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
        "summary": "GTA matrix, FSA, liftgate/weight card, tax, and fuel — quotes use these immediately.",
        "related_keys": [
            "pricing_tax",
            "pricing_fuel",
            "pricing_rate_card",
            "pricing_customer_distance",
            "pricing_book",
            "pricing_fsa_card",
            "driver_pay_plan",
        ],
        "write_role": "super_admin",
        "versioned_by": "pricing_version",
    },
    {
        "id": "driver_pay",
        "storage_key": "driver_pay_plan",
        "effect": "policy",
        "readers": ["porterchain_pricing.driver_pay.compute_driver_pay"],
        "ui_editable": True,
        "summary": "Driver pay plan (hourly / per stop / per route / wave block / hybrid). Stored and calculable; payouts still use the rate card.",
        "write_role": "super_admin",
    },
    {
        "id": "delivery_promise",
        "storage_key": "delivery_promise",
        "effect": "wired",
        "readers": ["integrations.shopify_carrier_rates.carrier_service_rates"],
        "ui_editable": True,
        "summary": "Checkout delivery promise: cut-offs, waves, operating days, holidays, FSA tiers. Off = fixed same-day window.",
        "write_role": "super_admin",
    },
    {
        "id": "marketing_site",
        "storage_key": "marketing_site",
        "effect": "wired",
        "readers": ["marketing_site.config.get_marketing_site"],
        "ui_editable": True,
        "summary": "Website marketing: hero copy A/B flag (off by default) and price-calculator limits.",
    },
    {
        "id": "coverage",
        "storage_key": "settings_coverage",
        "effect": "wired",
        "readers": ["booking_engine.quote_service.create_quote"],
        "ui_editable": True,
        "summary": "Active coverage cities gate retail quotes (empty areas = unrestricted).",
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
        "effect": "wired",
        "readers": [
            "merchant_engine.activation_service.approval_required",
            "merchant_engine.activation_service.trusted_channels_auto_activate",
        ],
        "ui_editable": True,
        "summary": "Approval gates are wired into onboarding. Payment terms / credit limit remain policy until billing reads them.",
        "fields": [
            {"key": "approval_required", "effect": "wired"},
            {"key": "auto_activate_trusted_channels", "effect": "wired"},
            {"key": "default_payment_terms", "effect": "policy"},
            {"key": "default_credit_limit_cents", "effect": "policy"},
        ],
    },
    {
        "id": "driver",
        "storage_key": "settings_driver",
        "effect": "wired",
        "readers": [
            "admin_engine.driver360_board.ai_payload",
            "driver_engine.background_check_service.status",
        ],
        "ui_editable": True,
        "summary": "Document expiry alert window and background-check required flag are wired into Driver 360 and verification status.",
        "fields": [
            {"key": "document_expiry_alert_days", "effect": "wired"},
            {"key": "background_check_required", "effect": "wired"},
        ],
    },
    {
        "id": "customer",
        "storage_key": "settings_customer",
        "effect": "wired",
        "readers": [
            "auth.customer_onboarding.evaluate_customer_onboarding",
            "routers.booking_drafts.create_booking_draft",
            "routers.quotes.post_booking",
        ],
        "ui_editable": True,
        "summary": "portal_enabled gates customer access; booking_self_service gates draft/booking create.",
        "fields": [
            {"key": "portal_enabled", "effect": "wired"},
            {"key": "booking_self_service", "effect": "wired"},
            {"key": "tracking_notifications", "effect": "policy"},
        ],
    },
    {
        "id": "finance",
        "storage_key": "settings_finance",
        "effect": "wired",
        "readers": [
            "billing_engine.invoice_numbering.allocate_invoice_number",
            "booking_engine.numbers.generate_receipt_number",
            "admin_engine.platform_settings.tax_cents_for_amount",
            "billing_engine.driver_finance_service._tax_summary",
        ],
        "ui_editable": True,
        "summary": "Invoice/receipt prefixes and default tax percent apply when invoices and tax estimates are generated.",
        "fields": [
            {"key": "invoice_number_prefix", "effect": "wired"},
            {"key": "receipt_number_prefix", "effect": "wired"},
            {"key": "default_tax_percent", "effect": "wired"},
            {"key": "tax_name", "effect": "wired"},
            {"key": "gst_hst_number", "effect": "wired"},
            {"key": "etransfer_email", "effect": "wired"},
            {"key": "etransfer_autodeposit", "effect": "wired"},
            {"key": "merchant_cycle_invoicing", "effect": "wired"},
            {"key": "tax_mode", "effect": "wired"},
            {"key": "default_tax_province", "effect": "wired"},
            {"key": "collect_qst", "effect": "wired"},
            {"key": "margin_floor_pct", "effect": "wired"},
            {"key": "margin_minutes_per_stop", "effect": "wired"},
            {"key": "interac_retention_years", "effect": "wired"},
        ],
    },
    {
        "id": "documents",
        "storage_key": "settings_documents",
        "effect": "wired",
        "readers": [
            "content_engine.blog_media.save_blog_image",
            "reporting.pod_export._max_artifact_bytes",
        ],
        "ui_editable": True,
        "summary": "Upload size and allowed types gate blog media and POD downloads. Retention days remain policy until a purge job exists.",
        "fields": [
            {"key": "max_file_size_mb", "effect": "wired"},
            {"key": "allowed_types", "effect": "wired"},
            {"key": "retention_days", "effect": "policy"},
        ],
    },
    {
        "id": "claims",
        "storage_key": "settings_claims",
        "effect": "wired",
        "readers": [
            "support_engine.claims_mutations.open_claim",
            "support_engine.claims_mutations.set_compensation",
        ],
        "ui_editable": True,
        "summary": "Investigation SLA stamps due-at on open; max compensation caps approved payouts.",
        "fields": [
            {"key": "investigation_sla_hours", "effect": "wired"},
            {"key": "max_compensation_cents", "effect": "wired"},
        ],
    },
    {
        "id": "dispatch",
        "storage_key": None,
        "effect": "status",
        "readers": ["dispatch_engine", "Valhalla", "Redis last_known"],
        "ui_editable": False,
        "summary": "PorterChain GPS, day plan (OR-Tools), and tracking.",
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
        "readers": [
            "SMTP env",
            "notification_engine.event_router",
            "notification_engine.preference_service",
            "FCM",
            "/notifications",
        ],
        "ui_editable": False,
        "summary": "Channel health + locked staff push alert budget. FCM secrets stay in env; templates under Notifications.",
    },
    {
        "id": "automation",
        "storage_key": "settings_automation",
        "effect": "wired",
        "readers": [
            "dispatch_engine.optimize_run_store",
            "worker processors.dispatch",
        ],
        "ui_editable": True,
        "summary": "Retry max attempts and first backoff apply to day-plan and dispatch worker jobs.",
        "fields": [
            {"key": "queue_retry_max", "effect": "wired"},
            {"key": "dispatch_retry_seconds", "effect": "wired"},
        ],
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
        "pricing_book",
        "driver_pay",
        "delivery_promise",
        "marketing_site",
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


_COMMERCIAL_REASON_KEYS: frozenset[str] = frozenset(
    {
        "vehicles",
        "pricing",
        "pricing_tax",
        "pricing_fuel",
        "pricing_rate_card",
        "pricing_book",
        "driver_pay",
        "delivery_promise",
        "booking",
        "merchant",
        "driver",
        "customer",
        "finance",
        "coverage",
        "documents",
        "claims",
        "automation",
        "general",
    }
)

# Logical config keys that require settings_commercial (vs settings_identity).
COMMERCIAL_WRITE_KEYS: frozenset[str] = frozenset(
    {
        "general",
        "vehicles",
        "pricing",
        "pricing_tax",
        "pricing_fuel",
        "pricing_rate_card",
        "pricing_book",
        "driver_pay",
        "delivery_promise",
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


def resolve_writable_config_key(key: str, *, reason: str | None = None) -> str:
    """Map a Settings UI logical key to a SystemConfig storage key (writable only)."""
    from porterchain_api.admin_engine.settings_service import CONFIG_KEYS

    if key not in WRITABLE_LOGICAL_KEYS and key not in CONFIG_KEYS:
        raise ValueError("unknown_config_key")
    if key not in WRITABLE_LOGICAL_KEYS:
        raise ValueError("config_key_not_writable")
    if key in _COMMERCIAL_REASON_KEYS and (not reason or not str(reason).strip()):
        raise ValueError("reason_required")
    return CONFIG_KEYS[key]


def bindings_payload() -> dict[str, Any]:
    return {
        "bindings": SETTINGS_BINDINGS,
        "aliases": SECTION_ALIASES,
        "writable": sorted(WRITABLE_LOGICAL_KEYS),
    }

from functools import lru_cache
from typing import Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from porterchain_shared.config.project_mode import (
    normalize_app_env,
    runtime_posture_from_settings,
)
from porterchain_shared.redis_health import is_local_env

_DEV_JWT_SECRETS = frozenset({"", "dev-sso-secret-change-in-production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = True
    # Interactive /docs, /redoc and /openapi.json. Always on in local/dev/test;
    # off in staging/production unless API_DOCS_ENABLED=true (readiness audit 2026-10-09).
    api_docs_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("api_docs_enabled", "API_DOCS_ENABLED"),
    )
    log_level: str = "debug"
    porterchain_api_url: str = "http://localhost:8001"
    database_url: str = "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain"
    database_url_replica: str = Field(
        default="",
        validation_alias=AliasChoices("database_url_replica", "DATABASE_URL_REPLICA"),
    )
    db_pool_size: int = Field(
        default=10,
        validation_alias=AliasChoices("db_pool_size", "DB_POOL_SIZE"),
    )
    db_max_overflow: int = Field(
        default=20,
        validation_alias=AliasChoices("db_max_overflow", "DB_MAX_OVERFLOW"),
    )
    db_pool_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("db_pool_timeout", "DB_POOL_TIMEOUT"),
    )
    db_pool_recycle: int = Field(
        default=1800,
        validation_alias=AliasChoices("db_pool_recycle", "DB_POOL_RECYCLE"),
    )
    quote_ttl_minutes: int = 30
    booking_draft_ttl_minutes: int = 1440
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004"

    clerk_jwks_url: str = ""
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_dev_bypass: bool = False

    # Per user-class Clerk apps (enterprise isolation). Empty → fall back to CLERK_* above.
    clerk_customer_secret_key: str = ""
    clerk_customer_jwks_url: str = ""
    clerk_customer_publishable_key: str = ""
    clerk_merchant_secret_key: str = ""
    clerk_merchant_jwks_url: str = ""
    clerk_merchant_publishable_key: str = ""
    clerk_admin_secret_key: str = ""
    clerk_admin_jwks_url: str = ""
    clerk_admin_publishable_key: str = ""
    clerk_driver_secret_key: str = ""
    clerk_driver_jwks_url: str = ""
    clerk_driver_publishable_key: str = ""

    # Phase 3 — optional JWT policy (empty = skip; required after unified Clerk cutover)
    clerk_audience: str = ""
    clerk_authorized_parties: str = ""  # comma-separated azp allowlist
    clerk_authorized_issuers: str = ""  # comma-separated iss allowlist
    # Phase 4 — Clerk webhook (Svix) signing secret
    clerk_webhook_signing_secret: str = ""
    # RETIRED — must stay false. platform_driver is the only supported layout.
    clerk_unified_mode: bool = False

    # SpiceDB (Zanzibar) — access-rules graph (not business data)
    # Default off until compose SpiceDB is up; set SPICEDB_ENABLED=true locally.
    spicedb_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("spicedb_enabled", "SPICEDB_ENABLED"),
    )
    spicedb_required: bool = Field(
        default=False,
        validation_alias=AliasChoices("spicedb_required", "SPICEDB_REQUIRED"),
    )
    spicedb_endpoint: str = Field(
        default="localhost:50051",
        validation_alias=AliasChoices("spicedb_endpoint", "SPICEDB_ENDPOINT"),
    )
    spicedb_preshared_key: str = Field(
        default="porterchain-spicedb-dev-key",
        validation_alias=AliasChoices("spicedb_preshared_key", "SPICEDB_PRESHARED_KEY"),
    )
    spicedb_use_memory: bool = Field(
        default=False,
        validation_alias=AliasChoices("spicedb_use_memory", "SPICEDB_USE_MEMORY"),
        description="Force in-process relationship store (tests / no compose SpiceDB).",
    )

    admin_portal_url: str = "http://localhost:3002"
    merchant_portal_url: str = "http://localhost:3001"
    driver_portal_url: str = "http://localhost:3003"
    customer_portal_url: str = "http://localhost:3004"
    website_url: str = "http://localhost:3000"
    # Interac e-Transfer inbox reader (billing@ on Zoho Mail). Off by default; env only —
    # the app password is never stored in the database or settings UI.
    interac_imap_enabled: bool = Field(
        default=False, validation_alias=AliasChoices("interac_imap_enabled", "INTERAC_IMAP_ENABLED")
    )
    interac_imap_host: str = Field(
        default="imappro.zoho.com", validation_alias=AliasChoices("interac_imap_host", "INTERAC_IMAP_HOST")
    )
    interac_imap_port: int = Field(
        default=993, validation_alias=AliasChoices("interac_imap_port", "INTERAC_IMAP_PORT")
    )
    interac_imap_user: str = Field(
        default="", validation_alias=AliasChoices("interac_imap_user", "INTERAC_IMAP_USER")
    )
    interac_imap_password: str = Field(
        default="", validation_alias=AliasChoices("interac_imap_password", "INTERAC_IMAP_PASSWORD")
    )
    interac_imap_folder: str = Field(
        default="INBOX", validation_alias=AliasChoices("interac_imap_folder", "INTERAC_IMAP_FOLDER")
    )
    interac_imap_lookback_days: int = Field(
        default=7, validation_alias=AliasChoices("interac_imap_lookback_days", "INTERAC_IMAP_LOOKBACK_DAYS")
    )
    # authserv-id of OUR receiving server's Authentication-Results header (Zoho: mx.zohomail.com).
    # Only that header is trusted; a sender can forge others.
    interac_authserv_id: str = Field(
        default="mx.zohomail.com", validation_alias=AliasChoices("interac_authserv_id", "INTERAC_AUTHSERV_ID")
    )
    billing_cycle_autorun_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("billing_cycle_autorun_enabled", "BILLING_CYCLE_AUTORUN_ENABLED"),
    )
    zeptomail_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("zeptomail_webhook_secret", "ZEPTOMAIL_WEBHOOK_SECRET"),
    )
    #: mailto half of List-Unsubscribe on marketing/CRM email (must be a monitored inbox).
    unsubscribe_mailbox: str = Field(
        default="unsubscribe@porterchain.com",
        validation_alias=AliasChoices("unsubscribe_mailbox", "UNSUBSCRIBE_MAILBOX"),
    )
    website_revalidate_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "website_revalidate_secret",
            "WEBSITE_REVALIDATE_SECRET",
        ),
        description="Shared secret for POST website /api/revalidate/blog after CMS publish.",
    )
    blog_media_public_base_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "blog_media_public_base_url",
            "BLOG_MEDIA_PUBLIC_BASE_URL",
        ),
        description=(
            "Optional CDN/origin prefix for blog media URLs (no trailing slash). "
            "When empty, uploads return relative /v1/public/blog/media/… paths."
        ),
    )
    blog_media_s3_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("blog_media_s3_endpoint", "BLOG_MEDIA_S3_ENDPOINT"),
        description="S3-compatible endpoint (e.g. https://ACCOUNT.r2.cloudflarestorage.com).",
    )
    blog_media_s3_bucket: str = Field(
        default="",
        validation_alias=AliasChoices("blog_media_s3_bucket", "BLOG_MEDIA_S3_BUCKET"),
    )
    blog_media_s3_access_key_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "blog_media_s3_access_key_id",
            "BLOG_MEDIA_S3_ACCESS_KEY_ID",
        ),
    )
    blog_media_s3_secret_access_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "blog_media_s3_secret_access_key",
            "BLOG_MEDIA_S3_SECRET_ACCESS_KEY",
        ),
    )
    blog_media_s3_region: str = Field(
        default="auto",
        validation_alias=AliasChoices("blog_media_s3_region", "BLOG_MEDIA_S3_REGION"),
    )
    blog_media_s3_prefix: str = Field(
        default="blog-media",
        validation_alias=AliasChoices("blog_media_s3_prefix", "BLOG_MEDIA_S3_PREFIX"),
        description="Object key prefix inside the bucket.",
    )
    public_ingest_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("public_ingest_api_key", "PUBLIC_INGEST_API_KEY"),
    )
    #: Meta Lead Ads / Instagram / Facebook / WhatsApp Cloud webhooks (Graph).
    meta_app_secret: str = Field(
        default="",
        validation_alias=AliasChoices("meta_app_secret", "META_APP_SECRET"),
    )
    meta_webhook_verify_token: str = Field(
        default="",
        validation_alias=AliasChoices(
            "meta_webhook_verify_token",
            "META_WEBHOOK_VERIFY_TOKEN",
        ),
    )
    #: Shared secret for Google Ads lead form / GBP message ingest (X-Lead-Webhook-Secret).
    google_lead_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "google_lead_webhook_secret",
            "GOOGLE_LEAD_WEBHOOK_SECRET",
        ),
    )
    #: Shared secret for LinkedIn / X / YouTube lead webhooks (X-Lead-Webhook-Secret).
    social_lead_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "social_lead_webhook_secret",
            "SOCIAL_LEAD_WEBHOOK_SECRET",
        ),
    )
    #: Meta Conversions API (CRM offline) — Lead ID attributed events.
    meta_capi_access_token: str = Field(
        default="",
        validation_alias=AliasChoices("meta_capi_access_token", "META_CAPI_ACCESS_TOKEN"),
    )
    meta_pixel_id: str = Field(
        default="",
        validation_alias=AliasChoices("meta_pixel_id", "META_PIXEL_ID", "NEXT_PUBLIC_META_PIXEL_ID"),
    )
    linkedin_capi_token: str = Field(
        default="",
        validation_alias=AliasChoices("linkedin_capi_token", "LINKEDIN_CAPI_TOKEN"),
    )
    #: urn:lla:llaPartnerConversion:{id} for LinkedIn Conversions API.
    linkedin_conversion_urn: str = Field(
        default="",
        validation_alias=AliasChoices(
            "linkedin_conversion_urn",
            "LINKEDIN_CONVERSION_URN",
        ),
    )
    #: JSON map territory key → admin_user id, e.g. {"ON":"...","GTA":"...","default":"..."}.
    lead_territory_map_json: str = Field(
        default="",
        validation_alias=AliasChoices("lead_territory_map_json", "LEAD_TERRITORY_MAP_JSON"),
    )
    #: JSON list of admin_user ids for round-robin when territory misses, e.g. ["id1","id2"].
    lead_round_robin_json: str = Field(
        default="",
        validation_alias=AliasChoices("lead_round_robin_json", "LEAD_ROUND_ROBIN_JSON"),
    )
    #: When true, Meta/Google/social webhooks enqueue to Redis WEBHOOKS (async ingest).
    lead_ingest_async: bool = Field(
        default=False,
        validation_alias=AliasChoices("lead_ingest_async", "LEAD_INGEST_ASYNC"),
    )
    #: JSON map channel → first-response SLA minutes, e.g. {"whatsapp":15,"default":60}.
    lead_sla_minutes_json: str = Field(
        default="",
        validation_alias=AliasChoices("lead_sla_minutes_json", "LEAD_SLA_MINUTES_JSON"),
    )
    #: Lead agent auto-send (welcome email / WhatsApp auto-reply / nurture steps).
    #: OFF by default since 2026-10: replies are drafted instantly and wait for a
    #: staff "Send". Set LEAD_AGENT_AUTO_SEND=true only as a deliberate opt-in.
    lead_agent_auto_send: bool = Field(
        default=False,
        validation_alias=AliasChoices("lead_agent_auto_send", "LEAD_AGENT_AUTO_SEND"),
    )
    #: Meta WhatsApp Cloud — System User token (whatsapp_business_messaging).
    meta_wa_access_token: str = Field(
        default="",
        validation_alias=AliasChoices("meta_wa_access_token", "META_WA_ACCESS_TOKEN"),
    )
    meta_wa_phone_number_id: str = Field(
        default="",
        validation_alias=AliasChoices("meta_wa_phone_number_id", "META_WA_PHONE_NUMBER_ID"),
    )
    meta_wa_business_account_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "meta_wa_business_account_id", "META_WA_BUSINESS_ACCOUNT_ID"
        ),
    )
    #: Optional JSON map PCD template key → Meta template name.
    meta_wa_template_map_json: str = Field(
        default="",
        validation_alias=AliasChoices(
            "meta_wa_template_map_json", "META_WA_TEMPLATE_MAP_JSON"
        ),
    )
    #: Extra recipients (comma separated) for security alerts; active super admins always get them.
    security_alert_email: str = Field(
        default="",
        validation_alias=AliasChoices("security_alert_email", "SECURITY_ALERT_EMAIL"),
    )
    #: Lead desk — owner alert email for new high-priority leads ("" = assignee only).
    lead_alert_email: str = Field(
        default="",
        validation_alias=AliasChoices("lead_alert_email", "LEAD_ALERT_EMAIL"),
    )
    #: SMS alert to LEAD_ALERT_SMS_TO — only when this is true AND Twilio is configured.
    lead_alert_sms_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("lead_alert_sms_enabled", "LEAD_ALERT_SMS_ENABLED"),
    )
    lead_alert_sms_to: str = Field(
        default="",
        validation_alias=AliasChoices("lead_alert_sms_to", "LEAD_ALERT_SMS_TO"),
    )
    #: Optional LLM polish for drafts / score notes (needs NVIDIA NIM key). Rules work without it.
    lead_ai_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("lead_ai_enabled", "LEAD_AI_ENABLED"),
    )
    #: Unified lead inbox — WhatsApp Cloud replies/inbound are OFF until this is true
    #: (and META_WA_ACCESS_TOKEN + META_WA_PHONE_NUMBER_ID are set).
    whatsapp_cloud_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("whatsapp_cloud_enabled", "WHATSAPP_CLOUD_ENABLED"),
    )
    #: Lead reply email: "" (disabled) | "zeptomail" (HTTPS API, SMTP_PASSWORD token)
    #: | "zoho_smtp" (Zoho Mail SMTP with an app password).
    lead_reply_email_transport: str = Field(
        default="",
        validation_alias=AliasChoices("lead_reply_email_transport", "LEAD_REPLY_EMAIL_TRANSPORT"),
    )
    lead_reply_from: str = Field(
        default="sales@porterchain.com",
        validation_alias=AliasChoices("lead_reply_from", "LEAD_REPLY_FROM"),
    )
    lead_reply_from_name: str = Field(
        default="PorterChain Sales",
        validation_alias=AliasChoices("lead_reply_from_name", "LEAD_REPLY_FROM_NAME"),
    )
    zoho_smtp_host: str = Field(
        default="smtp.zoho.com",
        validation_alias=AliasChoices("zoho_smtp_host", "ZOHO_SMTP_HOST"),
    )
    zoho_smtp_port: int = Field(
        default=465, validation_alias=AliasChoices("zoho_smtp_port", "ZOHO_SMTP_PORT")
    )
    #: Zoho mailbox login (e.g. sales@porterchain.com) — shared by SMTP + IMAP.
    zoho_mail_user: str = Field(
        default="", validation_alias=AliasChoices("zoho_mail_user", "ZOHO_MAIL_USER")
    )
    #: Zoho *app-specific* password (never the account password). Secret store only.
    zoho_mail_app_password: str = Field(
        default="",
        validation_alias=AliasChoices("zoho_mail_app_password", "ZOHO_MAIL_APP_PASSWORD"),
    )
    #: Inbound email → lead threads by polling the Zoho mailbox over IMAP (worker).
    lead_inbound_imap_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("lead_inbound_imap_enabled", "LEAD_INBOUND_IMAP_ENABLED"),
    )
    zoho_imap_host: str = Field(
        default="imap.zoho.com",
        validation_alias=AliasChoices("zoho_imap_host", "ZOHO_IMAP_HOST"),
    )
    zoho_imap_folder: str = Field(
        default="INBOX", validation_alias=AliasChoices("zoho_imap_folder", "ZOHO_IMAP_FOLDER")
    )
    #: HMAC secret for POST /v1/public/mail/inbound (forwarder / parse webhook).
    lead_inbound_email_secret: str = Field(
        default="",
        validation_alias=AliasChoices("lead_inbound_email_secret", "LEAD_INBOUND_EMAIL_SECRET"),
    )
    #: Unknown senders writing to sales@ create a new lead (else: only thread to existing).
    lead_inbound_email_create_leads: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "lead_inbound_email_create_leads", "LEAD_INBOUND_EMAIL_CREATE_LEADS"
        ),
    )
    #: Referral credit (cents) granted when a referred lead converts to merchant.
    referral_credit_cents: int = Field(
        default=25000,
        validation_alias=AliasChoices("referral_credit_cents", "REFERRAL_CREDIT_CENTS"),
    )
    #: Doppler service token — enables admin Lead Ingest settings → Doppler write.
    #: Note: DOPPLER_PROJECT / DOPPLER_CONFIG are reserved by Doppler CLI; keep defaults
    #: or set PORTERCHAIN_DOPPLER_PROJECT / PORTERCHAIN_DOPPLER_CONFIG.
    doppler_token: str = Field(
        default="",
        validation_alias=AliasChoices("doppler_token", "DOPPLER_TOKEN"),
    )
    doppler_project: str = Field(
        default="pcd",
        validation_alias=AliasChoices(
            "doppler_project",
            "PORTERCHAIN_DOPPLER_PROJECT",
        ),
    )
    doppler_config: str = Field(
        default="prd",
        validation_alias=AliasChoices(
            "doppler_config",
            "PORTERCHAIN_DOPPLER_CONFIG",
        ),
    )

    stripe_secret: str = ""
    stripe_webhook_secret: str = ""
    stripe_mock: bool = True
    #: P0 — Stripe Identity for driver license + selfie (Ontario onboarding).
    driver_identity_verification_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "driver_identity_verification_enabled",
            "DRIVER_IDENTITY_VERIFICATION_ENABLED",
        ),
    )
    driver_identity_return_url: str = Field(
        default="http://localhost:3003/profile?identity=return",
        validation_alias=AliasChoices(
            "driver_identity_return_url",
            "DRIVER_IDENTITY_RETURN_URL",
        ),
    )
    #: P1 — Checkr (Canada) background screening for drivers.
    driver_background_check_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "driver_background_check_enabled",
            "DRIVER_BACKGROUND_CHECK_ENABLED",
        ),
    )
    checkr_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("checkr_api_key", "CHECKR_API_KEY"),
    )
    checkr_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("checkr_webhook_secret", "CHECKR_WEBHOOK_SECRET"),
    )
    checkr_api_base_url: str = Field(
        default="https://api.checkr.com",
        validation_alias=AliasChoices("checkr_api_base_url", "CHECKR_API_BASE_URL"),
    )
    checkr_package_slug: str = Field(
        default="driver_pro",
        validation_alias=AliasChoices("checkr_package_slug", "CHECKR_PACKAGE_SLUG"),
    )
    checkr_mock: bool = Field(
        default=True,
        validation_alias=AliasChoices("checkr_mock", "CHECKR_MOCK"),
    )
    #: P2 — Ontario abstract attestation rules (no MTO scrape).
    driver_abstract_verification_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "driver_abstract_verification_enabled",
            "DRIVER_ABSTRACT_VERIFICATION_ENABLED",
        ),
    )
    driver_abstract_max_demerits: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "driver_abstract_max_demerits",
            "DRIVER_ABSTRACT_MAX_DEMERITS",
        ),
    )
    driver_abstract_allowed_classes: str = Field(
        default="G,A,B,C,D,E,F",
        validation_alias=AliasChoices(
            "driver_abstract_allowed_classes",
            "DRIVER_ABSTRACT_ALLOWED_CLASSES",
        ),
    )
    driver_compliance_expiry_sweep_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "driver_compliance_expiry_sweep_enabled",
            "DRIVER_COMPLIANCE_EXPIRY_SWEEP_ENABLED",
        ),
    )
    #: Platform fee taken on COD Connect charges (basis points, e.g. 500 = 5%).
    stripe_cod_platform_fee_bps: int = Field(
        default=500,
        validation_alias=AliasChoices(
            "stripe_cod_platform_fee_bps",
            "STRIPE_COD_PLATFORM_FEE_BPS",
        ),
    )
    stripe_connect_refresh_url: str = Field(
        default="http://localhost:3001/billing",
        validation_alias=AliasChoices(
            "stripe_connect_refresh_url",
            "STRIPE_CONNECT_REFRESH_URL",
        ),
    )
    stripe_connect_return_url: str = Field(
        default="http://localhost:3001/billing?connect=return",
        validation_alias=AliasChoices(
            "stripe_connect_return_url",
            "STRIPE_CONNECT_RETURN_URL",
        ),
    )

    dispatch_engine: str = Field(
        default="porterchain",
        validation_alias=AliasChoices("dispatch_engine", "DISPATCH_ENGINE"),
    )
    #: Deprecated driver_location_pings INSERT. Default off — last-known Redis is the registry.
    gps_write_ping_table: bool = Field(
        default=False,
        validation_alias=AliasChoices("gps_write_ping_table", "GPS_WRITE_PING_TABLE"),
    )
    sso_jwt_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "sso_jwt_secret",
            "SSO_JWT_SECRET",
            "PORTERCHAIN_SSO_JWT_SECRET",
        ),
    )
    jwt_secret: str = Field(
        default="dev-sso-secret-change-in-production",
        validation_alias=AliasChoices("jwt_secret", "JWT_SECRET"),
    )

    shopify_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("shopify_api_key", "SHOPIFY_API_KEY"),
    )
    shopify_api_secret: str = Field(
        default="",
        validation_alias=AliasChoices("shopify_api_secret", "SHOPIFY_API_SECRET"),
    )
    shopify_api_scopes: str = Field(
        default=(
            "read_orders,write_fulfillments,write_shipping,"
            "read_merchant_managed_fulfillment_orders,"
            "write_merchant_managed_fulfillment_orders,"
            "read_assigned_fulfillment_orders,"
            "write_assigned_fulfillment_orders,"
            # Requested at OAuth only when SHOPIFY_RETURNS_SCOPE_ENABLED (see shopify_urls.oauth_scopes).
            "read_returns"
        ),
        validation_alias=AliasChoices("shopify_api_scopes", "SHOPIFY_API_SCOPES"),
    )
    # 2026-10: carrierServiceCreate no longer auto-attaches to the General profile
    # (merchant adds the rate in Shipping and delivery); see shopify_one_click advisories.
    shopify_api_version: str = Field(
        default="2026-10",
        validation_alias=AliasChoices("shopify_api_version", "SHOPIFY_API_VERSION"),
    )
    # Request read_returns (returns/approve + returns/cancel via GraphQL webhooks).
    # Turn on only after an app version with that scope is released in the Partner Dashboard.
    shopify_returns_scope_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("shopify_returns_scope_enabled", "SHOPIFY_RETURNS_SCOPE_ENABLED"),
    )
    shopify_carrier_rate_limit_per_minute: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "shopify_carrier_rate_limit_per_minute",
            "SHOPIFY_CARRIER_RATE_LIMIT_PER_MINUTE",
        ),
    )
    shopify_webhook_rate_limit_per_minute: int = Field(
        default=300,
        validation_alias=AliasChoices(
            "shopify_webhook_rate_limit_per_minute",
            "SHOPIFY_WEBHOOK_RATE_LIMIT_PER_MINUTE",
        ),
    )
    #: When true, register Shopify FulfillmentService + FO request webhooks on install.
    #: Default off — orders/create + mid-flight tracking remain the live path until ops enables.
    shopify_fulfillment_service_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "shopify_fulfillment_service_enabled",
            "SHOPIFY_FULFILLMENT_SERVICE_ENABLED",
        ),
    )
    # 4-click embedded onboarding (confirm pickup → Go live). OFF in prod while App Review runs.
    shopify_four_click_onboarding_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "shopify_four_click_onboarding_enabled",
            "SHOPIFY_FOUR_CLICK_ONBOARDING_ENABLED",
        ),
    )

    retail_checkout_success_url: str = "http://localhost:3000/en/book/success"
    retail_checkout_cancel_url: str = "http://localhost:3000/en/book/continue"
    customer_checkout_success_url: str = ""
    customer_checkout_cancel_url: str = ""

    phase2_crm: bool = Field(
        default=False,
        validation_alias=AliasChoices("phase2_crm", "PORTERCHAIN_PHASE2_CRM"),
    )
    # RETIRED — Route Center tables/code removed; keep flag for env compat (always treat as off).
    phase2_route_center: bool = Field(
        default=False,
        validation_alias=AliasChoices("phase2_route_center", "PORTERCHAIN_PHASE2_ROUTE_CENTER"),
    )
    phase2_ai_dispatch: bool = Field(
        default=False,
        validation_alias=AliasChoices("phase2_ai_dispatch", "PORTERCHAIN_PHASE2_AI_DISPATCH"),
    )
    phase2_analytics: bool = Field(
        default=False,
        validation_alias=AliasChoices("phase2_analytics", "PORTERCHAIN_PHASE2_ANALYTICS"),
    )
    phase2_intelligence: bool = Field(
        default=False,
        validation_alias=AliasChoices("phase2_intelligence", "PORTERCHAIN_PHASE2_INTELLIGENCE"),
    )
    oauth_third_party_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("oauth_third_party_enabled", "PORTERCHAIN_OAUTH_THIRD_PARTY_ENABLED"),
    )

    # Server pricing: max drift allowed vs client website estimate (2% or $1 CAD).
    pricing_client_tolerance_cents: int = 100
    pricing_client_tolerance_percent: float = 0.02
    enable_driver_auto_reoptimize: bool = True
    portal_rate_limit_per_minute: int = Field(
        default=120,
        validation_alias=AliasChoices("portal_rate_limit_per_minute", "PORTAL_RATE_LIMIT_PER_MINUTE"),
    )
    public_rate_limit_per_minute: int = Field(
        default=120,
        validation_alias=AliasChoices("public_rate_limit_per_minute", "PUBLIC_RATE_LIMIT_PER_MINUTE"),
    )
    sentry_dsn: str = Field(
        default="",
        validation_alias=AliasChoices("sentry_dsn", "SENTRY_DSN"),
    )
    # Driver Android/iOS store gate — exposed on GET /health/status (no auth).
    driver_app_min_version: str = Field(
        default="1.0.0",
        validation_alias=AliasChoices("driver_app_min_version", "DRIVER_APP_MIN_VERSION"),
    )
    driver_app_force_update: bool = Field(
        default=False,
        validation_alias=AliasChoices("driver_app_force_update", "DRIVER_APP_FORCE_UPDATE"),
    )
    driver_app_store_url_ios: str = Field(
        default="https://apps.apple.com/app/porterchain-driver",
        validation_alias=AliasChoices("driver_app_store_url_ios", "DRIVER_APP_STORE_URL_IOS"),
    )
    driver_app_store_url_android: str = Field(
        default="https://play.google.com/store/apps/details?id=com.porterchain.PCD",
        validation_alias=AliasChoices(
            "driver_app_store_url_android", "DRIVER_APP_STORE_URL_ANDROID"
        ),
    )
    driver_app_update_message: str = Field(
        default="A required update is available for the Porterchain Driver app.",
        validation_alias=AliasChoices("driver_app_update_message", "DRIVER_APP_UPDATE_MESSAGE"),
    )

    @field_validator("app_env", mode="before")
    @classmethod
    def normalize_project_app_env(cls, value: object) -> str:
        return normalize_app_env(str(value) if value is not None else "")

    @field_validator("database_url")
    @classmethod
    def reject_sqlite(cls, value: str) -> str:
        if value.startswith("sqlite"):
            raise ValueError(
                "SQLite is not supported for Porterchain. "
                "Use postgresql+psycopg://user:pass@host:5432/dbname"
            )
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg:// for Porterchain")
        return value

    @field_validator("database_url_replica")
    @classmethod
    def validate_replica_url(cls, value: str) -> str:
        if not value:
            return value
        if value.startswith("sqlite"):
            raise ValueError("DATABASE_URL_REPLICA must use postgresql+psycopg://")
        if not value.startswith("postgresql"):
            raise ValueError("DATABASE_URL_REPLICA must use postgresql+psycopg://")
        return value

    @model_validator(mode="after")
    def derive_customer_checkout_urls(self) -> Self:
        base = self.customer_portal_url.rstrip("/")
        if not self.customer_checkout_success_url:
            object.__setattr__(self, "customer_checkout_success_url", f"{base}/book/success")
        if not self.customer_checkout_cancel_url:
            object.__setattr__(self, "customer_checkout_cancel_url", f"{base}/book")
        return self

    @model_validator(mode="after")
    def reject_dev_jwt_secret_in_production(self) -> Self:
        if not is_local_env(self.app_env) and self.jwt_secret in _DEV_JWT_SECRETS:
            raise ValueError(
                "JWT_SECRET must be set to a secure non-default value when APP_ENV is not local "
                "(generate with: openssl rand -hex 32)"
            )
        return self

    @model_validator(mode="after")
    def reject_retired_clerk_unified_mode(self) -> Self:
        if self.clerk_unified_mode:
            raise ValueError(
                "CLERK_UNIFIED_MODE is retired — use CLERK_MODE=platform_driver "
                "(Platform + distinct Driver). Set CLERK_UNIFIED_MODE=false."
            )
        return self

    @model_validator(mode="after")
    def require_clerk_in_production(self) -> Self:
        if is_local_env(self.app_env):
            return self
        from porterchain_api.auth.clerk_config_audit import production_clerk_errors

        errors = production_clerk_errors(self)
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        # Local LAN access (Next "Network" URL) must be allowed or browsers report Failed to fetch.
        if is_local_env(self.app_env):
            for port in (3000, 3001, 3002, 3003, 3004):
                for host in ("localhost", "127.0.0.1"):
                    origin = f"http://{host}:{port}"
                    if origin not in origins:
                        origins.append(origin)
        return origins

    @property
    def allow_stripe_mock(self) -> bool:
        """Stripe mock checkout and mock-complete are development mode only (masterrule §14)."""
        return runtime_posture_from_settings(self).stripe_mock_allowed

    @property
    def runtime_posture(self) -> dict:
        """Boot-time project mode + derived gates (read-only for Admin / metrics)."""
        return runtime_posture_from_settings(self).as_dict()

    @property
    def phase2_flags(self) -> dict[str, bool]:
        from porterchain_shared.config.phase2 import phase2_flags_from_mapping

        return phase2_flags_from_mapping(self.model_dump()).as_dict()


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from typing import Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from porterchain_shared.redis_health import is_local_env

_DEV_JWT_SECRETS = frozenset({"", "dev-sso-secret-change-in-production"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = True
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
    public_ingest_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("public_ingest_api_key", "PUBLIC_INGEST_API_KEY"),
    )

    stripe_secret: str = ""
    stripe_webhook_secret: str = ""
    stripe_mock: bool = True

    fleetbase_api_url: str = "http://localhost:8000"
    fleetbase_api_key: str = ""
    fleetbase_webhook_secret: str = ""
    fleetbase_dispatch_bridge: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "fleetbase_dispatch_bridge",
            "FLEETBASE_DISPATCH_BRIDGE",
            "PORTERCHAIN_FLEETBASE_DISPATCH_BRIDGE",
        ),
    )
    fleetbase_default_company_uuid: str = Field(
        default="",
        validation_alias=AliasChoices(
            "fleetbase_default_company_uuid",
            "PORTERCHAIN_FLEETBASE_DEFAULT_COMPANY_UUID",
        ),
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
    sso_token_ttl_seconds: int = 300
    fleetbase_console_url: str = "http://localhost:4200"
    fleetbase_sso_enabled: bool = True

    retail_checkout_success_url: str = "http://localhost:3000/en/book/success"
    retail_checkout_cancel_url: str = "http://localhost:3000/en/book/continue"
    customer_checkout_success_url: str = ""
    customer_checkout_cancel_url: str = ""

    phase2_crm: bool = Field(
        default=False,
        validation_alias=AliasChoices("phase2_crm", "PORTERCHAIN_PHASE2_CRM"),
    )
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
    sentry_dsn: str = Field(
        default="",
        validation_alias=AliasChoices("sentry_dsn", "SENTRY_DSN"),
    )

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
    def require_fleetbase_secrets_when_bridge_enabled(self) -> Self:
        if not is_local_env(self.app_env) and self.fleetbase_dispatch_bridge:
            missing: list[str] = []
            if not self.fleetbase_api_key:
                missing.append("FLEETBASE_API_KEY")
            if not self.fleetbase_webhook_secret:
                missing.append("FLEETBASE_WEBHOOK_SECRET")
            if not self.fleetbase_default_company_uuid:
                missing.append("FLEETBASE_DEFAULT_COMPANY_UUID")
            if missing:
                raise ValueError(
                    "FLEETBASE_DISPATCH_BRIDGE=true in production requires: "
                    + ", ".join(missing)
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
        """Stripe mock checkout and mock-complete are local dev only (masterrule §14)."""
        if self.app_env != "local":
            return False
        return self.stripe_mock or not self.stripe_secret

    @property
    def phase2_flags(self) -> dict[str, bool]:
        from porterchain_shared.config.phase2 import phase2_flags_from_mapping

        return phase2_flags_from_mapping(self.model_dump()).as_dict()


@lru_cache
def get_settings() -> Settings:
    return Settings()

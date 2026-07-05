from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = True
    log_level: str = "debug"
    porterchain_api_url: str = "http://localhost:8001"
    database_url: str = "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
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

    admin_portal_url: str = "http://localhost:3002"
    merchant_portal_url: str = "http://localhost:3001"
    driver_portal_url: str = "http://localhost:3003"
    customer_portal_url: str = "http://localhost:3004"
    website_url: str = "http://localhost:3000"

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

    sso_jwt_secret: str = ""
    jwt_secret: str = "dev-sso-secret-change-in-production"
    sso_token_ttl_seconds: int = 300
    fleetbase_console_url: str = "http://localhost:4200"
    fleetbase_sso_enabled: bool = True

    retail_checkout_success_url: str = "http://localhost:3000/en/book/success"
    retail_checkout_cancel_url: str = "http://localhost:3000/en/book/continue"

    # Server pricing: max drift allowed vs client website estimate (2% or $1 CAD).
    pricing_client_tolerance_cents: int = 100
    pricing_client_tolerance_percent: float = 0.02
    enable_driver_auto_reoptimize: bool = True
    portal_rate_limit_per_minute: int = Field(
        default=120,
        validation_alias=AliasChoices("portal_rate_limit_per_minute", "PORTAL_RATE_LIMIT_PER_MINUTE"),
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allow_stripe_mock(self) -> bool:
        """Stripe mock checkout and mock-complete are local dev only (masterrule §14)."""
        if self.app_env != "local":
            return False
        return self.stripe_mock or not self.stripe_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()

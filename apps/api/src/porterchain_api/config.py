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
    def require_clerk_in_production(self) -> Self:
        if is_local_env(self.app_env) or self.clerk_dev_bypass:
            return self
        from porterchain_api.auth.clerk_registry import (
            ALL_CLERK_APP_KINDS,
            clerk_configuration_mode,
        )

        mode = clerk_configuration_mode(self)
        if mode in ("enterprise", "legacy"):
            return self
        missing = ", ".join(f"clerk_{k}" for k in ALL_CLERK_APP_KINDS)
        raise ValueError(
            "Production requires Clerk: set all CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_* "
            f"keys or legacy CLERK_SECRET_KEY + CLERK_JWKS_URL (missing: {missing})"
        )

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

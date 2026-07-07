"""Centralized platform configuration — single source for integration env vars."""

from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    """Shared settings consumed by API, worker, and service modules."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = True
    log_level: str = "info"

    # Porterchain database (owned data)
    database_url: str = "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain"

    # Redis — cache, events, queues
    redis_url: str = "redis://localhost:6379/0"

    # Clerk — sole authentication provider
    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    clerk_dev_bypass: bool = False

    # Stripe
    stripe_secret: str = ""
    stripe_webhook_secret: str = ""
    stripe_mock: bool = True

    # Fleetbase — internal logistics engine only
    fleetbase_api_url: str = "http://localhost:8000"
    fleetbase_api_key: str = ""
    fleetbase_dispatch_bridge: bool = False
    fleetbase_default_company_uuid: str = ""
    fleetbase_webhook_secret: str = ""
    fleetbase_console_url: str = "http://localhost:4200"
    fleetbase_sso_enabled: bool = True

    # SSO — Porterchain JWT for Fleetbase trust
    sso_jwt_secret: str = ""
    sso_token_ttl_seconds: int = 300

    # Maps / routing
    google_maps_api_key: str = ""
    valhalla_url: str = Field(
        default="http://localhost:8002",
        validation_alias=AliasChoices("valhalla_url", "VALHALLA_BASE_URL", "VALHALLA_BASE_URI"),
    )
    osrm_url: str = Field(
        default="",
        validation_alias=AliasChoices("osrm_url", "OSRM_HOST", "OSRM_URL"),
    )
    routing_engine: str = "valhalla"

    # Firebase push
    firebase_project_id: str = ""
    firebase_credentials_json: str = ""
    firebase_credentials_path: str = Field(
        default="",
        validation_alias=AliasChoices("firebase_credentials_path", "FIREBASE_CREDENTIALS_PATH"),
    )
    firebase_web_vapid_key: str = Field(
        default="",
        validation_alias=AliasChoices("firebase_web_vapid_key", "FIREBASE_WEB_VAPID_KEY"),
    )
    push_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("push_enabled", "PORTERCHAIN_PUSH_ENABLED", "PORTERCHAIN_DRIVER_PUSH_ENABLED"),
    )
    push_send: bool = Field(
        default=True,
        validation_alias=AliasChoices("push_send", "PORTERCHAIN_PUSH_SEND", "PORTERCHAIN_DRIVER_PUSH_SEND"),
    )
    notification_max_retries: int = Field(default=5, validation_alias=AliasChoices("notification_max_retries", "NOTIFICATION_MAX_RETRIES"))

    # SMTP (Zoho Mail — transactional; auth is Clerk-only)
    smtp_host: str = Field(default="", validation_alias=AliasChoices("smtp_host", "MAIL_HOST"))
    smtp_port: int = Field(default=465, validation_alias=AliasChoices("smtp_port", "MAIL_PORT"))
    smtp_user: str = Field(default="", validation_alias=AliasChoices("smtp_user", "MAIL_USERNAME"))
    smtp_password: str = Field(default="", validation_alias=AliasChoices("smtp_password", "MAIL_PASSWORD"))
    smtp_from: str = Field(
        default="ops@porterchain.com",
        validation_alias=AliasChoices("smtp_from", "MAIL_FROM_ADDRESS"),
    )
    smtp_from_sales: str = Field(
        default="",
        validation_alias=AliasChoices("smtp_from_sales", "MAIL_FROM_ADDRESS2", "MAIL_FROM_SALES"),
    )
    smtp_from_personal: str = Field(
        default="",
        validation_alias=AliasChoices("smtp_from_personal", "MAIL_FROM_ADDRESS3"),
    )
    smtp_from_name: str = Field(
        default="Porterchain",
        validation_alias=AliasChoices("smtp_from_name", "MAIL_FROM_NAME"),
    )

    # Zoho Calendar (CRM meetings / follow-ups)
    zoho_calendar_client_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "zoho_calendar_client_id",
            "ZOHO_CALENDAR_CLIENT_ID",
            "ZOHO_CALANDER_API",
        ),
    )
    zoho_calendar_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices(
            "zoho_calendar_client_secret",
            "ZOHO_CALENDAR_CLIENT_SECRET",
            "ZOHO_CALANDER_API_SECRET",
        ),
    )
    zoho_calendar_refresh_token: str = Field(
        default="",
        validation_alias=AliasChoices(
            "zoho_calendar_refresh_token",
            "ZOHO_CALENDAR_REFRESH_TOKEN",
            "ZOHO_CALANDER_API_OPERATION",
        ),
    )
    zoho_calendar_accounts_url: str = Field(
        default="https://accounts.zohocloud.ca",
        validation_alias=AliasChoices("zoho_calendar_accounts_url", "ZOHO_CALENDAR_ACCOUNTS_URL"),
    )
    zoho_calendar_api_base: str = Field(
        default="https://calendar.zoho.ca/api/v1",
        validation_alias=AliasChoices("zoho_calendar_api_base", "ZOHO_CALENDAR_API_BASE"),
    )
    zoho_calendar_uid: str = Field(
        default="",
        validation_alias=AliasChoices("zoho_calendar_uid", "ZOHO_CALENDAR_UID"),
    )
    zoho_calendar_timezone: str = Field(
        default="America/Toronto",
        validation_alias=AliasChoices("zoho_calendar_timezone", "ZOHO_CALENDAR_TIMEZONE"),
    )

    # JWT session (driver API — Porterchain-issued refresh tokens)
    jwt_secret: str = ""
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_days: int = 30

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_local(self) -> bool:
        return self.app_env.lower() in ("local", "development", "dev", "test")

    @property
    def zoho_calendar_configured(self) -> bool:
        return bool(
            self.zoho_calendar_client_id
            and self.zoho_calendar_client_secret
            and self.zoho_calendar_refresh_token
        )

    def smtp_from_for(self, alias: str | None = None) -> str:
        """Resolve transactional From address — ops (default), sales, or personal."""
        key = (alias or "ops").lower()
        if key in ("sales", "crm"):
            return self.smtp_from_sales or self.smtp_from
        if key in ("personal", "ravi"):
            return self.smtp_from_personal or self.smtp_from
        return self.smtp_from


@lru_cache
def get_platform_settings() -> PlatformSettings:
    return PlatformSettings()

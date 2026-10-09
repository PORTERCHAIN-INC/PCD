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

    # Retired Fleetbase bridge keys (nullable until later drop — keep off)
    fleetbase_api_url: str = ""
    fleetbase_api_key: str = ""
    fleetbase_dispatch_bridge: bool = False
    fleetbase_default_company_uuid: str = ""
    fleetbase_webhook_secret: str = ""
    fleetbase_console_url: str = ""
    fleetbase_sso_enabled: bool = False

    # Maps / routing
    google_maps_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "google_maps_api_key",
            "GOOGLE_MAPS_API_KEY",
            "GOOGLE_MAPS_SERVER_API_KEY",
        ),
    )
    valhalla_url: str = Field(
        default="http://localhost:8002",
        validation_alias=AliasChoices("valhalla_url", "VALHALLA_BASE_URL", "VALHALLA_BASE_URI"),
    )
    osrm_url: str = Field(
        default="http://localhost:5000",
        validation_alias=AliasChoices("osrm_url", "OSRM_HOST", "OSRM_URL"),
    )
    osrm_allow_public_demo: bool = Field(
        default=False,
        validation_alias=AliasChoices("osrm_allow_public_demo", "OSRM_ALLOW_PUBLIC_DEMO"),
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
    sms_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("sms_enabled", "PORTERCHAIN_SMS_ENABLED"),
    )
    sms_provider: str = Field(
        default="",
        validation_alias=AliasChoices("sms_provider", "PORTERCHAIN_SMS_PROVIDER"),
    )
    twilio_account_sid: str = Field(
        default="",
        validation_alias=AliasChoices("twilio_account_sid", "TWILIO_ACCOUNT_SID"),
    )
    twilio_auth_token: str = Field(
        default="",
        validation_alias=AliasChoices("twilio_auth_token", "TWILIO_AUTH_TOKEN"),
    )
    twilio_from_number: str = Field(
        default="",
        validation_alias=AliasChoices("twilio_from_number", "TWILIO_FROM_NUMBER"),
    )

    # NVIDIA NIM (OpenAI-compatible) — intelligence_engine only; not on pay path
    nvidia_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("nvidia_api_key", "NVIDIA_API_KEY", "NGC_API_KEY"),
    )
    nvidia_api_base: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        validation_alias=AliasChoices("nvidia_api_base", "NVIDIA_API_BASE"),
    )
    nvidia_model: str = Field(
        default="openai/gpt-oss-20b",
        validation_alias=AliasChoices("nvidia_model", "NVIDIA_MODEL"),
    )
    # cuOpt Catalog / self-host OptimizedRouting (shadow only)
    nvidia_cuopt_url: str = Field(
        default="https://optimize.api.nvidia.com/v1/nvidia/cuopt",
        validation_alias=AliasChoices("nvidia_cuopt_url", "NVIDIA_CUOPT_URL"),
    )

    # SMTP / ZeptoMail transactional (auth is Clerk-only)
    smtp_host: str = Field(default="", validation_alias=AliasChoices("smtp_host", "MAIL_HOST"))
    smtp_port: int = Field(default=587, validation_alias=AliasChoices("smtp_port", "MAIL_PORT"))
    smtp_user: str = Field(default="", validation_alias=AliasChoices("smtp_user", "MAIL_USERNAME"))
    smtp_password: str = Field(default="", validation_alias=AliasChoices("smtp_password", "MAIL_PASSWORD"))
    smtp_from: str = Field(
        default="noreply@porterchain.com",
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
    # Comma-separated. When set, staff email (including push fallback) goes only to these addresses.
    ops_watch_emails: str = Field(
        default="",
        validation_alias=AliasChoices("ops_watch_emails", "OPS_WATCH_EMAILS"),
    )
    # auto | smtp | https — auto uses HTTPS for ZeptoMail in non-local envs (DO blocks SMTP).
    mail_transport: str = Field(
        default="auto",
        validation_alias=AliasChoices("mail_transport", "MAIL_TRANSPORT"),
    )
    zeptomail_api_url: str = Field(
        default="https://api.zeptomail.ca/v1.1/email",
        validation_alias=AliasChoices("zeptomail_api_url", "ZEPTOMAIL_API_URL"),
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

    def smtp_from_for(self, alias: str | None = None) -> str:
        """Resolve transactional From address — ops (default), sales, or personal."""
        key = (alias or "ops").lower()
        if key in ("sales", "crm"):
            return self.smtp_from_sales or self.smtp_from
        if key in ("personal", "ravi"):
            return self.smtp_from_personal or self.smtp_from
        return self.smtp_from

    def resolve_mail_transport(self) -> str:
        """Return ``smtp`` or ``https`` for outbound transactional mail."""
        explicit = (self.mail_transport or "auto").strip().lower()
        if explicit in {"smtp", "https"}:
            return explicit
        if self.is_local:
            return "smtp"
        host = (self.smtp_host or "").lower()
        if "zeptomail" in host:
            return "https"
        return "smtp"


@lru_cache
def get_platform_settings() -> PlatformSettings:
    return PlatformSettings()

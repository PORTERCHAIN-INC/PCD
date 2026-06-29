"""Centralized platform configuration — single source for integration env vars."""

from functools import lru_cache

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
    valhalla_url: str = "http://localhost:8002"
    osrm_url: str = ""
    routing_engine: str = "valhalla"

    # Firebase push
    firebase_project_id: str = ""
    firebase_credentials_json: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@porterchain.com"

    # SMS (Twilio)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # JWT session (driver API — Porterchain-issued refresh tokens)
    jwt_secret: str = ""
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_days: int = 30

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_platform_settings() -> PlatformSettings:
    return PlatformSettings()

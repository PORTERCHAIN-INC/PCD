from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    app_debug: bool = True
    log_level: str = "debug"
    porterchain_api_url: str = "http://localhost:8001"
    database_url: str = "sqlite:///./porterchain.db"
    quote_ttl_minutes: int = 30
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003"

    clerk_jwks_url: str = ""
    clerk_secret_key: str = ""
    clerk_publishable_key: str = ""
    clerk_dev_bypass: bool = True

    stripe_secret: str = ""
    stripe_webhook_secret: str = ""
    stripe_mock: bool = True

    fleetbase_api_url: str = "http://localhost:8000"
    fleetbase_api_key: str = ""
    fleetbase_webhook_secret: str = ""
    fleetbase_dispatch_bridge: bool = True
    fleetbase_default_company_uuid: str = ""

    sso_jwt_secret: str = ""
    jwt_secret: str = "dev-sso-secret-change-in-production"
    sso_token_ttl_seconds: int = 300
    fleetbase_console_url: str = "http://localhost:4200"
    fleetbase_sso_enabled: bool = True

    retail_checkout_success_url: str = "http://localhost:3000/en/book/success"
    retail_checkout_cancel_url: str = "http://localhost:3000/en/book/continue"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

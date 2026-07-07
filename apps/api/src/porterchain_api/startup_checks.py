"""Fail-fast validation of required configuration / Doppler-managed secrets.

Runs once at API startup so the process refuses to boot with incomplete
production configuration, surfacing *every* missing secret at once (instead of
failing lazily deep inside a request path). Local/dev (`APP_ENV=local`) is a
no-op so developer machines and CI are unaffected.

The required set is intentionally aligned with what production deployment
already expects (``infrastructure/deploy/sync-secrets.sh`` and the validators
in :mod:`porterchain_api.config`) so this adds fail-fast reporting without
tightening the contract.
"""

from __future__ import annotations

import logging

from porterchain_shared.redis_health import is_local_env

from porterchain_api.config import _DEV_JWT_SECRETS, Settings

logger = logging.getLogger(__name__)

# Dev-only default DB URLs that must never be used outside local.
_LOCAL_DEFAULT_DB_URLS = frozenset(
    {
        "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
        "postgresql://porterchain:porterchain@localhost:5432/porterchain",
    }
)


class MissingConfigError(RuntimeError):
    """Raised at startup when required production configuration is missing."""


def _clerk_configured(settings: Settings) -> bool:
    # Imported lazily to avoid a circular import at module load.
    from porterchain_api.auth.clerk_registry import clerk_configuration_mode

    return clerk_configuration_mode(settings) in ("enterprise", "legacy")


def collect_missing_required(settings: Settings) -> list[str]:
    """Return the list of required secret names that are missing/invalid.

    Empty for local/dev. For non-local environments, reports secrets that the
    production stack requires to operate correctly.
    """
    if is_local_env(settings.app_env):
        return []

    missing: list[str] = []

    if not settings.database_url or settings.database_url in _LOCAL_DEFAULT_DB_URLS:
        missing.append("DATABASE_URL")

    # JWT signing secret for driver/SSO tokens (config also guards this).
    if settings.jwt_secret in _DEV_JWT_SECRETS:
        missing.append("JWT_SECRET")

    # Stripe — required by the production deploy secret sync.
    if not settings.stripe_secret.strip():
        missing.append("STRIPE_SECRET")
    if not settings.stripe_webhook_secret.strip():
        missing.append("STRIPE_WEBHOOK_SECRET")

    # Clerk — legacy (CLERK_SECRET_KEY + CLERK_JWKS_URL) or enterprise (4 apps).
    if not _clerk_configured(settings):
        missing.append(
            "CLERK_SECRET_KEY+CLERK_JWKS_URL "
            "(or CLERK_{CUSTOMER,MERCHANT,ADMIN,DRIVER}_SECRET_KEY+_JWKS_URL)"
        )

    return missing


def validate_required_settings(settings: Settings) -> None:
    """Raise :class:`MissingConfigError` if required config is missing.

    No-op for ``APP_ENV=local``. Call this at startup to fail fast.
    """
    missing = collect_missing_required(settings)
    if missing:
        raise MissingConfigError(
            f"Refusing to start: missing required configuration for APP_ENV={settings.app_env!r}. "
            "Set these via Doppler (see docs/DOPPLER_AUDIT.md): " + ", ".join(missing)
        )
    logger.info("Startup config validation passed for APP_ENV=%s", settings.app_env)

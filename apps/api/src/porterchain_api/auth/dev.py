"""Local-only auth bypass helpers — never active in staging/production."""

from __future__ import annotations

from porterchain_api.config import Settings


def allow_auth_dev_bypass(settings: Settings) -> bool:
    """True only when explicitly running local dev with CLERK_DEV_BYPASS=true."""
    return settings.app_env == "local" and settings.clerk_dev_bypass

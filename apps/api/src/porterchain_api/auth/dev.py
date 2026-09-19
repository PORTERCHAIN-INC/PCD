"""Local-only auth bypass helpers — never active in staging/production."""

from __future__ import annotations

from porterchain_api.config import Settings
from porterchain_shared.config.project_mode import ProjectMode, project_mode_for_app_env


def allow_auth_dev_bypass(settings: Settings) -> bool:
    """True only in development project mode with CLERK_DEV_BYPASS=true."""
    return (
        project_mode_for_app_env(settings.app_env) is ProjectMode.DEVELOPMENT
        and settings.clerk_dev_bypass
    )

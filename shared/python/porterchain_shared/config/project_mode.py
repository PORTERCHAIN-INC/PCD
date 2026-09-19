"""Project runtime mode — boot-time SoT derived from APP_ENV (Jeff Dean).

Mode is a process/deploy property. Do not store it in Postgres or flip it from
a live production Admin UI. Change APP_ENV (Doppler / .env), then restart.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

# Canonical stored values after Settings normalization.
APP_ENV_DEVELOPMENT = "local"
APP_ENV_TESTING = "test"
APP_ENV_PRODUCTION = "production"

_DEV_ALIASES = frozenset({"local", "dev", "development"})
_TEST_ALIASES = frozenset({"test"})
_PROD_ALIASES = frozenset({"production", "staging", "prod"})


class ProjectMode(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


def normalize_app_env(raw: str | None) -> str:
    """Map aliases to the three canonical APP_ENV strings."""
    env = (raw or "").strip().lower()
    if env in _DEV_ALIASES:
        return APP_ENV_DEVELOPMENT
    if env in _TEST_ALIASES:
        return APP_ENV_TESTING
    if env in _PROD_ALIASES:
        # Keep staging distinct for logs, but same ProjectMode.production.
        if env == "staging":
            return "staging"
        if env == "prod":
            return APP_ENV_PRODUCTION
        return APP_ENV_PRODUCTION
    # Unknown / empty → treat as production-like fail-closed (do not unlock laptop doors).
    return env or APP_ENV_PRODUCTION


def project_mode_for_app_env(app_env: str | None) -> ProjectMode:
    env = normalize_app_env(app_env)
    if env == APP_ENV_DEVELOPMENT:
        return ProjectMode.DEVELOPMENT
    if env == APP_ENV_TESTING:
        return ProjectMode.TESTING
    return ProjectMode.PRODUCTION


def is_relaxed_boot_env(app_env: str | None) -> bool:
    """True for development + testing — JWT defaults / Clerk optional at boot."""
    return project_mode_for_app_env(app_env) in (ProjectMode.DEVELOPMENT, ProjectMode.TESTING)


@dataclass(frozen=True)
class RuntimePosture:
    mode: ProjectMode
    app_env: str
    auth_bypass_allowed: bool
    stripe_mock_allowed: bool
    requires_live_clerk: bool
    cookie_domain_mode: str  # "host_only" | "porterchain_domain"
    restart_required_to_change: bool = True
    change_control: str = "Set APP_ENV in Doppler or env/.env, then restart API and portals."

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        return d


def runtime_posture(
    *,
    app_env: str,
    clerk_dev_bypass: bool = False,
    stripe_mock: bool = False,
    stripe_secret: str = "",
) -> RuntimePosture:
    """Derived gates for the running process (never mutate APP_ENV here)."""
    normalized = normalize_app_env(app_env)
    mode = project_mode_for_app_env(normalized)
    is_dev = mode is ProjectMode.DEVELOPMENT
    is_prod = mode is ProjectMode.PRODUCTION
    return RuntimePosture(
        mode=mode,
        app_env=normalized,
        auth_bypass_allowed=is_dev and bool(clerk_dev_bypass),
        stripe_mock_allowed=is_dev and (bool(stripe_mock) or not stripe_secret),
        requires_live_clerk=is_prod,
        cookie_domain_mode="host_only" if is_dev else "porterchain_domain",
    )


def runtime_posture_from_settings(settings: Any) -> RuntimePosture:
    return runtime_posture(
        app_env=getattr(settings, "app_env", APP_ENV_DEVELOPMENT),
        clerk_dev_bypass=bool(getattr(settings, "clerk_dev_bypass", False)),
        stripe_mock=bool(getattr(settings, "stripe_mock", False)),
        stripe_secret=str(getattr(settings, "stripe_secret", "") or ""),
    )

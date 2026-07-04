"""Per user-class Clerk application registry (enterprise blast-radius isolation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from porterchain_api.auth.clerk_client import ClerkClient
from porterchain_api.config import Settings

ClerkAppKind = Literal["customer", "merchant", "admin", "driver"]

ALL_CLERK_APP_KINDS: tuple[ClerkAppKind, ...] = ("customer", "merchant", "admin", "driver")


@dataclass(frozen=True)
class ClerkAppConfig:
    kind: ClerkAppKind
    secret_key: str
    jwks_url: str
    publishable_key: str


def _resolve_app(
    settings: Settings,
    kind: ClerkAppKind,
    *,
    secret: str,
    jwks: str,
    publishable: str,
) -> ClerkAppConfig | None:
    secret_key = (secret or settings.clerk_secret_key or "").strip()
    jwks_url = (jwks or settings.clerk_jwks_url or "").strip()
    publishable_key = (publishable or settings.clerk_publishable_key or "").strip()
    if not secret_key and not jwks_url and not publishable_key:
        return None
    return ClerkAppConfig(
        kind=kind,
        secret_key=secret_key,
        jwks_url=jwks_url,
        publishable_key=publishable_key,
    )


def clerk_app_configs(settings: Settings) -> list[ClerkAppConfig]:
    """All configured Clerk apps. Per-class keys override legacy CLERK_* fallback."""
    candidates = [
        _resolve_app(
            settings,
            "customer",
            secret=settings.clerk_customer_secret_key,
            jwks=settings.clerk_customer_jwks_url,
            publishable=settings.clerk_customer_publishable_key,
        ),
        _resolve_app(
            settings,
            "merchant",
            secret=settings.clerk_merchant_secret_key,
            jwks=settings.clerk_merchant_jwks_url,
            publishable=settings.clerk_merchant_publishable_key,
        ),
        _resolve_app(
            settings,
            "admin",
            secret=settings.clerk_admin_secret_key,
            jwks=settings.clerk_admin_jwks_url,
            publishable=settings.clerk_admin_publishable_key,
        ),
        _resolve_app(
            settings,
            "driver",
            secret=settings.clerk_driver_secret_key,
            jwks=settings.clerk_driver_jwks_url,
            publishable=settings.clerk_driver_publishable_key,
        ),
    ]
    apps = [c for c in candidates if c is not None]

    # Legacy single-app mode: one shared config applies to all classes.
    if not apps and settings.clerk_secret_key.strip() and settings.clerk_jwks_url.strip():
        shared = ClerkAppConfig(
            kind="admin",
            secret_key=settings.clerk_secret_key.strip(),
            jwks_url=settings.clerk_jwks_url.strip(),
            publishable_key=settings.clerk_publishable_key.strip(),
        )
        return [
            ClerkAppConfig(kind=k, secret_key=shared.secret_key, jwks_url=shared.jwks_url, publishable_key=shared.publishable_key)
            for k in ALL_CLERK_APP_KINDS
        ]

    return apps


def clerk_app_for_kind(settings: Settings, kind: ClerkAppKind) -> ClerkAppConfig | None:
    for app in clerk_app_configs(settings):
        if app.kind == kind:
            return app
    return None


def clerk_client_for_kind(settings: Settings, kind: ClerkAppKind) -> ClerkClient:
    app = clerk_app_for_kind(settings, kind)
    if not app or not app.secret_key:
        raise ValueError(f"clerk_{kind}_secret_key_required")
    return ClerkClient(app.secret_key)


def clerk_jwks_urls(settings: Settings) -> list[tuple[ClerkAppKind, str]]:
    seen: set[str] = set()
    urls: list[tuple[ClerkAppKind, str]] = []
    for app in clerk_app_configs(settings):
        if app.jwks_url and app.jwks_url not in seen:
            seen.add(app.jwks_url)
            urls.append((app.kind, app.jwks_url))
    return urls


def is_clerk_secret_configured(settings: Settings, kind: ClerkAppKind | None = None) -> bool:
    if kind:
        app = clerk_app_for_kind(settings, kind)
        return bool(app and app.secret_key)
    return any(app.secret_key for app in clerk_app_configs(settings))


def is_clerk_configured(settings: Settings) -> bool:
    return bool(clerk_jwks_urls(settings))


def fetch_clerk_user(settings: Settings, clerk_user_id: str) -> tuple[dict | None, ClerkAppKind | None]:
    """Try each Clerk app's Backend API until the user is found."""
    for app in clerk_app_configs(settings):
        if not app.secret_key:
            continue
        try:
            user = ClerkClient(app.secret_key).get_user(clerk_user_id)
            if user:
                return user, app.kind
        except Exception:
            continue
    return None, None

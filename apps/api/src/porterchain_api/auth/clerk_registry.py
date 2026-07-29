"""Clerk application registry — PorterChain Platform (single app) by default.

Enterprise multi-app slots remain parseable for rollback, but when
``clerk_unified_mode`` is set (or all slots share one sk+jwks), every
``ClerkAppKind`` resolves to the same Platform triad.

Platform = former Porterchain Admin app keys (``CLERK_*`` triad or ``CLERK_ADMIN_*``).
"""

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
    secret_key = (secret or "").strip()
    jwks_url = (jwks or "").strip()
    publishable_key = (publishable or "").strip()
    if not secret_key and not jwks_url and not publishable_key:
        return None
    return ClerkAppConfig(
        kind=kind,
        secret_key=secret_key or settings.clerk_secret_key.strip(),
        jwks_url=jwks_url or settings.clerk_jwks_url.strip(),
        publishable_key=publishable_key or settings.clerk_publishable_key.strip(),
    )


def _portal_slot_apps(settings: Settings) -> list[ClerkAppConfig]:
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
    return [c for c in candidates if c is not None]


def resolve_platform_clerk_config(settings: Settings) -> ClerkAppConfig | None:
    """
    PorterChain Platform triad.

    Prefer ``CLERK_SECRET_KEY`` + ``CLERK_JWKS_URL``; fall back to Admin slots
    (Platform was renamed from Porterchain Admin).
    """
    secret = settings.clerk_secret_key.strip() or settings.clerk_admin_secret_key.strip()
    jwks = settings.clerk_jwks_url.strip() or settings.clerk_admin_jwks_url.strip()
    publishable = (
        settings.clerk_publishable_key.strip() or settings.clerk_admin_publishable_key.strip()
    )
    if not secret and not jwks and not publishable:
        return None
    if not secret or not jwks:
        # Incomplete triad — still allow publishable-only for client surfaces
        if not secret and not jwks:
            return None
    return ClerkAppConfig(
        kind="admin",
        secret_key=secret,
        jwks_url=jwks,
        publishable_key=publishable,
    )


def _apps_share_single_issuer(apps: list[ClerkAppConfig]) -> bool:
    usable = [a for a in apps if a.secret_key and a.jwks_url]
    if len(usable) < 1:
        return False
    secrets = {a.secret_key for a in usable}
    jwks = {a.jwks_url for a in usable}
    return len(secrets) == 1 and len(jwks) == 1


def is_divergent_enterprise_clerk(settings: Settings) -> bool:
    """True when four portal slots are filled with *different* Clerk apps."""
    if not is_enterprise_clerk_configured(settings):
        return False
    apps = _portal_slot_apps(settings)
    return not _apps_share_single_issuer(apps)


def should_use_platform_clerk(settings: Settings) -> bool:
    """Force single PorterChain Platform client."""
    if settings.clerk_unified_mode:
        return True
    slots = _portal_slot_apps(settings)
    if slots and _apps_share_single_issuer(slots):
        return True
    platform = resolve_platform_clerk_config(settings)
    if platform and platform.secret_key and platform.jwks_url and not is_divergent_enterprise_clerk(settings):
        return True
    return False


def _expand_platform(platform: ClerkAppConfig) -> list[ClerkAppConfig]:
    return [
        ClerkAppConfig(
            kind=k,
            secret_key=platform.secret_key,
            jwks_url=platform.jwks_url,
            publishable_key=platform.publishable_key,
        )
        for k in ALL_CLERK_APP_KINDS
    ]


def clerk_app_configs(settings: Settings) -> list[ClerkAppConfig]:
    """Configured Clerk apps. Unified / Platform → one triad expanded to all kinds."""
    if should_use_platform_clerk(settings):
        platform = resolve_platform_clerk_config(settings)
        if platform and (platform.secret_key or platform.jwks_url):
            return _expand_platform(platform)
        # Unified flag set but triad empty — fall through to slots if identical
        slots = _portal_slot_apps(settings)
        if slots and _apps_share_single_issuer(slots):
            shared = next(a for a in slots if a.secret_key and a.jwks_url)
            return _expand_platform(shared)

    apps = _portal_slot_apps(settings)

    # Legacy single-app mode: one shared config applies to all classes.
    if not apps and settings.clerk_secret_key.strip() and settings.clerk_jwks_url.strip():
        shared = ClerkAppConfig(
            kind="admin",
            secret_key=settings.clerk_secret_key.strip(),
            jwks_url=settings.clerk_jwks_url.strip(),
            publishable_key=settings.clerk_publishable_key.strip(),
        )
        return _expand_platform(shared)

    return apps


def clerk_app_for_kind(settings: Settings, kind: ClerkAppKind) -> ClerkAppConfig | None:
    for app in clerk_app_configs(settings):
        if app.kind == kind:
            return app
    return None


def clerk_client_for_kind(settings: Settings, kind: ClerkAppKind) -> ClerkClient:
    """Backend API client. In Platform mode every kind uses the same secret."""
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


def clerk_health_checks(settings: Settings) -> dict[str, str]:
    """Per-portal JWKS reachability for readiness (§0.5.6)."""
    import httpx

    results: dict[str, str] = {}
    # Platform mode: one JWKS check, mirror status to all kinds
    if should_use_platform_clerk(settings):
        urls = clerk_jwks_urls(settings)
        if not urls:
            return {k: "missing" for k in ALL_CLERK_APP_KINDS}
        _kind, jwks_url = urls[0]
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(jwks_url)
                if response.status_code >= 400:
                    status = f"http_{response.status_code}"
                else:
                    keys = response.json().get("keys", [])
                    status = "ok" if keys else "empty_jwks"
        except Exception as exc:  # noqa: BLE001
            status = f"unreachable: {exc}"
        return {k: status for k in ALL_CLERK_APP_KINDS}

    for kind in ALL_CLERK_APP_KINDS:
        app = clerk_app_for_kind(settings, kind)
        if not app or not app.jwks_url:
            results[kind] = "missing"
            continue
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.get(app.jwks_url)
                if response.status_code >= 400:
                    results[kind] = f"http_{response.status_code}"
                    continue
                keys = response.json().get("keys", [])
                results[kind] = "ok" if keys else "empty_jwks"
        except Exception as exc:  # noqa: BLE001
            results[kind] = f"unreachable: {exc}"
    return results


def is_enterprise_clerk_configured(settings: Settings) -> bool:
    """True when all four portal slots have explicit secret + JWKS env vars."""
    explicit = {
        "customer": (settings.clerk_customer_secret_key, settings.clerk_customer_jwks_url),
        "merchant": (settings.clerk_merchant_secret_key, settings.clerk_merchant_jwks_url),
        "admin": (settings.clerk_admin_secret_key, settings.clerk_admin_jwks_url),
        "driver": (settings.clerk_driver_secret_key, settings.clerk_driver_jwks_url),
    }
    return all(secret.strip() and jwks.strip() for secret, jwks in explicit.values())


def is_legacy_clerk_configured(settings: Settings) -> bool:
    return bool(settings.clerk_secret_key.strip() and settings.clerk_jwks_url.strip())


def clerk_configuration_mode(settings: Settings) -> str:
    """
    unified | enterprise | legacy | incomplete

    Identical four-slot keys or ``clerk_unified_mode`` → unified (not enterprise).
    """
    if settings.clerk_unified_mode:
        if resolve_platform_clerk_config(settings) or is_enterprise_clerk_configured(settings):
            return "unified"
        if is_legacy_clerk_configured(settings):
            return "unified"
        return "incomplete"

    if is_enterprise_clerk_configured(settings):
        if _apps_share_single_issuer(_portal_slot_apps(settings)):
            return "unified"
        return "enterprise"

    if is_legacy_clerk_configured(settings):
        return "legacy"

    platform = resolve_platform_clerk_config(settings)
    if platform and platform.secret_key and platform.jwks_url:
        return "unified"

    return "incomplete"


def is_clerk_secret_configured(settings: Settings, kind: ClerkAppKind | None = None) -> bool:
    if kind:
        app = clerk_app_for_kind(settings, kind)
        return bool(app and app.secret_key)
    return any(app.secret_key for app in clerk_app_configs(settings))


def is_clerk_configured(settings: Settings) -> bool:
    return bool(clerk_jwks_urls(settings))


def fetch_clerk_user(settings: Settings, clerk_user_id: str) -> tuple[dict | None, ClerkAppKind | None]:
    """Resolve user via Platform Backend API (single secret in unified mode)."""
    if should_use_platform_clerk(settings):
        platform = resolve_platform_clerk_config(settings)
        if not platform or not platform.secret_key:
            apps = clerk_app_configs(settings)
            platform = next((a for a in apps if a.secret_key), None)
        if not platform or not platform.secret_key:
            return None, None
        try:
            user = ClerkClient(platform.secret_key).get_user(clerk_user_id)
            if user:
                return user, "admin"
        except Exception:
            return None, None
        return None, None

    seen_secrets: set[str] = set()
    for app in clerk_app_configs(settings):
        if not app.secret_key or app.secret_key in seen_secrets:
            continue
        seen_secrets.add(app.secret_key)
        try:
            user = ClerkClient(app.secret_key).get_user(clerk_user_id)
            if user:
                return user, app.kind
        except Exception:
            continue
    return None, None

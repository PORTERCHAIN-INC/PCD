"""Shopify offline access tokens: expiring pair, refresh, and legacy migration.

Shopify no longer accepts non-expiring offline tokens from this public app: Admin
API calls answer 403 "Non-expiring access tokens are no longer accepted". So every
grant asks for an expiring token (``expiring=1``), the refresh token is stored next
to it, and every Admin call takes its token from ``access_token_for``, which
refreshes it before it lapses and migrates a stored legacy token once.

Docs: https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/offline-access-tokens
and .../migrate-to-expiring-offline-access-tokens
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, object_session
from sqlalchemy.orm.exc import UnmappedInstanceError

from porterchain_api.config import Settings
from porterchain_api.merchant_engine.secrets import (
    decrypt_signing_secret,
    encrypt_signing_secret,
)
from porterchain_api.merchant_engine.shopify_urls import (
    normalize_shop_domain,
    oauth_configured,
)
from porterchain_api.merchant_models import ShopifyShop

logger = logging.getLogger(__name__)

GRANT_TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
TOKEN_TYPE_ID_TOKEN = "urn:ietf:params:oauth:token-type:id_token"
TOKEN_TYPE_OFFLINE = "urn:shopify:params:oauth:token-type:offline-access-token"

# ``ShopifyShop.token_status``. None means a token stored before expiring tokens
# (or by an older build): legacy until migrated.
STATUS_EXPIRING = "expiring"
STATUS_CUSTOM_APP = "custom_app"  # pasted Admin token from a merchant-made app: never exchanged
TOKEN_REAUTH_REQUIRED = "token_reauth_required"  # Shopify refused our token; merchant must reopen

REFRESH_MARGIN = timedelta(minutes=5)
_TOKEN_ATTRS = (
    "encrypted_access_token",
    "access_token_expires_at",
    "encrypted_refresh_token",
    "refresh_token_expires_at",
    "token_status",
)
_NON_EXPIRING_PHRASE = "non-expiring access token"


class ShopifyTokenError(RuntimeError):
    """The token endpoint refused or could not be reached. Message has no secrets."""

    def __init__(self, status: int | None, error: str) -> None:
        super().__init__(f"shopify_token_request_failed:{status or 'network'}:{error}")
        self.status = status
        self.error = error

    @property
    def transient(self) -> bool:
        return self.status is None or self.status == 429 or self.status >= 500


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _encrypt(value: str | None, settings: Settings) -> str | None:
    return encrypt_signing_secret(value, encryption_key=settings.jwt_secret) if value else None


def _decrypt(value: str | None, settings: Settings) -> str | None:
    return decrypt_signing_secret(value, encryption_key=settings.jwt_secret) if value else None


def _token_request(shop: str, data: dict[str, str]) -> dict[str, Any]:
    """POST https://{shop}/admin/oauth/access_token (form body, as documented)."""
    url = f"https://{normalize_shop_domain(shop)}/admin/oauth/access_token"
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, data=data, headers={"Accept": "application/json"})
    except httpx.HTTPError as exc:
        raise ShopifyTokenError(None, type(exc).__name__) from exc
    if response.status_code >= 400:
        try:
            parsed = response.json()
        except ValueError:
            parsed = None
        error = str(parsed.get("error") or "") if isinstance(parsed, dict) else ""
        raise ShopifyTokenError(response.status_code, error or f"http_{response.status_code}")
    body = response.json()
    return body if isinstance(body, dict) else {}


def _client(settings: Settings) -> dict[str, str]:
    return {"client_id": settings.shopify_api_key, "client_secret": settings.shopify_api_secret}


def exchange_authorization_code(shop: str, code: str, settings: Settings) -> dict[str, Any]:
    """Authorization code grant → expiring offline token + refresh token."""
    return _token_request(shop, {**_client(settings), "code": code, "expiring": "1"})


def exchange_id_token(shop: str, id_token: str, settings: Settings) -> dict[str, Any]:
    """Token exchange (Shopify id_token) → expiring offline token + refresh token."""
    return _token_request(
        shop,
        {
            **_client(settings),
            "grant_type": GRANT_TOKEN_EXCHANGE,
            "subject_token": id_token,
            "subject_token_type": TOKEN_TYPE_ID_TOKEN,
            "requested_token_type": TOKEN_TYPE_OFFLINE,
            "expiring": "1",
        },
    )


def migrate_legacy_token(shop: str, legacy_token: str, settings: Settings) -> dict[str, Any]:
    """One-time exchange of a stored non-expiring offline token for an expiring pair."""
    return _token_request(
        shop,
        {
            **_client(settings),
            "grant_type": GRANT_TOKEN_EXCHANGE,
            "subject_token": legacy_token,
            "subject_token_type": TOKEN_TYPE_OFFLINE,
            "requested_token_type": TOKEN_TYPE_OFFLINE,
            "expiring": "1",
        },
    )


def refresh_access_token(shop: str, refresh_token: str, settings: Settings) -> dict[str, Any]:
    """Refresh grant. A retry after a transient failure returns the same rotated pair."""
    data = {**_client(settings), "grant_type": "refresh_token", "refresh_token": refresh_token}
    try:
        return _token_request(shop, data)
    except ShopifyTokenError as exc:
        if not exc.transient:
            raise
        return _token_request(shop, data)


def _seconds(value: Any) -> int | None:
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


def store_token_response(row: Any, body: dict[str, Any], settings: Settings) -> str:
    """Save a token-endpoint response on the shop. Returns the access token."""
    access_token = str(body.get("access_token") or "")
    if not access_token:
        raise ValueError("oauth_token_missing")
    now = _now()
    expires_in = _seconds(body.get("expires_in"))
    refresh_in = _seconds(body.get("refresh_token_expires_in"))
    row.encrypted_access_token = _encrypt(access_token, settings)
    row.access_token_expires_at = now + timedelta(seconds=expires_in) if expires_in else None
    row.encrypted_refresh_token = _encrypt(str(body.get("refresh_token") or ""), settings)
    row.refresh_token_expires_at = now + timedelta(seconds=refresh_in) if refresh_in else None
    row.token_status = STATUS_EXPIRING if expires_in else None
    if body.get("scope"):
        row.scopes = str(body["scope"])
    return access_token


def store_custom_app_token(row: Any, token: str, settings: Settings) -> None:
    """A merchant-made custom app's Admin token: it does not expire and is never exchanged."""
    clear_tokens(row)
    row.encrypted_access_token = _encrypt(token, settings)
    row.token_status = STATUS_CUSTOM_APP


def clear_tokens(row: Any) -> None:
    for attr in _TOKEN_ATTRS:
        setattr(row, attr, None)


def _session_of(shop: Any) -> Session | None:
    try:
        return object_session(shop)
    except UnmappedInstanceError:
        return None


def _persist(shop: Any) -> None:
    sess = _session_of(shop)
    if sess is not None:
        sess.add(shop)
        sess.commit()


def mark_reauth_required(shop: Any, reason: str) -> None:
    """Shopify will not take our token. The next admin open sends the merchant through OAuth."""
    logger.warning(
        "shopify_token_reauth_required shop=%s reason=%s", getattr(shop, "shop_domain", ""), reason
    )
    shop.token_status = TOKEN_REAUTH_REQUIRED
    _persist(shop)


def needs_reauth(shop: Any) -> bool:
    return getattr(shop, "token_status", None) == TOKEN_REAUTH_REQUIRED


def no_token_code(shop: Any, default: str) -> str:
    return TOKEN_REAUTH_REQUIRED if needs_reauth(shop) else default


def token_rejection_reason(status_code: int, text: str) -> str | None:
    """Tell a refused token from a missing scope (both can be 403)."""
    if status_code == 401:
        return "token_invalid"
    if status_code == 403 and _NON_EXPIRING_PHRASE in (text or "").lower():
        return "token_non_expiring"
    return None


def is_token_rejection(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        marker in lowered
        for marker in (TOKEN_REAUTH_REQUIRED, "token_non_expiring", "token_invalid", "http_401")
    ) or (_NON_EXPIRING_PHRASE in lowered)


def _legacy_oauth_token(shop: Any) -> bool:
    """Stored by our OAuth/token exchange before expiring tokens (those rows carry scopes)."""
    return (
        getattr(shop, "access_token_expires_at", None) is None
        and getattr(shop, "token_status", None) is None
        and bool(getattr(shop, "scopes", None))
    )


def _fresh(shop: Any) -> bool:
    expires_at = getattr(shop, "access_token_expires_at", None)
    return expires_at is not None and _aware(expires_at) - _now() > REFRESH_MARGIN


def access_token_for(shop: Any, settings: Settings) -> str | None:
    """A token Shopify will accept for this shop, or None (missing or reauth needed).

    Expiring token near its end → refresh. Legacy OAuth token → migrate once.
    Custom-app tokens and anything we cannot renew are returned unchanged.
    """
    token = _decrypt(getattr(shop, "encrypted_access_token", None), settings)
    if not token or needs_reauth(shop):
        return None
    if getattr(shop, "token_status", None) == STATUS_CUSTOM_APP:
        return token
    if getattr(shop, "access_token_expires_at", None) is None:
        if not _legacy_oauth_token(shop) or not oauth_configured(settings):
            return token
        return _renew(shop, settings, token, migrate=True)
    if _fresh(shop):
        return token
    return _renew(shop, settings, token, migrate=False)


def _renew(shop: Any, settings: Settings, token: str, *, migrate: bool) -> str | None:
    sess = _session_of(shop)
    if sess is not None and sa_inspect(shop).persistent:
        # Row lock: one worker renews; the others wait, then reuse its token.
        sess.refresh(shop, attribute_names=list(_TOKEN_ATTRS), with_for_update=True)
        if needs_reauth(shop):
            return None
        if _fresh(shop):
            return _decrypt(shop.encrypted_access_token, settings)
        token = _decrypt(shop.encrypted_access_token, settings) or token
        migrate = migrate and getattr(shop, "access_token_expires_at", None) is None
    domain = str(getattr(shop, "shop_domain", ""))
    try:
        if migrate:
            body = migrate_legacy_token(domain, token, settings)
        else:
            refresh = _decrypt(getattr(shop, "encrypted_refresh_token", None), settings)
            if not refresh or _refresh_expired(shop):
                mark_reauth_required(shop, "refresh_token_missing_or_expired")
                return None
            body = refresh_access_token(domain, refresh, settings)
    except ShopifyTokenError as exc:
        if exc.transient:
            # Shopify down: keep what we have; a still-valid token keeps working.
            logger.warning("shopify_token_renew_deferred shop=%s err=%s", domain, exc)
            return token if migrate or _not_expired(shop) else None
        # invalid_subject_token / invalid_request: only a new grant fixes it.
        mark_reauth_required(shop, f"{'migrate' if migrate else 'refresh'}:{exc.error}")
        return None
    try:
        new_token = store_token_response(shop, body, settings)
    except ValueError:
        mark_reauth_required(shop, "token_response_missing_access_token")
        return None
    _persist(shop)
    logger.info("shopify_token_%s shop=%s", "migrated" if migrate else "refreshed", domain)
    return new_token


def _refresh_expired(shop: Any) -> bool:
    expires_at = getattr(shop, "refresh_token_expires_at", None)
    return expires_at is not None and _aware(expires_at) <= _now()


def _not_expired(shop: Any) -> bool:
    expires_at = getattr(shop, "access_token_expires_at", None)
    return expires_at is not None and _aware(expires_at) > _now()


def token_state_for_open(db: Session, settings: Settings, shop_domain: str) -> str:
    """Merchant opened the app from Shopify admin: ``ok``, ``migrated`` or ``""``.

    ``""`` means no usable token (none stored, refused, or refresh expired), so the
    caller sends the merchant through OAuth instead of a dead-end page.
    """
    shop = normalize_shop_domain(shop_domain)
    row = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.shop_domain == shop, ShopifyShop.uninstalled_at.is_(None))
        .first()
    )
    if row is None or not getattr(row, "encrypted_access_token", None) or needs_reauth(row):
        return ""
    if getattr(row, "access_token_expires_at", None) is None and not _legacy_oauth_token(row):
        return "ok"  # custom-app token: nothing to renew
    legacy = _legacy_oauth_token(row)
    if not access_token_for(row, settings):
        return ""
    if legacy and getattr(row, "access_token_expires_at", None) is not None:
        return "migrated"
    return "ok"

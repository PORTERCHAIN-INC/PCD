"""Shopify HMAC (webhooks + OAuth callback query)."""

from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import parse_qsl


def verify_webhook_hmac(raw_body: bytes, header: str | None, secrets: list[str]) -> bool:
    """Shopify `X-Shopify-Hmac-Sha256` is Base64(HMAC-SHA256(raw body))."""
    if not header or not raw_body:
        return False
    provided = header.strip().encode()
    for secret in secrets:
        if not secret:
            continue
        digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
        expected = base64.b64encode(digest)
        if hmac.compare_digest(provided, expected):
            return True
    return False


def verify_oauth_hmac(query_string: str, secret: str) -> bool:
    """OAuth callback `hmac` is hex HMAC-SHA256 of the other query params."""
    if not secret:
        return False
    pairs = parse_qsl(query_string, keep_blank_values=True)
    provided = ""
    rest: list[tuple[str, str]] = []
    for key, value in pairs:
        if key == "hmac":
            provided = value
        elif key != "signature":
            rest.append((key, value))
    if not provided:
        return False
    message = "&".join(f"{k}={v}" for k, v in sorted(rest))
    expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)

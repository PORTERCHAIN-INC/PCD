"""Shopify HMAC (webhooks + OAuth callback query)."""

from __future__ import annotations

import base64
import hashlib
import hmac


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

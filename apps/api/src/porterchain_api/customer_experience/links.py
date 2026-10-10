"""Signed, expiring self-service links for the delivery recipient.

Token = base64url(json payload) + "." + base64url(HMAC-SHA256). The key is derived
from ``settings.jwt_secret`` with a purpose label, so a manage token can never be
replayed as a session JWT (and vice versa). Tokens bind order id + tracking number.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

_PURPOSE = b"porterchain-cx-manage-v1"


def _key(secret: str) -> bytes:
    return hmac.new(str(secret or "").encode(), _PURPOSE, hashlib.sha256).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def make_manage_token(
    secret: str,
    *,
    order_id: str,
    tracking_number: str,
    ttl_hours: int = 72,
    now: datetime | None = None,
) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "o": order_id,
        "t": tracking_number,
        "exp": int((issued + timedelta(hours=max(1, int(ttl_hours)))).timestamp()),
    }
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = _b64(hmac.new(_key(secret), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_manage_token(
    secret: str,
    token: str,
    *,
    tracking_number: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return {'order_id', 'tracking_number', 'exp'}; raises ValueError link_invalid/link_expired."""
    try:
        body, sig = str(token or "").split(".", 1)
        expected = _b64(hmac.new(_key(secret), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("link_invalid")
        payload = json.loads(_unb64(body))
    except ValueError as exc:
        if str(exc) == "link_invalid":
            raise
        raise ValueError("link_invalid") from exc
    except Exception as exc:  # noqa: BLE001 — malformed base64/json
        raise ValueError("link_invalid") from exc
    if not isinstance(payload, dict) or not payload.get("o") or not payload.get("t"):
        raise ValueError("link_invalid")
    if tracking_number is not None and str(payload["t"]) != str(tracking_number):
        raise ValueError("link_invalid")
    current = (now or datetime.now(UTC)).timestamp()
    if int(payload.get("exp") or 0) < current:
        raise ValueError("link_expired")
    return {"order_id": str(payload["o"]), "tracking_number": str(payload["t"]), "exp": int(payload["exp"])}


def manage_url(website_url: str, tracking_number: str, token: str) -> str:
    base = str(website_url or "").rstrip("/")
    return f"{base}/track/{quote(str(tracking_number), safe='')}/manage?t={quote(token, safe='')}"

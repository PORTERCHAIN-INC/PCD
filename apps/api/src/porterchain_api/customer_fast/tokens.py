"""Purpose-bound signed links (HMAC-SHA256 over settings.jwt_secret).

Separate purposes so a preferences link can never act as a Send-again link or a manage link.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any

PREFS = b"porterchain-customer-prefs-v1"
SEND_AGAIN = b"porterchain-send-again-v1"

PREFS_TTL_DAYS = 400  # CASL: unsubscribe must keep working >= 60 days after the message.
SEND_AGAIN_TTL_DAYS = 120
MANAGE_TTL_HOURS = 24 * 30  # Booking-confirmation tracking link: covers delivery + rating.


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key(secret: str, purpose: bytes) -> bytes:
    return hmac.new(str(secret or "").encode(), purpose, hashlib.sha256).digest()


def sign(secret: str, purpose: bytes, claims: dict[str, Any], *, ttl: timedelta, now: datetime | None = None) -> str:
    payload = {**claims, "exp": int(((now or datetime.now(UTC)) + ttl).timestamp())}
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    sig = _b64(hmac.new(_key(secret, purpose), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify(secret: str, purpose: bytes, token: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Return claims or raise ValueError('link_invalid' | 'link_expired')."""
    try:
        body, sig = str(token or "").split(".", 1)
        expected = _b64(hmac.new(_key(secret, purpose), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("link_invalid")
        claims = json.loads(_unb64(body))
    except ValueError as exc:
        if str(exc) == "link_invalid":
            raise
        raise ValueError("link_invalid") from exc
    except Exception as exc:
        raise ValueError("link_invalid") from exc
    if not isinstance(claims, dict):
        raise ValueError("link_invalid")
    if int(claims.get("exp") or 0) < (now or datetime.now(UTC)).timestamp():
        raise ValueError("link_expired")
    return claims


def prefs_token(secret: str, customer_id: str) -> str:
    return sign(secret, PREFS, {"c": customer_id}, ttl=timedelta(days=PREFS_TTL_DAYS))


def send_again_token(secret: str, order_id: str) -> str:
    return sign(secret, SEND_AGAIN, {"o": order_id}, ttl=timedelta(days=SEND_AGAIN_TTL_DAYS))

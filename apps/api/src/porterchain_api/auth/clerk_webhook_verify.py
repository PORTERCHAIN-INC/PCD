"""Clerk/Svix webhook signature verification (no extra dependency)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time


class ClerkWebhookSignatureError(ValueError):
    pass


def verify_clerk_webhook_signature(
    *,
    payload: bytes,
    secret: str,
    svix_id: str | None,
    svix_timestamp: str | None,
    svix_signature: str | None,
    tolerance_seconds: int = 300,
) -> None:
    """
    Verify Clerk webhook signatures (Svix format).

    Secret form: ``whsec_<base64>`` (Clerk dashboard) or raw base64.
    """
    if not secret:
        raise ClerkWebhookSignatureError("missing_signing_secret")
    if not svix_id or not svix_timestamp or not svix_signature:
        raise ClerkWebhookSignatureError("missing_svix_headers")

    try:
        ts = int(svix_timestamp)
    except ValueError as exc:
        raise ClerkWebhookSignatureError("invalid_timestamp") from exc

    if abs(int(time.time()) - ts) > tolerance_seconds:
        raise ClerkWebhookSignatureError("timestamp_out_of_tolerance")

    raw_secret = secret.strip()
    raw_secret = raw_secret.removeprefix("whsec_")
    try:
        key = base64.b64decode(raw_secret)
    except Exception as exc:
        raise ClerkWebhookSignatureError("invalid_signing_secret") from exc

    signed_content = f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}".encode()
    digest = hmac.new(key, signed_content, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()

    candidates = []
    for part in svix_signature.split(" "):
        part = part.strip()
        if not part:
            continue
        if "," in part:
            # v1,<sig>
            _, _, sig = part.partition(",")
            candidates.append(sig)
        elif part.startswith("v1="):
            candidates.append(part[3:])
        else:
            candidates.append(part)

    if not any(hmac.compare_digest(expected, c) for c in candidates):
        raise ClerkWebhookSignatureError("invalid_signature")

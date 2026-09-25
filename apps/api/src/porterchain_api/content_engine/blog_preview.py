"""Signed blog draft preview tokens (HMAC over locale:slug:exp)."""

from __future__ import annotations

import hashlib
import hmac
import time


def make_blog_preview_token(
    *,
    locale: str,
    slug: str,
    secret: str,
    ttl_seconds: int = 60 * 60 * 24 * 7,
) -> str:
    exp = int(time.time()) + max(60, ttl_seconds)
    msg = f"{locale.strip().lower()}:{slug.strip().lower()}:{exp}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_blog_preview_token(
    *,
    locale: str,
    slug: str,
    token: str,
    secret: str,
) -> bool:
    secret = (secret or "").strip()
    token = (token or "").strip()
    if not secret or not token or "." not in token:
        return False
    exp_s, sig = token.split(".", 1)
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    if exp < int(time.time()):
        return False
    msg = f"{locale.strip().lower()}:{slug.strip().lower()}:{exp}"
    expected = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)

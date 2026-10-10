"""Abuse protection for guest checkout (no account = we must defend the endpoint).

Layers, cheapest first: honeypot field, minimum human fill time, disposable-email block,
per-IP and per-email Redis windows, and quote sanity (retail, fresh, not already paid).
Fails closed on Redis errors outside local/test.
"""

from __future__ import annotations

import hashlib
import re

from porterchain_api.config import Settings

MIN_FILL_MS = 2500
IP_PER_MINUTE = 4
EMAIL_PER_MINUTE = 3

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
_PHONE_DIGITS = re.compile(r"\d")
DISPOSABLE_DOMAINS = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "10minutemail.com",
        "tempmail.com",
        "temp-mail.org",
        "yopmail.com",
        "trashmail.com",
        "sharklasers.com",
        "getnada.com",
        "dispostable.com",
        "maildrop.cc",
        "throwawaymail.com",
    }
)


def ip_hash(ip: str | None) -> str | None:
    return hashlib.sha256(f"pc-ip:{ip}".encode()).hexdigest() if ip else None


def check_contact(email: str, phone: str) -> tuple[str, str]:
    clean = (email or "").strip().lower()
    if not _EMAIL.match(clean) or len(clean) > 320:
        raise ValueError("email_invalid")
    if clean.rsplit("@", 1)[-1] in DISPOSABLE_DOMAINS:
        raise ValueError("email_disposable")
    digits = "".join(_PHONE_DIGITS.findall(phone or ""))
    if not 10 <= len(digits) <= 15:
        raise ValueError("phone_invalid")
    return clean, (phone or "").strip()[:32]


def check_bot(*, honeypot: str | None, form_elapsed_ms: int | None) -> None:
    if (honeypot or "").strip():
        raise ValueError("rejected")
    if form_elapsed_ms is None or form_elapsed_ms < MIN_FILL_MS:
        raise ValueError("rejected")


def check_rate(settings: Settings, *, ip: str | None, email: str) -> None:
    from porterchain_api.platform.rate_limit import check_fixed_window

    windows = [
        (f"rl:guest_book:ip:{ip_hash(ip)}", IP_PER_MINUTE, None),
        (f"rl:guest_book:email:{hashlib.sha256(email.encode()).hexdigest()}", EMAIL_PER_MINUTE, None),
    ]
    for key, limit, window in windows:
        allowed, _current, error = check_fixed_window(key, limit, window=window)  # per-minute buckets
        if error:
            if settings.app_env in ("local", "test", "development"):
                continue
            raise ValueError("rate_limit_unavailable")
        if not allowed:
            raise ValueError("rate_limited")

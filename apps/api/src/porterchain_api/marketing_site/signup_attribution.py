"""First-touch marketing attribution stamped on a merchant at signup.

Stored in ``merchant.profile["signup_attribution"]`` (JSON, no migration) and
never overwritten once set.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

ALLOWED_KEYS: tuple[str, ...] = (
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "from",
    "landing_page",
    "referrer",
    "pc_vid",
)


def clean_signup_attribution(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in ALLOWED_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()[: 500 if key in ("landing_page", "referrer") else 120]
    return out


def stamp_signup_attribution(merchant: Any, raw: Any) -> bool:
    """Set first-touch attribution on the merchant profile. True when stamped."""
    clean = clean_signup_attribution(raw)
    if not clean:
        return False
    profile = dict(merchant.profile or {}) if isinstance(getattr(merchant, "profile", None), dict) else {}
    if profile.get("signup_attribution"):
        return False
    profile["signup_attribution"] = {**clean, "captured_at": datetime.now(UTC).isoformat()}
    merchant.profile = profile
    return True

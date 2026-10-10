"""Constant-time shared-secret checks for webhook / ingest headers."""

from __future__ import annotations

import hmac


def secrets_match(provided: str | None, expected: str | None) -> bool:
    """True only when both are non-empty and equal (timing-safe)."""
    a = (provided or "").strip()
    b = (expected or "").strip()
    if not a or not b:
        return False
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


__all__ = ["secrets_match"]

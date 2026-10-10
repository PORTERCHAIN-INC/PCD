"""PII minimisation before any third-party model call."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d")
_POSTAL_FULL = re.compile(r"\b([A-Z]\d[A-Z])\s?\d[A-Z]\d\b", re.IGNORECASE)


def redact(text: str) -> str:
    """Data minimisation before any third-party model (PIPEDA 4.4 / GDPR 5(1)(c)):
    no emails or phone numbers; postal codes cut to the FSA."""
    t = _EMAIL.sub("[email]", text or "")
    t = _PHONE.sub("[phone]", t)
    return _POSTAL_FULL.sub(lambda m: m.group(1).upper(), t)

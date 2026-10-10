"""PorterChain's own GST/HST registration number: one validated source for every document.

CRA format: 9-digit Business Number + program identifier RT + 4-digit reference
(e.g. ``123456789 RT0001``). Empty means "not registered yet": documents omit the line
and admin shows a warning; we never print a placeholder on a customer document.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERN = re.compile(r"^(\d{9})\s*RT\s*(\d{4})$")


def normalize_gst_hst(raw: Any) -> str:
    """Return ``'123456789 RT0001'`` or ``''``; raise ValueError on anything else."""
    text = re.sub(r"[\s-]+", " ", str(raw or "")).strip().upper()
    if not text:
        return ""
    m = _PATTERN.match(text.replace(" ", " "))
    if not m:
        m = _PATTERN.match(text.replace(" ", ""))
    if not m:
        raise ValueError("GST/HST number must be 9 digits + RT and 4 digits, e.g. 123456789 RT0001")
    return f"{m.group(1)} RT{m.group(2)}"


def safe_gst_hst(raw: Any) -> str:
    """Valid number or '' (legacy/invalid stored values never reach a document)."""
    try:
        return normalize_gst_hst(raw)
    except ValueError:
        return ""


def normalize_finance(raw: Any) -> dict[str, Any]:
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("finance settings must be an object")
    out = dict(raw or {})
    if "gst_hst_number" in out:
        out["gst_hst_number"] = normalize_gst_hst(out.get("gst_hst_number"))
    return out


def registration_status(number: str) -> dict[str, Any]:
    return {
        "gst_hst_number": number,
        "set": bool(number),
        "warning": None if number else (
            "GST/HST registration number is not set. Invoices, statements, quotes and tax "
            "reports print no registration line until you add it in Settings > Finance."
        ),
    }


def supplier_gst_hst_number(db: Any) -> str:
    """Read Settings > Finance directly (platform layer, usable from every engine)."""
    from porterchain_api.admin_models import SystemConfig

    row = db.get(SystemConfig, "settings_finance")
    value = row.value if row is not None and isinstance(row.value, dict) else {}
    return safe_gst_hst(value.get("gst_hst_number"))

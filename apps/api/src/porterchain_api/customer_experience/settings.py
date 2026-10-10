"""Per-merchant customer-experience settings (tracking page, notifications, self-service).

Stored in ``merchant.profile["settings"]["customer_experience"]`` (JSON, no migration).
Every customer-facing behaviour is OFF by default: the branded page, proactive
notifications, self-scheduling and the re-attempt policy only start once the
merchant (or ops) turns them on.
"""

from __future__ import annotations

import copy
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

NOTIFICATION_KINDS: tuple[str, ...] = (
    "out_for_delivery",
    "next_stop",
    "eta_20",
    "delivered",
    "attempted",
    "schedule_request",
)
CHANNELS: tuple[str, ...] = ("email", "sms", "whatsapp")

_DEFAULT: dict[str, Any] = {
    "schema": 1,
    "tracking": {
        "branded_page": False,
        "show_driver_first_name": True,
        "show_stops_away": True,
        "show_pod_photo": False,
        "support_email": None,
        "support_phone": None,
        "help_url": None,
    },
    "notifications": {
        "enabled": False,
        "channels": {"email": True, "sms": False, "whatsapp": False},
        "events": {kind: True for kind in NOTIFICATION_KINDS},
        "next_stop_threshold": 1,
        "eta_minutes": 20,
        # SMS/WhatsApp are held during quiet hours; email still goes out.
        "quiet_hours": {"enabled": True, "start": "21:00", "end": "08:00", "timezone": "America/Toronto"},
    },
    "self_service": {
        "enabled": False,
        "link_ttl_hours": 72,
        "allow_reschedule": True,
        "allow_instructions": True,
        "schedule_days": 7,
    },
    "delivery_rules": {
        "safe_place_allowed": True,
        "id_required": False,
        "signature_required": False,
        "require_schedule_for_bulky": False,
        "bulky_package_types": ["furniture", "bulky", "appliance", "oversized"],
        "bulky_vehicle_classes": [],
    },
    "reattempt": {"enabled": False, "max_attempts": 2, "return_to_sender_after": 2},
}

#: One-click presets the merchant portal can apply (merged over current settings).
PRESETS: dict[str, dict[str, Any]] = {
    "pharmacy": {
        "delivery_rules": {"safe_place_allowed": False, "id_required": True, "signature_required": True},
    },
    "furniture": {
        "delivery_rules": {"require_schedule_for_bulky": True},
        "self_service": {"enabled": True, "allow_reschedule": True},
    },
}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^\+?[0-9 ()\-.]{7,20}$")


def default_cx() -> dict[str, Any]:
    return copy.deepcopy(_DEFAULT)


def sanitize_hex(value: Any, fallback: str | None = None) -> str | None:
    text = str(value or "").strip()
    return text.lower() if _HEX.match(text) else fallback


def _bool(raw: dict[str, Any], out: dict[str, Any], key: str) -> None:
    if key in raw:
        out[key] = bool(raw[key])


def _int(raw: dict[str, Any], out: dict[str, Any], key: str, lo: int, hi: int, path: str) -> None:
    if key not in raw:
        return
    try:
        n = int(raw[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"cx_invalid:{path}.{key}") from exc
    if n < lo or n > hi:
        raise ValueError(f"cx_invalid:{path}.{key}")
    out[key] = n


def _section(raw: Any, path: str) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"cx_invalid:{path}")
    return raw


def _optional_text(raw: dict[str, Any], out: dict[str, Any], key: str, pattern: re.Pattern | None, path: str) -> None:
    if key not in raw:
        return
    text = str(raw[key] or "").strip()
    if not text:
        out[key] = None
        return
    if pattern is not None and not pattern.match(text):
        raise ValueError(f"cx_invalid:{path}.{key}")
    out[key] = text[:200]


def normalize_cx(raw: Any) -> dict[str, Any]:
    """Validate and fill defaults. Raises ValueError('cx_invalid:<path>')."""
    out = default_cx()
    if raw is None:
        return out
    if not isinstance(raw, dict):
        raise ValueError("cx_invalid:root")

    tr = _section(raw.get("tracking"), "tracking")
    t_out = out["tracking"]
    for key in ("branded_page", "show_driver_first_name", "show_stops_away", "show_pod_photo"):
        _bool(tr, t_out, key)
    _optional_text(tr, t_out, "support_email", _EMAIL, "tracking")
    _optional_text(tr, t_out, "support_phone", _PHONE, "tracking")
    if "help_url" in tr:
        url = str(tr.get("help_url") or "").strip()
        if url and not url.startswith("https://"):
            raise ValueError("cx_invalid:tracking.help_url")
        t_out["help_url"] = url[:300] or None

    nt = _section(raw.get("notifications"), "notifications")
    n_out = out["notifications"]
    _bool(nt, n_out, "enabled")
    chans = _section(nt.get("channels"), "notifications.channels")
    for ch in CHANNELS:
        if ch in chans:
            n_out["channels"][ch] = bool(chans[ch])
    evs = _section(nt.get("events"), "notifications.events")
    for kind in NOTIFICATION_KINDS:
        if kind in evs:
            n_out["events"][kind] = bool(evs[kind])
    _int(nt, n_out, "next_stop_threshold", 0, 10, "notifications")
    _int(nt, n_out, "eta_minutes", 5, 120, "notifications")
    qh = _section(nt.get("quiet_hours"), "notifications.quiet_hours")
    q_out = n_out["quiet_hours"]
    _bool(qh, q_out, "enabled")
    for key in ("start", "end"):
        if key in qh:
            text = str(qh[key] or "").strip()
            if not _HHMM.match(text):
                raise ValueError(f"cx_invalid:notifications.quiet_hours.{key}")
            q_out[key] = text
    if qh.get("timezone"):
        try:
            ZoneInfo(str(qh["timezone"]))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("cx_invalid:notifications.quiet_hours.timezone") from exc
        q_out["timezone"] = str(qh["timezone"])

    ss = _section(raw.get("self_service"), "self_service")
    s_out = out["self_service"]
    for key in ("enabled", "allow_reschedule", "allow_instructions"):
        _bool(ss, s_out, key)
    _int(ss, s_out, "link_ttl_hours", 1, 24 * 14, "self_service")
    _int(ss, s_out, "schedule_days", 1, 21, "self_service")

    dr = _section(raw.get("delivery_rules"), "delivery_rules")
    d_out = out["delivery_rules"]
    for key in ("safe_place_allowed", "id_required", "signature_required", "require_schedule_for_bulky"):
        _bool(dr, d_out, key)
    for key in ("bulky_package_types", "bulky_vehicle_classes"):
        if key in dr:
            vals = dr[key]
            if not isinstance(vals, list) or len(vals) > 20:
                raise ValueError(f"cx_invalid:delivery_rules.{key}")
            d_out[key] = sorted({re.sub(r"[^a-z0-9_]", "", str(v).lower())[:32] for v in vals} - {""})

    ra = _section(raw.get("reattempt"), "reattempt")
    r_out = out["reattempt"]
    _bool(ra, r_out, "enabled")
    _int(ra, r_out, "max_attempts", 1, 5, "reattempt")
    _int(ra, r_out, "return_to_sender_after", 1, 5, "reattempt")
    r_out["return_to_sender_after"] = max(r_out["return_to_sender_after"], r_out["max_attempts"])
    return out


def merge_patch(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(current)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_patch(merged[key], value)
        else:
            merged[key] = value
    return merged


def apply_preset(current: dict[str, Any], preset: str) -> dict[str, Any]:
    if preset not in PRESETS:
        raise ValueError("cx_invalid:preset")
    return normalize_cx(merge_patch(current, PRESETS[preset]))


def cx_for_merchant(merchant: Any) -> dict[str, Any]:
    """Normalized settings for a merchant (defaults on missing/invalid data)."""
    profile = getattr(merchant, "profile", None) if merchant is not None else None
    settings = profile.get("settings") if isinstance(profile, dict) else None
    raw = settings.get("customer_experience") if isinstance(settings, dict) else None
    try:
        return normalize_cx(raw)
    except ValueError:
        return default_cx()


def brand_colours(merchant: Any) -> dict[str, str | None]:
    profile = getattr(merchant, "profile", None) if merchant is not None else None
    settings = profile.get("settings") if isinstance(profile, dict) else None
    branding = settings.get("branding") if isinstance(settings, dict) else None
    branding = branding if isinstance(branding, dict) else {}
    return {
        "primary_color": sanitize_hex(branding.get("primary_color"), "#1e3a5f"),
        "accent_color": sanitize_hex(branding.get("accent_color"), "#f59e0b"),
    }

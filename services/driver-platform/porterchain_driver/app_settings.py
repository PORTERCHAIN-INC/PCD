"""Driver app settings (mobile Settings page), stored on driver.performance["app_settings"]."""

from __future__ import annotations

from typing import Any

_SETTING_KEYS = {
    "nav_app": {"google", "apple", "waze"},
    "language": {"en", "fr"},
}
_BOOL_KEYS = {"voice", "drive_mode_auto", "haptics", "notify_jobs", "notify_messages", "notify_route_changes", "notify_documents"}


def clean_settings(raw: dict) -> dict:
    out: dict = {}
    for key, allowed in _SETTING_KEYS.items():
        if raw.get(key) in allowed:
            out[key] = raw[key]
    for key in _BOOL_KEYS:
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    if isinstance(raw.get("text_scale"), (int, float)) and 0.85 <= raw["text_scale"] <= 1.6:
        out["text_scale"] = float(raw["text_scale"])
    if isinstance(raw.get("battery_saver_pct"), int) and 0 <= raw["battery_saver_pct"] <= 50:
        out["battery_saver_pct"] = raw["battery_saver_pct"]
    return out


def read_settings(driver: Any) -> dict:
    return clean_settings((driver.performance or {}).get("app_settings") or {})


def merge_settings(db: Any, driver: Any, raw: dict) -> dict:
    """Merge-update; unknown keys and bad values are dropped; other performance data kept."""
    perf = dict(driver.performance or {})
    merged = {**clean_settings(perf.get("app_settings") or {}), **clean_settings(raw or {})}
    perf["app_settings"] = merged
    driver.performance = perf
    db.flush()
    return merged

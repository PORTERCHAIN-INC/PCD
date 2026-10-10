"""Driver live-GPS switch (``system_config['driver_gps']``): global + per driver.

Off means: the driver app stops sending, pings are refused (nothing stored),
read paths (admin Live, customer tracking, ETA) see no position, and the
driver's Redis last-known pin is deleted at once (PIPEDA / GDPR minimal
retention). Breadcrumb history still ages out under ``dispatch_retention``.
"""

from __future__ import annotations

import time
from typing import Any

STORAGE_KEY = "driver_gps"
DRIVER_MESSAGE_OFF = (
    "Live location sharing is turned off by PorterChain. Your location is not being collected; "
    "keep updating each stop's status so customers see accurate progress."
)
DRIVER_MESSAGE_ON = (
    "PorterChain shares your live location only while you are on shift, to dispatch and track deliveries. "
    "Location history is deleted after the retention period."
)

CONSENT_VERSION = "2026-10"
CONSENT_TEXT = (
    "I agree that PorterChain collects my device location while I am on shift, to dispatch, "
    "route and track deliveries and show customers an ETA. Location is not collected off shift, "
    "live pins are deleted when sharing is turned off, and history is deleted after the retention "
    "period. I can withdraw by going off shift or contacting dispatch."
)

_CACHE: dict[str, Any] = {"at": 0.0, "value": None}
_TTL = 30.0


def default_driver_gps() -> dict[str, Any]:
    return {"enabled": True, "disabled_driver_ids": [], "require_consent": False}


def normalize_driver_gps(raw: Any) -> dict[str, Any]:
    if raw is not None and not isinstance(raw, dict):
        raise ValueError("driver_gps must be an object")
    src = raw or {}
    ids = src.get("disabled_driver_ids") or []
    if not isinstance(ids, list):
        raise ValueError("disabled_driver_ids must be a list")
    return {
        "enabled": bool(src.get("enabled", True)),
        "disabled_driver_ids": sorted({str(i) for i in ids if i}),
        "require_consent": bool(src.get("require_consent", False)),
    }


def set_policy_cache(value: dict[str, Any] | None) -> None:
    """Refresh after an admin save (and in tests)."""
    _CACHE["value"] = normalize_driver_gps(value) if value is not None else None
    _CACHE["at"] = time.monotonic() if value is not None else 0.0


def load_policy(db: Any | None = None) -> dict[str, Any]:
    if _CACHE["value"] is not None and time.monotonic() - _CACHE["at"] < _TTL:
        return _CACHE["value"]
    from porterchain_api.admin_models import SystemConfig

    value = default_driver_gps()
    try:
        if db is not None:
            row = db.get(SystemConfig, STORAGE_KEY)
            value = normalize_driver_gps(row.value if row else None)
        else:
            from porterchain_api.db import SessionLocal

            with SessionLocal() as s:
                row = s.get(SystemConfig, STORAGE_KEY)
                value = normalize_driver_gps(row.value if row else None)
    except Exception:  # noqa: BLE001 — policy read must never break GPS paths
        value = _CACHE["value"] or default_driver_gps()
    set_policy_cache(value)
    return value


def gps_enabled_for(driver_id: str | None, db: Any | None = None) -> bool:
    policy = load_policy(db)
    return (
        bool(policy["enabled"])
        and str(driver_id or "") not in policy["disabled_driver_ids"]
    )


def consent_of(driver: Any) -> dict[str, Any] | None:
    rec = ((getattr(driver, "documents", None) or {}).get("gps_consent")) or None
    return rec if isinstance(rec, dict) and rec.get("version") == CONSENT_VERSION else None


def record_consent(driver: Any, *, accepted: bool, source: str = "app") -> dict[str, Any]:
    """Store the driver's answer (timestamp, version, source) on the driver record."""
    from datetime import UTC, datetime

    docs = dict(driver.documents or {})
    rec = {
        "version": CONSENT_VERSION,
        "accepted": bool(accepted),
        "at": datetime.now(UTC).isoformat(),
        "source": source,
    }
    history = list(docs.get("gps_consent_history") or [])[-19:] + [rec]
    docs["gps_consent"] = rec if accepted else None
    docs["gps_consent_history"] = history
    driver.documents = docs
    return rec


def driver_gps_status(driver_id: str, db: Any | None = None, driver: Any | None = None) -> dict[str, Any]:
    on = gps_enabled_for(driver_id, db)
    consent = consent_of(driver) if driver is not None else None
    hist = ((getattr(driver, "documents", None) or {}).get("gps_consent_history")) or [] if driver is not None else []
    withdrawn = bool(hist) and hist[-1].get("accepted") is False  # withdrawal always stops collection
    needs = on and consent is None and (withdrawn or load_policy(db)["require_consent"])
    return {
        "enabled": on and not needs,
        "message": (CONSENT_TEXT if needs else DRIVER_MESSAGE_ON if on else DRIVER_MESSAGE_OFF),
        "consent_required": bool(needs),
        "consent": consent,
        "consent_version": CONSENT_VERSION,
        "consent_text": CONSENT_TEXT,
    }


def forget_positions(driver_ids: list[str]) -> int:
    """Delete Redis last-known pins for drivers whose GPS was switched off."""
    from porterchain_api.platform.last_known import LAST_KEY, _client

    client = _client()
    if client is None:
        return 0
    n = 0
    if driver_ids == ["*"]:
        try:
            driver_ids = [
                (k.decode() if isinstance(k, bytes) else k).split(":")[-1]
                for k in client.scan_iter(LAST_KEY.format(driver_id="*"))
            ]
        except Exception:  # noqa: BLE001
            return 0
    for d in driver_ids:
        try:
            n += int(client.delete(LAST_KEY.format(driver_id=d)) or 0)
        except Exception:  # noqa: BLE001
            pass
    return n

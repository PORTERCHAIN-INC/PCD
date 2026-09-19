"""Resolve driver document verification provenance (auto vs manual vs rules)."""

from __future__ import annotations

from typing import Any

from porterchain_api.admin_models import Driver

_AUTO_SOURCES = frozenset({"auto", "rules", "auto_pending"})
_BACKGROUND_PASSED = frozenset({"passed", "cleared", "approved"})


def doc_entry(driver: Driver, key: str) -> dict[str, Any]:
    docs = getattr(driver, "documents", None) or {}
    entry = docs.get(key) if isinstance(docs, dict) else None
    return dict(entry) if isinstance(entry, dict) else {}


def resolve_source(entry: dict[str, Any] | None) -> str:
    """Return auto | rules | manual | unknown for ops badges."""
    if not isinstance(entry, dict) or not entry:
        return "unknown"
    raw = str(entry.get("verification_source") or "").lower().strip()
    if raw in _AUTO_SOURCES:
        return "rules" if raw == "rules" else "auto"
    if raw == "manual":
        return "manual"
    if entry.get("provider") in {"stripe_identity", "checkr"}:
        return "auto"
    if entry.get("provider") == "ontario_abstract":
        return "rules"
    if entry.get("verified") or entry.get("status") in {"verified", "cleared", "passed"}:
        return "manual"
    return "unknown"


def is_provider_verified(entry: dict[str, Any] | None) -> bool:
    source = resolve_source(entry)
    if source not in {"auto", "rules"}:
        return False
    if not isinstance(entry, dict):
        return False
    return bool(entry.get("verified")) or str(entry.get("status") or "").lower() in {
        "verified",
        "cleared",
        "passed",
        "approved",
    }


def verification_sources_payload(driver: Driver) -> dict[str, dict[str, Any]]:
    keys = ("license", "insurance", "vehicle_registration", "background_check", "abstract")
    out: dict[str, dict[str, Any]] = {}
    for key in keys:
        entry = doc_entry(driver, key)
        source = resolve_source(entry)
        verified = bool(entry.get("verified"))
        if key == "license":
            verified = bool(driver.license_verified)
        elif key == "insurance":
            verified = bool(driver.insurance_verified)
        elif key == "vehicle_registration":
            verified = bool(driver.vehicle_verified)
        elif key == "background_check":
            verified = str(driver.background_check_status or "").lower() in _BACKGROUND_PASSED
        out[key] = {
            "source": source,
            "provider": entry.get("provider"),
            "verified": verified,
            "status": entry.get("status"),
            "verification_source": entry.get("verification_source"),
        }
    return out


def mark_manual_source(driver: Driver, portal_key: str) -> None:
    """Admin toggles are explicit manual provenance."""
    from sqlalchemy.orm.attributes import flag_modified
    from sqlalchemy.orm.exc import UnmappedInstanceError

    docs = dict(getattr(driver, "documents", None) or {})
    entry = dict(docs.get(portal_key) or {}) if isinstance(docs.get(portal_key), dict) else {}
    entry["verification_source"] = "manual"
    entry["provider"] = entry.get("provider") or "admin"
    docs[portal_key] = entry
    driver.documents = docs
    try:
        flag_modified(driver, "documents")
    except (UnmappedInstanceError, AttributeError):
        pass

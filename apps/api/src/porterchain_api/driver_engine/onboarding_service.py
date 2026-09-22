"""Driver onboarding gate — Clerk invite, admin approval, compliance verification."""

from __future__ import annotations

from typing import Any, Literal

from porterchain_api.admin_models import Driver
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.user_sync_service import _is_pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus

OnboardingStepId = Literal[
    "clerk_account",
    "admin_approval",
    "license_verified",
    "insurance_verified",
    "vehicle_verified",
    "background_check",
    "documents_uploaded",
    "abstract_verified",
]

_REQUIRED_DOC_TYPES = ("license", "insurance", "vehicle_registration")
_BACKGROUND_PASSED = frozenset({"passed", "cleared", "approved"})
_DOC_TYPE_ALIASES: dict[str, frozenset[str]] = {
    "license": frozenset({"license", "driver_license", "drivers_license"}),
    "insurance": frozenset({"insurance", "insurance_certificate"}),
    "vehicle_registration": frozenset({"vehicle_registration", "vehicle_reg", "registration"}),
}


def _doc_step_status(driver: Driver, key: str, verified: bool) -> str:
    if verified:
        return "complete"
    entry = (driver.documents or {}).get(key)
    if isinstance(entry, dict):
        status = str(entry.get("status") or "")
        if status in {"rejected", "expired"}:
            return status
    return "pending_review"


def _doc_rejection(driver: Driver, key: str) -> str | None:
    entry = (driver.documents or {}).get(key)
    if isinstance(entry, dict) and entry.get("status") == "rejected":
        reason = entry.get("rejection_reason")
        return str(reason) if reason else None
    return None


def _has_doc_file(driver: Driver, category: str) -> bool:
    docs = driver.documents or {}
    entry = docs.get(category)
    if isinstance(entry, dict) and (entry.get("url") or entry.get("file_url")):
        return True
    aliases = _DOC_TYPE_ALIASES.get(category, frozenset({category}))
    for file_entry in docs.get("files") or []:
        if not isinstance(file_entry, dict):
            continue
        doc_type = str(file_entry.get("doc_type") or "").lower()
        if doc_type not in aliases and not any(alias in doc_type for alias in aliases):
            continue
        if file_entry.get("file_url") or file_entry.get("url"):
            return True
    return False


def _compliance_docs_complete(driver: Driver) -> bool:
    """Admin verification implies documents were reviewed; else require uploads."""
    if driver.license_verified and driver.insurance_verified and driver.vehicle_verified:
        return True
    return all(_has_doc_file(driver, key) for key in _REQUIRED_DOC_TYPES)


def _doc_uploaded(driver: Driver, doc_type: str) -> bool:
    return _has_doc_file(driver, doc_type)


def evaluate_driver_onboarding(driver: Driver, *, settings: Settings | None = None) -> dict[str, Any]:
    """Return structured onboarding checklist for driver portal gate."""
    clerk_linked = not _is_pending_clerk_id(driver.clerk_user_id)
    if settings and allow_auth_dev_bypass(settings):
        clerk_linked = True
    status = driver.status or DriverStatus.PENDING.value
    bg_status = (driver.background_check_status or "pending").lower()

    docs_uploaded = _compliance_docs_complete(driver)
    missing_docs = [key for key in _REQUIRED_DOC_TYPES if not _has_doc_file(driver, key)]

    steps: list[dict[str, Any]] = [
        {
            "id": "clerk_account",
            "label": "Clerk account connected",
            "description": "Accept your Porterchain driver invitation and sign in with the email we invited.",
            "complete": clerk_linked,
            "status": "complete" if clerk_linked else "pending",
        },
        {
            "id": "admin_approval",
            "label": "Admin authorization",
            "description": "Operations must approve your driver profile before you can work.",
            "complete": status == DriverStatus.APPROVED.value,
            "status": (
                "complete"
                if status == DriverStatus.APPROVED.value
                else "rejected"
                if status == DriverStatus.REJECTED.value
                else "suspended"
                if status == DriverStatus.SUSPENDED.value
                else "pending"
            ),
            "reason": (
                ((driver.documents or {}).get("account_rejection") or {}).get("reason")
                if isinstance((driver.documents or {}).get("account_rejection"), dict)
                and status == DriverStatus.REJECTED.value
                else None
            ),
        },
        {
            "id": "documents_uploaded",
            "label": "Compliance documents submitted",
            "description": "Upload license, insurance, and vehicle registration in Profile.",
            "complete": docs_uploaded,
            "status": "complete" if docs_uploaded else "pending",
            "missing": missing_docs,
        },
        {
            "id": "license_verified",
            "label": "Driver license verified",
            "description": (
                "Verify your license with photo ID + selfie (automated when enabled), "
                "or wait for operations review."
                if settings and settings.driver_identity_verification_enabled
                else "Admin reviews and verifies your license document."
            ),
            "complete": bool(driver.license_verified),
            "status": _doc_step_status(driver, "license", bool(driver.license_verified)),
            "reason": _doc_rejection(driver, "license"),
        },
        {
            "id": "insurance_verified",
            "label": "Insurance verified",
            "description": "Admin verifies your insurance certificate.",
            "complete": bool(driver.insurance_verified),
            "status": _doc_step_status(driver, "insurance", bool(driver.insurance_verified)),
            "reason": _doc_rejection(driver, "insurance"),
        },
        {
            "id": "vehicle_verified",
            "label": "Vehicle verified",
            "description": "Admin verifies your vehicle registration and details.",
            "complete": bool(driver.vehicle_verified),
            "status": _doc_step_status(driver, "vehicle_registration", bool(driver.vehicle_verified)),
            "reason": _doc_rejection(driver, "vehicle_registration"),
        },
        {
            "id": "background_check",
            "label": "Background check cleared",
            "description": (
                "Complete Checkr screening after your license is verified "
                "(automated when enabled), or wait for operations clearance."
                if settings and settings.driver_background_check_enabled
                else "Background screening must be cleared by operations."
            ),
            "complete": bg_status in _BACKGROUND_PASSED,
            "status": "complete" if bg_status in _BACKGROUND_PASSED else bg_status,
        },
    ]

    if settings and settings.driver_abstract_verification_enabled:
        abstract = (driver.documents or {}).get("abstract") if isinstance(driver.documents, dict) else {}
        abstract_ok = isinstance(abstract, dict) and bool(abstract.get("verified"))
        steps.append(
            {
                "id": "abstract_verified",
                "label": "Ontario driver abstract verified",
                "description": "Submit your MTO abstract details (class, demerits, suspensions) for rule checks.",
                "complete": abstract_ok,
                "status": "complete" if abstract_ok else (
                    str(abstract.get("status")) if isinstance(abstract, dict) and abstract.get("status") else "pending"
                ),
            }
        )

    blockers = [s["id"] for s in steps if not s["complete"]]
    ready = len(blockers) == 0

    if status == DriverStatus.SUSPENDED.value:
        ready = False
        blockers = ["account_suspended"]
    elif status == DriverStatus.REJECTED.value:
        ready = False
        blockers = ["account_rejected"]

    return {
        "ready": ready,
        "blockers": blockers,
        "status": status,
        "clerk_linked": clerk_linked,
        "steps": steps,
        "pending_documents": len(missing_docs),
        "can_access_portal": ready,
    }


def require_fully_onboarded_driver(driver: Driver, *, settings: Settings | None = None) -> None:
    """Raise PermissionError when driver cannot access operational portal."""
    snapshot = evaluate_driver_onboarding(driver, settings=settings)
    if snapshot["ready"]:
        return
    blockers = snapshot.get("blockers") or ["onboarding_incomplete"]
    raise PermissionError(f"driver_onboarding_blocked:{','.join(blockers)}")

"""D-25 — admin driver docs mirror the portal keyed schema."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Driver

if TYPE_CHECKING:
    from porterchain_api.schemas_admin import DriverDocumentInput


_PORTAL_REVIEW_KEYS: tuple[tuple[str, str], ...] = (
    ("license", "Driver license"),
    ("insurance", "Insurance"),
    ("vehicle_registration", "Vehicle registration"),
    ("background_check", "Background check"),
    ("abstract", "Ontario driver abstract"),
    ("training_certificate", "Training certificate"),
)


def admin_review_files(docs: dict | None) -> list[dict]:
    """Files the admin Documents tab can open.

    Mobile uploads write ``documents[doc_type].url`` (and ``vehicle_photos``).
    The admin Add-document form writes ``documents.files[].file_url``. Both
    shapes must appear in the review list.
    """
    payload = docs or {}
    files = payload.get("files") or []
    out: list[dict] = []
    seen: set[str] = set()
    if isinstance(files, list):
        for raw in files:
            if not isinstance(raw, dict):
                continue
            item = dict(raw)
            url = item.get("file_url") or item.get("url")
            if url and not item.get("file_url"):
                item["file_url"] = url
            key = portal_doc_key(str(item.get("doc_type") or ""))
            if key and url:
                seen.add(key)
            out.append(item)
    for key, label in _PORTAL_REVIEW_KEYS:
        if key in seen:
            continue
        entry = payload.get(key)
        if not isinstance(entry, dict):
            continue
        url = entry.get("url") or entry.get("file_url")
        if not url:
            continue
        out.append(
            {
                "id": key,
                "doc_type": key,
                "label": label,
                "file_url": url,
                "status": entry.get("status") or "pending_review",
                "verified": bool(entry.get("verified")),
                "rejection_reason": entry.get("rejection_reason"),
                "uploaded_at": entry.get("uploaded_at"),
                "expires_at": entry.get("expires_at"),
                "reference_number": entry.get("reference_number") or entry.get("policy_number"),
                "notes": entry.get("notes"),
            }
        )
    photos = payload.get("vehicle_photos") or []
    if isinstance(photos, list):
        for index, photo in enumerate(photos):
            if not isinstance(photo, dict):
                continue
            url = photo.get("url") or photo.get("file_url")
            if not url:
                continue
            out.append(
                {
                    "id": photo.get("id") or f"vehicle_photo_{index}",
                    "doc_type": "vehicle_photo",
                    "label": photo.get("label") or f"Vehicle photo {index + 1}",
                    "file_url": url,
                    "status": photo.get("status") or "pending_review",
                    "verified": bool(photo.get("verified")),
                    "rejection_reason": photo.get("rejection_reason"),
                    "uploaded_at": photo.get("uploaded_at"),
                }
            )
    return out


def portal_doc_key(doc_type: str) -> str | None:
    raw = (doc_type or "").lower().strip()
    mapping = {
        "license": "license",
        "driver_license": "license",
        "drivers_license": "license",
        "insurance": "insurance",
        "insurance_certificate": "insurance",
        "vehicle_registration": "vehicle_registration",
        "vehicle_reg": "vehicle_registration",
        "registration": "vehicle_registration",
        "background_check": "background_check",
        "abstract": "abstract",
        "driver_abstract": "abstract",
        "mto_abstract": "abstract",
    }
    return mapping.get(raw)


def assign_blockers(driver: Driver, *, active_vehicle_count: int) -> list[str]:
    """Sentences the admin header and Orders tab can show without re-coding dispatch rules."""
    from porterchain_api.domain.admin_states import DriverStatus
    from porterchain_api.driver_engine.verification_sources import doc_entry

    blockers: list[str] = []
    if (driver.status or "") != DriverStatus.APPROVED.value:
        blockers.append("Driver is not approved.")
    expired = {
        "license": "License is expired.",
        "insurance": "Insurance is expired.",
        "vehicle_registration": "Vehicle registration is expired.",
    }
    for key, sentence in expired.items():
        entry = doc_entry(driver, key)
        if str(entry.get("status") or "").lower() == "expired":
            blockers.append(sentence)
    if not driver.license_verified and "License is expired." not in blockers:
        blockers.append("License is not verified.")
    if not driver.insurance_verified and "Insurance is expired." not in blockers:
        blockers.append("Insurance is not verified.")
    bg = str(driver.background_check_status or "").lower()
    if bg not in {"passed", "cleared", "approved"}:
        blockers.append("Background check is not passed.")
    if active_vehicle_count <= 0:
        blockers.append("No active vehicle.")
    return blockers


def decide_document(
    db: Session,
    ctx: AdminContext,
    driver: Driver,
    *,
    doc_type: str,
    decision: str,
    reason: str | None = None,
    audit,
) -> None:
    """Verify or reject one compliance document. Does not change driver account status."""
    from porterchain_api.driver_engine.verification_sources import mark_manual_source

    key = portal_doc_key(doc_type)
    if key is None:
        raise ValueError("invalid_doc_type")
    if decision not in {"verified", "rejected", "cleared"}:
        raise ValueError("invalid_decision")
    note = (reason or "").strip()
    if decision == "rejected" and not note:
        raise ValueError("reason_required")

    docs = dict(driver.documents or {})
    entry = docs.get(key)
    entry = dict(entry) if isinstance(entry, dict) else {}
    verified = decision == "verified"
    entry["verified"] = verified
    if decision == "verified":
        entry["status"] = "verified"
        entry.pop("rejection_reason", None)
    elif decision == "rejected":
        entry["status"] = "rejected"
        entry["rejection_reason"] = note
    else:
        has_file = bool(entry.get("url") or entry.get("file_url"))
        entry["status"] = "pending_review" if has_file else "missing"
        entry.pop("rejection_reason", None)
    docs[key] = entry

    aliases = {
        "license": {"license", "driver_license", "drivers_license"},
        "insurance": {"insurance", "insurance_certificate"},
        "vehicle_registration": {"vehicle_registration", "vehicle_reg", "registration"},
        "background_check": {"background_check"},
        "abstract": {"abstract", "driver_abstract", "mto_abstract"},
    }.get(key, {key})
    updated_files = []
    for file_entry in list(docs.get("files") or []):
        if not isinstance(file_entry, dict):
            updated_files.append(file_entry)
            continue
        found = str(file_entry.get("doc_type") or "").lower()
        if found in aliases or any(alias in found for alias in aliases):
            file_entry = {**file_entry, "status": entry["status"], "verified": verified}
            if decision == "rejected":
                file_entry["rejection_reason"] = note
            else:
                file_entry.pop("rejection_reason", None)
        updated_files.append(file_entry)
    if updated_files or docs.get("files"):
        docs["files"] = updated_files
    driver.documents = docs

    if key == "license":
        driver.license_verified = verified
    elif key == "insurance":
        driver.insurance_verified = verified
    elif key == "vehicle_registration":
        driver.vehicle_verified = verified
    elif key == "background_check":
        driver.background_check_status = (
            "passed" if verified else "failed" if decision == "rejected" else "pending"
        )
    elif key == "abstract":
        pass
    mark_manual_source(driver, key)
    audit(
        db,
        ctx,
        "driver.document_decided",
        "driver",
        driver.id,
        {"doc_type": key, "decision": decision, "reason": note or None},
    )


def document_entry(body: DriverDocumentInput, ctx: AdminContext) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "doc_type": body.doc_type,
        "label": body.label or body.doc_type.replace("_", " ").title(),
        "file_url": body.file_url,
        "reference_number": body.reference_number,
        "expires_at": body.expires_at.isoformat() if body.expires_at else None,
        "notes": body.notes,
        "status": "pending_review",
        "verified": False,
        "uploaded_at": datetime.now(UTC).isoformat(),
        "uploaded_by": ctx.user.id if ctx.user else None,
    }


def sync_portal_doc_status(
    driver: Driver,
    portal_key: str,
    *,
    verified: bool,
    status: str | None = None,
) -> None:
    """Keep portal keyed docs (license/insurance/…) in sync with Admin verify toggles (D-25)."""
    docs = dict(driver.documents or {})
    entry = docs.get(portal_key)
    if not isinstance(entry, dict):
        entry = {}
    entry["verified"] = verified
    entry["status"] = status or ("verified" if verified else "pending_review")
    docs[portal_key] = entry
    files = list(docs.get("files") or [])
    aliases = {
        "license": {"license", "driver_license", "drivers_license"},
        "insurance": {"insurance", "insurance_certificate"},
        "vehicle_registration": {"vehicle_registration", "vehicle_reg", "registration"},
        "background_check": {"background_check"},
        "abstract": {"abstract", "driver_abstract", "mto_abstract"},
    }.get(portal_key, {portal_key})
    updated_files = []
    for f in files:
        if not isinstance(f, dict):
            updated_files.append(f)
            continue
        doc_type = str(f.get("doc_type") or "").lower()
        if doc_type in aliases or any(a in doc_type for a in aliases):
            f = {**f, "status": entry["status"], "verified": verified}
        updated_files.append(f)
    docs["files"] = updated_files
    driver.documents = docs
    from sqlalchemy.orm import object_session
    from sqlalchemy.orm.exc import UnmappedInstanceError

    from porterchain_api.driver_engine.document_store import sync_document_status

    try:
        session = object_session(driver)
    except UnmappedInstanceError:
        session = None
    if session is not None:
        sync_document_status(
            session,
            driver.id,
            portal_key,
            verified=verified,
            status=status or ("verified" if verified else "pending_review"),
        )


def add_document(svc, db: Session, ctx: AdminContext, driver_id: str, body: DriverDocumentInput) -> Driver:
    driver = svc._get_or_raise(db, driver_id)
    docs = dict(driver.documents or {})
    files = list(docs.get("files") or [])
    entry = svc._document_entry(body, ctx)
    files.append(entry)
    docs["files"] = files
    key = svc._portal_doc_key(body.doc_type)
    if key:
        docs[key] = {
            "status": "pending_review",
            "verified": False,
            "url": body.file_url,
            "uploaded_at": entry["uploaded_at"],
            "reference_number": body.reference_number,
            "expires_at": entry.get("expires_at"),
            "notes": body.notes,
        }
    driver.documents = docs
    from porterchain_api.driver_engine.document_store import record_document

    record_document(
        db,
        driver_id=driver_id,
        doc_type=body.doc_type,
        label=entry.get("label"),
        file_url=body.file_url,
        reference_number=body.reference_number,
        status="pending_review",
        expires_at=body.expires_at,
        notes=body.notes,
        uploaded_by=ctx.user.id if ctx.user else None,
        flush=False,
    )
    svc._audit(
        db,
        ctx,
        "driver.document_added",
        "driver",
        driver_id,
        {"doc_type": body.doc_type, "label": body.label},
    )
    db.commit()
    db.refresh(driver)
    return driver


def update_verification(
    svc,
    db: Session,
    ctx: AdminContext,
    driver_id: str,
    *,
    license_verified: bool | None = None,
    medical_transport_certified: bool | None = None,
    insurance_verified: bool | None = None,
    vehicle_verified: bool | None = None,
    background_check_status: str | None = None,
) -> Driver:
    from porterchain_api.driver_engine.verification_sources import mark_manual_source

    driver = svc._get_or_raise(db, driver_id)
    if license_verified is not None:
        driver.license_verified = license_verified
        svc._sync_portal_doc_status(driver, "license", verified=license_verified)
        mark_manual_source(driver, "license")
    if medical_transport_certified is not None:
        driver.medical_transport_certified = medical_transport_certified
    if insurance_verified is not None:
        driver.insurance_verified = insurance_verified
        svc._sync_portal_doc_status(driver, "insurance", verified=insurance_verified)
        mark_manual_source(driver, "insurance")
    if vehicle_verified is not None:
        driver.vehicle_verified = vehicle_verified
        svc._sync_portal_doc_status(driver, "vehicle_registration", verified=vehicle_verified)
        mark_manual_source(driver, "vehicle_registration")
    if background_check_status:
        driver.background_check_status = background_check_status
        passed = background_check_status.lower() in {"passed", "cleared", "approved"}
        svc._sync_portal_doc_status(
            driver,
            "background_check",
            verified=passed,
            status="verified" if passed else background_check_status.lower(),
        )
        mark_manual_source(driver, "background_check")
    db.commit()
    db.refresh(driver)
    return driver

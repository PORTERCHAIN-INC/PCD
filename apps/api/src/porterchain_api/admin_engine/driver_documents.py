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

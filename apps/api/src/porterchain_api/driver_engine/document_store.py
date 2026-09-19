"""Driver document table writes owned by driver_engine."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from porterchain_api.driver_models import DriverDocument


def record_document(
    db: Session,
    *,
    driver_id: str,
    doc_type: str,
    label: str | None = None,
    file_url: str | None = None,
    reference_number: str | None = None,
    status: str = "pending_review",
    verified: bool = False,
    expires_at: datetime | None = None,
    notes: str | None = None,
    uploaded_by: str | None = None,
    flush: bool = True,
) -> DriverDocument:
    row = DriverDocument(
        driver_id=driver_id,
        doc_type=doc_type,
        label=label,
        file_url=file_url,
        reference_number=reference_number,
        status=status,
        verified=verified,
        expires_at=expires_at,
        notes=notes,
        uploaded_by=uploaded_by,
    )
    db.add(row)
    if flush:
        db.flush()
    return row


def sync_document_status(
    db: Session,
    driver_id: str,
    doc_type: str,
    *,
    verified: bool,
    status: str | None = None,
) -> None:
    rows = (
        db.query(DriverDocument)
        .filter(DriverDocument.driver_id == driver_id, DriverDocument.doc_type == doc_type)
        .all()
    )
    next_status = status or ("verified" if verified else "pending_review")
    for row in rows:
        row.verified = verified
        row.status = next_status

"""Merchant document vault + support rollup (tickets, claims, exceptions).

PIPEDA / GDPR: documents are kept only while needed (``expires_on``), every
download is written to the merchant audit log, deletion wipes the bytes
immediately (row kept as a tombstone for the audit trail), and merchant
erasure purges all document bytes (see ``purge_documents``).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import MerchantDocument

KINDS: dict[str, str] = {
    "insurance_coi": "Certificate of insurance",
    "signed_contract": "Signed contract",
    "tax_form": "HST / tax form",
    "rate_sheet": "Rate sheet",
    "onboarding": "Onboarding form",
    "other": "Other",
}
ALLOWED_TYPES: dict[str, bytes] = {
    "application/pdf": b"%PDF",
    "image/png": b"\x89PNG",
    "image/jpeg": b"\xff\xd8\xff",
}
MAX_BYTES = 10 * 1024 * 1024
MAX_PER_MERCHANT = 100


def _row(doc: MerchantDocument) -> dict[str, Any]:
    today = date.today()
    return {
        "id": doc.id,
        "kind": doc.kind,
        "kind_label": KINDS.get(doc.kind, doc.kind),
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size_bytes": doc.size_bytes,
        "expires_on": doc.expires_on.isoformat() if doc.expires_on else None,
        "expired": bool(doc.expires_on and doc.expires_on < today),
        "note": doc.note,
        "uploaded_by": doc.uploaded_by,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


def list_documents(db: Session, merchant_id: str) -> list[dict[str, Any]]:
    rows = (
        db.query(MerchantDocument)
        .filter(MerchantDocument.merchant_id == merchant_id, MerchantDocument.deleted_at.is_(None))
        .order_by(MerchantDocument.created_at.desc())
        .all()
    )
    return [_row(r) for r in rows]


def _safe_name(name: str) -> str:
    keep = "".join(c for c in (name or "document") if c.isalnum() or c in "._- ")
    return (keep.strip() or "document")[:120]


def upload_document(
    db: Session,
    ctx: Any,
    merchant_id: str,
    *,
    kind: str,
    filename: str,
    content_type: str,
    data: bytes,
    expires_on: date | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    from porterchain_api.merchant_engine.account_ops import get_merchant, staff_audit

    get_merchant(db, merchant_id)
    if kind not in KINDS:
        raise ValueError("document_kind_invalid")
    ctype = (content_type or "").split(";")[0].strip().lower()
    magic = ALLOWED_TYPES.get(ctype)
    if magic is None:
        raise ValueError("document_type_not_allowed")
    if not data or len(data) > MAX_BYTES:
        raise ValueError("document_size_invalid")
    if not data.startswith(magic):
        raise ValueError("document_content_mismatch")
    count = (
        db.query(MerchantDocument)
        .filter(MerchantDocument.merchant_id == merchant_id, MerchantDocument.deleted_at.is_(None))
        .count()
    )
    if count >= MAX_PER_MERCHANT:
        raise ValueError("document_limit_reached")
    doc = MerchantDocument(
        merchant_id=merchant_id,
        kind=kind,
        filename=_safe_name(filename),
        content_type=ctype,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        content=data,
        expires_on=expires_on,
        note=(note or "").strip()[:255] or None,
        uploaded_by=f"admin:{ctx.user.id}",
    )
    db.add(doc)
    db.flush()
    staff_audit(
        db, ctx, merchant_id, action="document.uploaded", resource_type="document", resource_id=doc.id,
        payload={"changes": {"document": {"old": None, "new": f"{KINDS[kind]}: {doc.filename}"}}},
    )
    return _row(doc)


def read_document(db: Session, ctx: Any, merchant_id: str, doc_id: str) -> tuple[MerchantDocument, bytes]:
    from porterchain_api.merchant_engine.account_ops import staff_audit
    doc = (
        db.query(MerchantDocument)
        .filter(
            MerchantDocument.id == doc_id,
            MerchantDocument.merchant_id == merchant_id,
            MerchantDocument.deleted_at.is_(None),
        )
        .first()
    )
    if not doc or doc.content is None:
        raise LookupError("document_not_found")
    staff_audit(
        db, ctx, merchant_id, action="document.downloaded", resource_type="document", resource_id=doc.id,
        payload={"filename": doc.filename},
    )
    return doc, bytes(doc.content)


def delete_document(db: Session, ctx: Any, merchant_id: str, doc_id: str, *, reason: str | None) -> None:
    from porterchain_api.merchant_engine.account_ops import staff_audit
    doc = (
        db.query(MerchantDocument)
        .filter(MerchantDocument.id == doc_id, MerchantDocument.merchant_id == merchant_id)
        .first()
    )
    if not doc or doc.deleted_at is not None:
        raise LookupError("document_not_found")
    doc.content = None  # bytes gone now; the tombstone keeps the audit trail
    doc.deleted_at = datetime.now(UTC)
    staff_audit(
        db, ctx, merchant_id, action="document.deleted", resource_type="document", resource_id=doc.id,
        payload={"reason": (reason or "").strip() or None,
                 "changes": {"document": {"old": doc.filename, "new": None}}},
    )


def purge_documents(db: Session, merchant_id: str) -> int:
    """Erasure: drop every document's bytes and filename. Returns rows purged."""
    n = 0
    now = datetime.now(UTC)
    for doc in db.query(MerchantDocument).filter(MerchantDocument.merchant_id == merchant_id).all():
        doc.content = None
        doc.filename = "erased"
        doc.note = None
        doc.deleted_at = doc.deleted_at or now
        n += 1
    return n

"""Shared booking-attachment engine (merchant, customer, driver, staff).

Rules
- Types: PDF, PNG, JPEG, HEIC/HEIF. Checked by magic bytes, not by the browser's
  claimed type. Max 10 MB, 10 files per booking.
- PDFs carrying active content (/JavaScript, /JS, /Launch, /EmbeddedFile) are
  refused. If a ClamAV daemon is reachable (CLAMD_HOST), the bytes are also scanned.
- Owners (merchant or customer on the booking) add/edit/remove until that stop
  is done. The assigned driver sees only the stop they are on. Staff see all.
- ``required_at_stop`` adds a "Show document to warehouse staff" step the driver
  must confirm before Picked up.
- Location templates: saved once against a pickup address (e.g. Milton warehouse)
  and attached automatically to every later booking from that address.
- Retention (PIPEDA): bytes and proof photos are wiped RETENTION_DAYS after the
  booking reaches a terminal state; the metadata row stays for the audit trail.
- Every upload, view, download, shown, delete and purge is written to
  booking_attachment_events.
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_attachment_models import (
    BookingAttachment,
    BookingAttachmentEvent,
)
from porterchain_api.booking_models import Order

KINDS: dict[str, str] = {
    "pickup_authorization": "Pickup authorization",
    "bill_of_lading": "Bill of lading",
    "delivery_instructions": "Delivery instructions",
    "customs": "Customs / other",
}
DEFAULT_STOP = {
    "pickup_authorization": "pickup",
    "bill_of_lading": "pickup",
    "delivery_instructions": "dropoff",
    "customs": "pickup",
}
MAX_BYTES = 10 * 1024 * 1024
MAX_PER_ORDER = 10
RETENTION_DAYS = 90
STOPS = ("pickup", "dropoff")

PICKUP_DONE = {
    "PICKED_UP", "IN_TRANSIT", "AT_DESTINATION", "DELIVERED", "POD_COMPLETED",
    "INVOICED", "CLOSED", "CANCELLED", "FAILED", "RETURNED",
}
DROPOFF_DONE = {"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "FAILED", "RETURNED"}
TERMINAL = {"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "FAILED", "RETURNED"}

_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("bill_of_lading", ("bol", "bill of lading", "bill-of-lading", "lading", "waybill")),
    ("customs", ("customs", "cbsa", "b3", "commercial invoice", "ci5", "usmca", "cusma")),
    ("delivery_instructions", ("delivery", "instructions", "dropoff", "drop-off", "receiving", "consignee")),
    ("pickup_authorization", ("pickup", "pick-up", "pick up", "release", "authorization", "authorisation",
                              "warehouse", "collection", "pu ")),
]


class AttachmentError(ValueError):
    pass


class PickupDocumentNotShown(Exception):
    """Pickup can't be confirmed until required documents were shown."""

    def __init__(self, missing: list[dict[str, Any]]):
        self.payload = {
            "code": "pickup_document_not_shown",
            "message": "Show the pickup document to warehouse staff, then tap Shown to staff.",
            "documents": missing,
        }
        super().__init__(self.payload["message"])


# ── detection ────────────────────────────────────────────────────────────

def sniff_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) > 12 and data[4:8] == b"ftyp" and data[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"heif", b"hevc"):
        return "image/heic"
    return None


_ACTIVE_PDF = re.compile(rb"/(JavaScript|JS|Launch|EmbeddedFile|OpenAction\s*<<[^>]*/JS)\b")


def _clamd_scan(data: bytes) -> str | None:
    """Returns a signature name if infected, None if clean or no scanner configured."""
    host = os.environ.get("CLAMD_HOST")
    if not host:
        return None
    port = int(os.environ.get("CLAMD_PORT", "3310"))
    try:
        with socket.create_connection((host, port), timeout=5) as s:
            s.sendall(b"zINSTREAM\0")
            for i in range(0, len(data), 64 * 1024):
                chunk = data[i : i + 64 * 1024]
                s.sendall(len(chunk).to_bytes(4, "big") + chunk)
            s.sendall(b"\0\0\0\0")
            reply = s.recv(4096).decode(errors="ignore")
    except OSError:
        return None  # scanner down: type + active-content checks still apply
    return reply.split("FOUND")[0].split(":")[-1].strip() if "FOUND" in reply else None


def validate_file(data: bytes) -> str:
    if not data:
        raise AttachmentError("attachment_empty")
    if len(data) > MAX_BYTES:
        raise AttachmentError("attachment_too_large")
    ctype = sniff_type(data)
    if ctype is None:
        raise AttachmentError("attachment_type_not_allowed")
    if ctype == "application/pdf" and _ACTIVE_PDF.search(data):
        raise AttachmentError("attachment_active_content")
    if _clamd_scan(data):
        raise AttachmentError("attachment_malware_detected")
    return ctype


def suggest_kind(filename: str, data: bytes | None = None) -> str:
    text = (filename or "").lower().replace("_", " ")
    if data and data.startswith(b"%PDF"):
        # Cheap peek at uncompressed text objects; good enough for a suggestion.
        text += " " + data[:200_000].decode("latin-1", errors="ignore").lower()
    for kind, words in _KEYWORDS:
        if any(w in text for w in words):
            return kind
    return "pickup_authorization"


def location_key(addr: Any) -> str | None:
    if not isinstance(addr, dict):
        return None
    street = addr.get("street") or addr.get("line1") or addr.get("address") or addr.get("formatted") or ""
    postal = addr.get("postal_code") or addr.get("postal") or addr.get("zip") or ""
    street = re.sub(r"[^a-z0-9]", "", str(street).lower().split(",")[0])
    postal = re.sub(r"[^a-z0-9]", "", str(postal).lower())
    unit = re.sub(r"[^a-z0-9]", "", str(addr.get("unit") or addr.get("line2") or "").lower())
    key = "|".join(p for p in (street, unit, postal) if p)
    return key or None


def _safe_name(name: str) -> str:
    keep = "".join(c for c in (name or "document") if c.isalnum() or c in "._- ")
    return (keep.strip() or "document")[:120]


def _now() -> datetime:
    return datetime.now(UTC)


def _event(db: Session, att: BookingAttachment, actor_type: str, actor_id: str | None, action: str,
           order_id: str | None = None, **payload: Any) -> None:
    db.add(BookingAttachmentEvent(
        attachment_id=att.id, order_id=order_id or att.order_id, actor_type=actor_type,
        actor_id=actor_id, action=action, payload=payload,
    ))


def row(att: BookingAttachment, *, for_owner: bool = True) -> dict[str, Any]:
    status = "shown_at_pickup" if att.shown_at else ("viewed_by_driver" if att.first_viewed_by_driver_at else "waiting")
    out = {
        "id": att.id,
        "order_id": att.order_id,
        "stop": att.stop,
        "kind": att.kind,
        "kind_label": KINDS.get(att.kind, att.kind),
        "filename": att.filename,
        "content_type": att.content_type,
        "size_bytes": att.size_bytes,
        "note": att.note,
        "required_at_stop": bool(att.required_at_stop),
        "is_location_template": bool(att.is_location_template),
        "from_location_template": bool(att.source_template_id),
        "status": status,
        "viewed_at": att.first_viewed_by_driver_at.isoformat() if att.first_viewed_by_driver_at else None,
        "shown_at": att.shown_at.isoformat() if att.shown_at else None,
        "has_proof_photo": att.proof_content is not None,
        "purged": att.purged_at is not None,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }
    if not for_owner:
        out.pop("is_location_template")
    return out


# ── owner side (merchant / customer) ─────────────────────────────────────

def _owner_filter(q, owner_type: str, owner_id: str):
    col = BookingAttachment.merchant_id if owner_type == "merchant" else BookingAttachment.customer_id
    return q.filter(col == owner_id)


def owned_order(db: Session, owner_type: str, owner_id: str, order_id: str) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise LookupError("order_not_found")
    owner = order.merchant_id if owner_type == "merchant" else order.customer_id
    if owner != owner_id:
        raise LookupError("order_not_found")  # don't reveal other people's bookings
    return order


def _stop_open(order: Order, stop: str) -> bool:
    done = PICKUP_DONE if stop == "pickup" else DROPOFF_DONE
    return order.state not in done


def sync_location_templates(db: Session, order: Order) -> None:
    """Attach saved location documents to this booking (idempotent)."""
    if not order.merchant_id and not order.customer_id:
        return
    keys = {"pickup": location_key(order.pickup), "dropoff": location_key(order.dropoff)}
    q = db.query(BookingAttachment).filter(
        BookingAttachment.is_location_template.is_(True), BookingAttachment.deleted_at.is_(None)
    )
    q = _owner_filter(q, "merchant" if order.merchant_id else "customer", order.merchant_id or order.customer_id)
    templates = [t for t in q.all() if t.location_key and t.location_key == keys.get(t.stop)]
    if not templates:
        return
    have = {
        r.source_template_id
        for r in db.query(BookingAttachment.source_template_id).filter(BookingAttachment.order_id == order.id).all()
    }
    for t in templates:
        if t.id in have or not _stop_open(order, t.stop):
            continue
        copy = BookingAttachment(
            order_id=order.id, merchant_id=order.merchant_id, customer_id=order.customer_id, stop=t.stop,
            kind=t.kind, filename=t.filename, content_type=t.content_type, size_bytes=t.size_bytes,
            sha256=t.sha256, content=t.content, note=t.note, required_at_stop=t.required_at_stop,
            source_template_id=t.id, uploaded_by=t.uploaded_by,
        )
        db.add(copy)
        db.flush()
        _event(db, copy, "system", None, "attached_from_location", template_id=t.id)
    db.flush()


def list_for_owner(db: Session, owner_type: str, owner_id: str, order_id: str) -> dict[str, Any]:
    order = owned_order(db, owner_type, owner_id, order_id)
    sync_location_templates(db, order)
    rows = (
        db.query(BookingAttachment)
        .filter(BookingAttachment.order_id == order.id, BookingAttachment.deleted_at.is_(None))
        .order_by(BookingAttachment.created_at)
        .all()
    )
    return {
        "items": [row(r) for r in rows],
        "kinds": KINDS,
        "max_bytes": MAX_BYTES,
        "editable": {s: _stop_open(order, s) for s in STOPS},
    }


def upload(
    db: Session, *, owner_type: str, owner_id: str, actor_id: str, order_id: str | None, data: bytes,
    filename: str, kind: str | None = None, stop: str | None = None, required_at_stop: bool = True,
    note: str | None = None, save_for_location: bool = False, location_address: dict | None = None,
) -> dict[str, Any]:
    ctype = validate_file(data)
    kind = kind or suggest_kind(filename, data)
    if kind not in KINDS:
        raise AttachmentError("attachment_kind_invalid")
    stop = stop or DEFAULT_STOP[kind]
    if stop not in STOPS:
        raise AttachmentError("attachment_stop_invalid")
    order = None
    if order_id:
        order = owned_order(db, owner_type, owner_id, order_id)
        if not _stop_open(order, stop):
            raise AttachmentError("attachment_stop_closed")
        count = (
            db.query(BookingAttachment)
            .filter(BookingAttachment.order_id == order.id, BookingAttachment.deleted_at.is_(None))
            .count()
        )
        if count >= MAX_PER_ORDER:
            raise AttachmentError("attachment_limit_reached")
    elif not save_for_location:
        raise AttachmentError("attachment_order_required")
    common = dict(
        merchant_id=owner_id if owner_type == "merchant" else (order.merchant_id if order else None),
        customer_id=owner_id if owner_type == "customer" else (order.customer_id if order else None),
        stop=stop, kind=kind, filename=_safe_name(filename), content_type=ctype, size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), content=data, note=(note or "").strip()[:500] or None,
        required_at_stop=bool(required_at_stop), uploaded_by=f"{owner_type}:{actor_id}",
    )
    template = None
    if save_for_location:
        addr = location_address
        if addr is None and order is not None:
            addr = order.pickup if stop == "pickup" else order.dropoff
        key = location_key(addr)
        if not key:
            raise AttachmentError("attachment_location_unknown")
        template = BookingAttachment(order_id=None, is_location_template=True, location_key=key, **common)
        db.add(template)
        db.flush()
        _event(db, template, owner_type, actor_id, "location_template_saved")
    att = None
    if order:
        att = BookingAttachment(order_id=order.id, source_template_id=template.id if template else None, **common)
        db.add(att)
        db.flush()
        _event(db, att, owner_type, actor_id, "uploaded", kind=kind, stop=stop)
    return row(att or template)


def update(db: Session, *, owner_type: str, owner_id: str, actor_id: str, attachment_id: str,
           kind: str | None = None, stop: str | None = None, required_at_stop: bool | None = None,
           note: str | None = None) -> dict[str, Any]:
    att = _owned_attachment(db, owner_type, owner_id, attachment_id)
    if att.order_id:
        order = db.get(Order, att.order_id)
        if not _stop_open(order, att.stop) or (stop and not _stop_open(order, stop)):
            raise AttachmentError("attachment_stop_closed")
    if kind is not None:
        if kind not in KINDS:
            raise AttachmentError("attachment_kind_invalid")
        att.kind = kind
    if stop is not None:
        if stop not in STOPS:
            raise AttachmentError("attachment_stop_invalid")
        att.stop = stop
    if required_at_stop is not None:
        att.required_at_stop = required_at_stop
    if note is not None:
        att.note = note.strip()[:500] or None
    _event(db, att, owner_type, actor_id, "updated")
    db.flush()
    return row(att)


def _owned_attachment(db: Session, owner_type: str, owner_id: str, attachment_id: str) -> BookingAttachment:
    q = db.query(BookingAttachment).filter(BookingAttachment.id == attachment_id, BookingAttachment.deleted_at.is_(None))
    att = _owner_filter(q, owner_type, owner_id).first()
    if not att:
        raise LookupError("attachment_not_found")
    return att


def delete(db: Session, *, owner_type: str, owner_id: str, actor_id: str, attachment_id: str) -> None:
    att = _owned_attachment(db, owner_type, owner_id, attachment_id)
    if att.order_id and not _stop_open(db.get(Order, att.order_id), att.stop):
        raise AttachmentError("attachment_stop_closed")
    att.deleted_at = _now()
    att.content = None
    _event(db, att, owner_type, actor_id, "deleted")
    db.flush()


def list_location_templates(db: Session, owner_type: str, owner_id: str) -> list[dict[str, Any]]:
    q = db.query(BookingAttachment).filter(
        BookingAttachment.is_location_template.is_(True), BookingAttachment.deleted_at.is_(None)
    )
    return [row(r) | {"location_key": r.location_key} for r in _owner_filter(q, owner_type, owner_id).all()]


def owner_download(db: Session, *, owner_type: str, owner_id: str, actor_id: str, attachment_id: str):
    att = _owned_attachment(db, owner_type, owner_id, attachment_id)
    if att.content is None:
        raise LookupError("attachment_purged")
    _event(db, att, owner_type, actor_id, "downloaded")
    return att, att.content


# ── driver side ──────────────────────────────────────────────────────────

def _driver_order(db: Session, driver_id: str, order_id: str) -> Order:
    order = db.get(Order, order_id)
    if not order:
        raise LookupError("order_not_found")
    if order.assigned_driver_id != driver_id:
        raise PermissionError("not_assigned_driver")
    return order


def _driver_stops(order: Order) -> list[str]:
    """The driver sees pickup docs until pickup is done, then the drop docs."""
    if order.state in TERMINAL:
        return []
    return ["dropoff"] if order.state in PICKUP_DONE else ["pickup", "dropoff"]


def list_for_driver(db: Session, driver_id: str, order_id: str) -> dict[str, Any]:
    order = _driver_order(db, driver_id, order_id)
    sync_location_templates(db, order)
    stops = _driver_stops(order)
    rows = (
        db.query(BookingAttachment)
        .filter(BookingAttachment.order_id == order.id, BookingAttachment.deleted_at.is_(None),
                BookingAttachment.stop.in_(stops or ["-"]))
        .order_by(BookingAttachment.created_at)
        .all()
    )
    items = [row(r, for_owner=False) for r in rows]
    checklist = [
        {"id": f"show_document:{r['id']}", "label": "Show document to warehouse staff",
         "document": r["filename"], "done": r["shown_at"] is not None}
        for r in items if r["required_at_stop"] and r["stop"] == "pickup"
    ]
    return {"items": items, "pickup_checklist": checklist}


def driver_download(db: Session, driver_id: str, attachment_id: str):
    att = db.get(BookingAttachment, attachment_id)
    if not att or att.deleted_at or not att.order_id:
        raise LookupError("attachment_not_found")
    order = _driver_order(db, driver_id, att.order_id)
    if att.stop not in _driver_stops(order):
        raise PermissionError("attachment_not_for_this_stop")
    if att.content is None:
        raise LookupError("attachment_purged")
    if att.first_viewed_by_driver_at is None:
        att.first_viewed_by_driver_at = _now()
    _event(db, att, "driver", driver_id, "viewed")
    db.flush()
    return att, att.content


def mark_shown(db: Session, driver_id: str, attachment_id: str, proof: bytes | None = None) -> dict[str, Any]:
    att = db.get(BookingAttachment, attachment_id)
    if not att or att.deleted_at or not att.order_id:
        raise LookupError("attachment_not_found")
    order = _driver_order(db, driver_id, att.order_id)
    if att.stop not in _driver_stops(order):
        raise PermissionError("attachment_not_for_this_stop")
    if proof:
        ctype = validate_file(proof)
        if not ctype.startswith("image/"):
            raise AttachmentError("proof_must_be_photo")
        att.proof_content, att.proof_content_type = proof, ctype
    now = _now()
    att.shown_at = now
    att.shown_by_driver_id = driver_id
    att.first_viewed_by_driver_at = att.first_viewed_by_driver_at or now
    _event(db, att, "driver", driver_id, "shown_at_stop", proof=bool(proof))
    db.flush()
    return row(att, for_owner=False)


def pickup_gate_enforced() -> bool:
    """Off until the mobile driver app ships the Show-to-staff screen (else drivers on the
    current app build would be blocked at pickup with no way to confirm)."""
    return os.environ.get("PICKUP_DOCUMENT_GATE", "off").lower() in ("1", "true", "on")


def assert_pickup_documents_shown(db: Session, order: Order, *, force: bool = False) -> None:
    if not (force or pickup_gate_enforced()):
        return
    missing = (
        db.query(BookingAttachment)
        .filter(BookingAttachment.order_id == order.id, BookingAttachment.deleted_at.is_(None),
                BookingAttachment.stop == "pickup", BookingAttachment.required_at_stop.is_(True),
                BookingAttachment.shown_at.is_(None))
        .all()
    )
    if missing:
        raise PickupDocumentNotShown([{"id": m.id, "filename": m.filename} for m in missing])


# ── staff ────────────────────────────────────────────────────────────────

def list_for_staff(db: Session, order_id: str) -> dict[str, Any]:
    rows = db.query(BookingAttachment).filter(BookingAttachment.order_id == order_id).order_by(BookingAttachment.created_at).all()
    events = (
        db.query(BookingAttachmentEvent).filter(BookingAttachmentEvent.order_id == order_id)
        .order_by(BookingAttachmentEvent.created_at).all()
    )
    return {
        "items": [row(r) | {"deleted": r.deleted_at is not None, "uploaded_by": r.uploaded_by} for r in rows],
        "events": [
            {"attachment_id": e.attachment_id, "actor_type": e.actor_type, "actor_id": e.actor_id,
             "action": e.action, "payload": e.payload, "at": e.created_at.isoformat() if e.created_at else None}
            for e in events
        ],
    }


def staff_download(db: Session, staff_id: str, attachment_id: str, *, proof: bool = False):
    att = db.get(BookingAttachment, attachment_id)
    if not att:
        raise LookupError("attachment_not_found")
    data = att.proof_content if proof else att.content
    if data is None:
        raise LookupError("attachment_purged")
    _event(db, att, "staff", staff_id, "proof_viewed" if proof else "downloaded")
    db.flush()
    return att, data, (att.proof_content_type if proof else att.content_type)


# ── retention ────────────────────────────────────────────────────────────

def purge_expired(db: Session, *, now: datetime | None = None) -> int:
    """Wipe bytes RETENTION_DAYS after the booking finished. Templates are kept until the owner deletes them."""
    cutoff = (now or _now()) - timedelta(days=RETENTION_DAYS)
    rows = (
        db.query(BookingAttachment)
        .join(Order, Order.id == BookingAttachment.order_id)
        .filter(BookingAttachment.purged_at.is_(None), Order.state.in_(TERMINAL), Order.updated_at < cutoff)
        .all()
    )
    for r in rows:
        r.content = None
        r.proof_content = None
        r.purged_at = now or _now()
        _event(db, r, "system", None, "purged", reason="retention")
    db.flush()
    return len(rows)

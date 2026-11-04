"""Pickup document checklist + instructions. Subjects are an order or a bulk-batch route."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.job_docs import rules
from porterchain_api.job_docs.models import InstructionAck, InstructionEdit, JobInstruction, PickupDocument

_id = lambda: str(uuid.uuid4())  # noqa: E731
ROLES = ("admin", "merchant", "customer", "partner")
VIEWERS = ("driver", "admin", "merchant", "customer", "partner")
STEPS = ("pickup", "scan", "delivery")
PRIORITIES = ("normal", "high", "must_read")


# ---------------- documents ----------------

def required_for_order(db: Session, order: Any) -> list[str]:
    from porterchain_api.flow_engine.service import flags_for, flow_specs_for_order
    spec = flow_specs_for_order(db, order)
    return rules.required_pickup_docs(spec["documents"], flags_for(order))


def _captured(db: Session, *, order_id: str | None, route_id: str | None) -> dict[str, str]:
    q = db.query(PickupDocument)
    q = q.filter(PickupDocument.order_id == order_id) if order_id else q.filter(PickupDocument.route_id == route_id)
    out: dict[str, str] = {}
    for d in q.order_by(PickupDocument.captured_at).all():
        if out.get(d.doc_type) != "captured":
            out[d.doc_type] = d.status
    return out


def checklist(db: Session, required: list[str], *, order_id: str | None = None, route_id: str | None = None,
              phase: str = "at_pickup", lang: str = "en") -> dict[str, Any]:
    cap = _captured(db, order_id=order_id, route_id=route_id)
    return {"items": [{"doc_type": d, "label": rules.PICKUP_DOCS[d]["label"], "blocking": rules.PICKUP_DOCS[d]["blocking"],
                       "needs_seal": rules.PICKUP_DOCS[d]["seal"], "status": cap.get(d, "todo")} for d in required],
            "blockers": rules.gate(required, cap), "reminders": rules.reminders(required, cap, phase, lang)}


def capture(db: Session, required: list[str], doc_type: str, body: dict[str, Any], driver_id: str, *,
            order_id: str | None = None, route_id: str | None = None) -> PickupDocument:
    if doc_type not in required:
        raise ValueError("document_not_required")
    rules.validate_capture(doc_type, body)
    d = PickupDocument(id=_id(), order_id=order_id, route_id=route_id, doc_type=doc_type, status="captured",
                       media_key=body.get("media_key"), scan_code=body.get("scan_code"), seal_no=body.get("seal_no"),
                       shipper_name=body["shipper_name"].strip(), shipper_signature_key=body["shipper_signature_key"],
                       note=body.get("note"), captured_by=driver_id)
    db.add(d)
    db.flush()
    return d


def report_missing(db: Session, required: list[str], doc_type: str, reason: str, driver_id: str, *,
                   order_id: str | None = None, route_id: str | None = None) -> dict[str, Any]:
    """Raises an exception record. Blocking docs stay blocking (ops must resolve); others let pickup continue."""
    if doc_type not in required:
        raise ValueError("document_not_required")
    if not (reason or "").strip():
        raise ValueError("reason_required")
    db.add(PickupDocument(id=_id(), order_id=order_id, route_id=route_id, doc_type=doc_type, status="missing",
                          note=reason.strip(), captured_by=driver_id))
    if order_id:
        from porterchain_api.booking_models import OrderException
        db.add(OrderException(id=_id(), order_id=order_id, type="pickup_document_missing", status="open",
                              reported_by_type="driver", reported_by_id=driver_id,
                              evidence={"doc_type": doc_type, "reason": reason.strip()}))
    elif route_id:
        from porterchain_api.batch_engine.models import BatchException
        db.add(BatchException(id=_id(), route_id=route_id, kind="document_missing", driver_id=driver_id,
                              detail={"doc_type": doc_type}, note=reason.strip()))
    db.flush()
    return {"doc_type": doc_type, "blocking": rules.PICKUP_DOCS[doc_type]["blocking"]}


def assert_pickup_docs(db: Session, required: list[str], *, order_id: str | None = None,
                       route_id: str | None = None) -> None:
    b = rules.gate(required, _captured(db, order_id=order_id, route_id=route_id))
    if b:
        raise ValueError(f"pickup_documents_missing:{b[0]}")


def documents_out(db: Session, *, order_id: str | None = None, route_id: str | None = None) -> list[dict[str, Any]]:
    """Admin/merchant view of what was attached at pickup."""
    q = db.query(PickupDocument)
    q = q.filter(PickupDocument.order_id == order_id) if order_id else q.filter(PickupDocument.route_id == route_id)
    return [{"id": d.id, "doc_type": d.doc_type, "status": d.status, "media_key": d.media_key, "scan_code": d.scan_code,
             "seal_no": d.seal_no, "shipper_name": d.shipper_name, "signature_key": d.shipper_signature_key,
             "note": d.note, "captured_by": d.captured_by, "captured_at": d.captured_at.isoformat() if d.captured_at else None}
            for d in q.order_by(PickupDocument.captured_at).all()]


# ---------------- instructions ----------------

def _snap(i: JobInstruction) -> dict[str, Any]:
    return {"text": i.text, "photo_key": i.photo_key, "priority": i.priority, "visibility": list(i.visibility or []),
            "steps": list(i.steps or []), "business": i.business, "parcel_id": i.parcel_id}


def _validate(role: str, body: dict[str, Any], *, own_parcels: set[str] | None) -> dict[str, Any]:
    if role not in ROLES:
        raise PermissionError("role_cannot_add_instructions")
    text = (body.get("text") or "").strip()
    if not text or len(text) > 2000:
        raise ValueError("text_required")
    pr = body.get("priority", "normal")
    if pr not in PRIORITIES:
        raise ValueError("bad_priority")
    vis = list(body.get("visibility") or ["driver", "admin", role])
    if any(v not in VIEWERS for v in vis):
        raise ValueError("bad_visibility")
    steps = list(body.get("steps") or ["delivery"])
    if any(s not in STEPS for s in steps):
        raise ValueError("bad_step")
    business = bool(body.get("business"))
    if role == "customer":
        # Customers only shape their own delivery: delivery step, no business flags, only their parcels.
        if steps != ["delivery"]:
            raise PermissionError("customer_delivery_only")
        if business or any(v in ("merchant", "partner") for v in vis):
            raise PermissionError("customer_visibility_limited")
        if body.get("parcel_id") and own_parcels is not None and body["parcel_id"] not in own_parcels:
            raise PermissionError("not_your_parcel")
    return {"text": text, "photo_key": body.get("photo_key"), "priority": pr, "visibility": vis, "steps": steps,
            "business": business, "parcel_id": body.get("parcel_id")}


def add_instruction(db: Session, role: str, author_id: str, body: dict[str, Any], *, order_id: str | None = None,
                    route_id: str | None = None, own_parcels: set[str] | None = None) -> JobInstruction:
    if not (order_id or route_id):
        raise ValueError("subject_required")
    v = _validate(role, body, own_parcels=own_parcels)
    i = JobInstruction(id=_id(), order_id=order_id, route_id=route_id, author_role=role, author_id=author_id, **v)
    db.add(i)
    db.add(InstructionEdit(id=_id(), instruction_id=i.id, author_role=role, author_id=author_id, action="create",
                           after=v))
    db.flush()
    return i


def edit_instruction(db: Session, instruction_id: str, role: str, author_id: str, body: dict[str, Any], *,
                     own_parcels: set[str] | None = None, delete: bool = False) -> JobInstruction:
    i = db.get(JobInstruction, instruction_id)
    if not i or i.deleted:
        raise LookupError("instruction_not_found")
    if role != "admin" and (i.author_role != role or i.author_id != author_id):
        raise PermissionError("not_your_instruction")
    before = _snap(i)
    if delete:
        i.deleted = True
        db.add(InstructionEdit(id=_id(), instruction_id=i.id, author_role=role, author_id=author_id, action="delete",
                               before=before))
    else:
        v = _validate(role if role != "admin" else "admin", {**before, **body}, own_parcels=own_parcels)
        for k, val in v.items():
            setattr(i, k, val)
        i.version += 1  # must-read acks reset on change
        db.add(InstructionEdit(id=_id(), instruction_id=i.id, author_role=role, author_id=author_id, action="edit",
                               before=before, after=v))
    db.flush()
    return i


def history(db: Session, instruction_id: str) -> list[dict[str, Any]]:
    rows = db.query(InstructionEdit).filter(InstructionEdit.instruction_id == instruction_id).all()
    rank = {"create": 0, "edit": 1, "delete": 2}
    rows.sort(key=lambda e: (e.at, rank.get(e.action, 9)))
    return [{"action": e.action, "author_role": e.author_role, "author_id": e.author_id, "before": e.before,
             "after": e.after, "at": e.at.isoformat() if e.at else None} for e in rows]


def _q(db: Session, order_id: str | None, route_id: str | None):
    q = db.query(JobInstruction).filter(JobInstruction.deleted.is_(False))
    return q.filter(JobInstruction.order_id == order_id) if order_id else q.filter(JobInstruction.route_id == route_id)


def for_viewer(db: Session, viewer: str, *, order_id: str | None = None, route_id: str | None = None,
               viewer_id: str | None = None) -> list[dict[str, Any]]:
    if viewer not in VIEWERS:
        raise PermissionError("bad_viewer")
    out = []
    for i in _q(db, order_id, route_id).all():
        if viewer != "admin" and viewer not in (i.visibility or []):
            continue
        if viewer == "driver" and i.business:
            continue  # privacy rule: business data never reaches drivers
        if viewer == "customer" and i.author_role != "customer" and i.business:
            continue
        out.append({"id": i.id, "parcel_id": i.parcel_id, "text": i.text, "photo_key": i.photo_key,
                    "priority": i.priority, "steps": i.steps, "version": i.version, "author_role": i.author_role,
                    **({} if viewer == "driver" else {"visibility": i.visibility, "business": i.business,
                                                       "author_id": i.author_id})})
    return out


def driver_step(db: Session, driver_id: str, step: str, *, order_id: str | None = None, route_id: str | None = None,
                parcel_id: str | None = None) -> dict[str, Any]:
    """Instructions for this step (+ for the parcel just scanned). must_read ones block until acknowledged."""
    if step not in STEPS:
        raise ValueError("bad_step")
    items = [i for i in for_viewer(db, "driver", order_id=order_id, route_id=route_id)
             if step in i["steps"] and (i["parcel_id"] is None or parcel_id is None or i["parcel_id"] == parcel_id)
             and (step != "scan" or parcel_id is None or i["parcel_id"] in (None, parcel_id))]
    acked = {(a.instruction_id, a.version) for a in db.query(InstructionAck).filter(InstructionAck.driver_id == driver_id)}
    for i in items:
        i["acknowledged"] = (i["id"], i["version"]) in acked
    order = {"must_read": 0, "high": 1, "normal": 2}
    items.sort(key=lambda i: order[i["priority"]])
    return {"items": items, "must_ack": [i["id"] for i in items if i["priority"] == "must_read" and not i["acknowledged"]]}


def acknowledge(db: Session, instruction_id: str, driver_id: str) -> None:
    i = db.get(JobInstruction, instruction_id)
    if not i or i.deleted or "driver" not in (i.visibility or []) or i.business:
        raise LookupError("instruction_not_found")
    db.add(InstructionAck(id=_id(), instruction_id=i.id, version=i.version, driver_id=driver_id))
    db.flush()


def assert_acknowledged(db: Session, driver_id: str, step: str, **subject: Any) -> None:
    pending = driver_step(db, driver_id, step, **subject)["must_ack"]
    if pending:
        raise ValueError(f"instruction_not_acknowledged:{pending[0]}")

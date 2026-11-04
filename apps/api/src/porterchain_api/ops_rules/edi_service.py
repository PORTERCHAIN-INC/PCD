"""Build an EDI file for one batch from its parcels and custody events."""
from __future__ import annotations

from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from porterchain_api.batch_engine.models import BatchParcel, CustodyEvent, DeliveryBatch
from porterchain_api.ops_rules import edi


def allocate_control_number(db: Session, receiver: str) -> int:
    """Next ISA/GS/ST control number for one trading partner: unique and incrementing.

    Partners reject a repeated interchange number as a duplicate, so every file sent to the same
    receiver (214 or 856) takes the next value. Stored in the gap-free counter table (row-locked).
    """
    from sqlalchemy import select

    from porterchain_api.billing_engine.models import InvoiceNumberSequence

    scope = f"EDI:{(receiver or 'PARTNER').strip().upper()[:15]}"
    row = db.execute(
        select(InvoiceNumberSequence).where(InvoiceNumberSequence.scope == scope).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        if db.get_bind().dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            db.execute(
                pg_insert(InvoiceNumberSequence)
                .values(scope=scope, last_value=0)
                .on_conflict_do_nothing(index_elements=["scope"])
            )
        else:  # pragma: no cover
            db.add(InvoiceNumberSequence(scope=scope, last_value=0))
            db.flush()
        row = db.execute(
            select(InvoiceNumberSequence).where(InvoiceNumberSequence.scope == scope).with_for_update()
        ).scalar_one()
    # ISA13 is 9 digits: wrap after 999,999,999 (never 0).
    row.last_value = int(row.last_value or 0) % 999_999_999 + 1
    db.flush()
    return int(row.last_value)


def export_batch(db: Session, batch_id: str, kind: str, receiver: str = "PARTNER") -> PlainTextResponse:
    if kind not in ("214", "856"):
        raise LookupError("edi_kind_unknown")
    b = db.get(DeliveryBatch, batch_id)
    if not b:
        raise LookupError("batch_not_found")
    ps = db.query(BatchParcel).filter(BatchParcel.batch_id == batch_id).order_by(BatchParcel.row_no).all()
    parcels = [{"id": p.id, "barcode": p.barcode, "client_labels": p.client_labels or [],
                "recipient": p.recipient, "address": p.address} for p in ps]
    ctl = allocate_control_number(db, receiver)
    if kind == "856":
        text = edi.x12_856({"id": b.id}, parcels, receiver=receiver, ctl=ctl)
    else:
        ids = [p.id for p in ps]
        evs = db.query(CustodyEvent).filter(CustodyEvent.parcel_id.in_(ids)).all() if ids else []
        rows = [{"parcel_id": e.parcel_id, "kind": e.kind, "at": e.at} for e in evs]
        text = edi.x12_214(parcels, rows, receiver=receiver, ctl=ctl)
    db.commit()
    name = batch_id + "_" + kind + ".edi"
    return PlainTextResponse(text, headers={"Content-Disposition": "attachment; filename=" + name})

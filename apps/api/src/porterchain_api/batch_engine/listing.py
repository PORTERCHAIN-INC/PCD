"""Batch list reads for merchant/admin routes (keeps DB access out of routers)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.batch_engine.models import BatchHandover, BatchRoute, DeliveryBatch


def list_batches(db: Session, merchant_id: str | None, limit: int) -> dict:
    q = db.query(DeliveryBatch)
    if merchant_id:
        q = q.filter(DeliveryBatch.merchant_id == merchant_id)
    rows = q.order_by(DeliveryBatch.created_at.desc()).limit(min(max(limit, 1), 200)).all()
    return {
        "batches": [
            {
                "id": b.id,
                "merchant_id": b.merchant_id,
                "status": b.status,
                "parcels": (b.plan or {}).get("parcels"),
                "routes": (b.plan or {}).get("routes"),
                "waves": (b.plan or {}).get("waves"),
                "pickup_docs": (b.plan or {}).get("pickup_docs") or [],
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in rows
        ]
    }


def driver_open_routes(db: Session, driver_id: str) -> dict:
    rows = (
        db.query(BatchRoute)
        .filter(BatchRoute.driver_id == driver_id, BatchRoute.status.notin_(("closed", "locked")))
        .order_by(BatchRoute.wave)
        .all()
    )
    return {
        "items": [
            {"id": r.id, "batch_id": r.batch_id, "route_no": r.route_no, "wave": r.wave, "status": r.status}
            for r in rows
        ]
    }


def driver_incoming_handovers(db: Session, driver_id: str) -> dict:
    rows = (
        db.query(BatchHandover)
        .filter(BatchHandover.to_driver_id == driver_id, BatchHandover.status == "pending")
        .all()
    )
    return {
        "items": [
            {"id": h.id, "from_driver_id": h.from_driver_id, "parcels": len(h.parcel_ids), "place_kind": h.place_kind}
            for h in rows
        ]
    }

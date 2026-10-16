"""Scan-anytime label lookup (driver camera). See routers/driver/scan.py."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package
from porterchain_api.driver_engine import scan_audit
from porterchain_api.driver_ownership import driver_owns_order
from porterchain_api.reporting.qr_codec import (
    InvalidLabelQr,
    decode_label_qr,
    decode_signed_label,
    is_signed_label,
)

_INACTIVE = {
    "DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED",
    "RETURN_TO_SENDER", "LOST", "REFUNDED",
}

# Parcel status -> what the driver may do next (each action uses its existing,
# state-checked endpoint; this list only drives the UI).
_ALLOWED = {
    "manifested": ["scan_pickup", "report_missing", "note", "photo", "exception"],
    "missing_at_pickup": ["scan_pickup", "note", "photo", "exception"],
    "picked_up": ["scan_delivery", "note", "photo", "exception"],
    "loaded": ["scan_delivery", "note", "photo", "exception"],
    "out_for_delivery": ["scan_delivery", "note", "photo", "exception"],
    "delivered": ["note"],
}


def _resolve(db: Session, code: str) -> Package | None:
    token = (code or "").strip()
    if not token or len(token) > 256:
        return None
    if is_signed_label(token):
        try:
            return db.get(Package, decode_signed_label(token))
        except InvalidLabelQr:
            return None
    try:
        d = decode_label_qr(token)
        return db.get(Package, d.package_id)
    except InvalidLabelQr:
        pass
    # Typed fallback: the human-readable tracking suffix printed under the QR.
    return db.query(Package).filter(Package.tracking_suffix == token.upper()).first() or (
        db.query(Package).filter(Package.tracking_suffix == token).first()
    )



def lookup(db: Session, driver_id: str, body: dict[str, Any]) -> dict[str, Any]:
    pkg = _resolve(db, str(body.get("code") or body.get("qr_payload") or ""))
    order = db.get(Order, pkg.order_id) if pkg else None
    if (
        not pkg
        or not order
        or not driver_owns_order(db, driver_id, order)
        or (order.state or "").upper() in _INACTIVE
    ):
        scan_audit.log_scan(db, driver_id=driver_id, kind="lookup", result="not_yours", body=body)
        raise LookupError("not_yours")

    expected = (body.get("expected_order_id") or "").strip() or None
    wrong_stop = bool(expected and expected != order.id)
    scan_audit.log_scan(
        db,
        driver_id=driver_id,
        kind="lookup",
        result="wrong_stop" if wrong_stop else "ok",
        body=body,
        package_id=pkg.id,
        order_id=order.id,
    )
    status = (pkg.status or "manifested").lower()
    return {
        "warning": "wrong_stop" if wrong_stop else None,
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "state": order.state,
        },
        "parcel": {
            "id": pkg.id,
            "tracking_suffix": pkg.tracking_suffix,
            "status": status,
            "item_label": pkg.item_label,
            "box_index": pkg.box_index,
            "box_count": pkg.box_count,
            "parcel_index": pkg.parcel_index,
            "total_parcels": pkg.total_parcels,
            "stop_sequence": pkg.stop_sequence,
        },
        "next_phase": "pickup" if status in ("manifested", "missing_at_pickup") else "delivery",
        "allowed_actions": _ALLOWED.get(status, ["note"]),
    }

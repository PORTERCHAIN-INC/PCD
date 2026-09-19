"""Dual-write order pickup/dropoff JSON onto Address + Stop rows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Address, Order, Stop


def address_from_blob(blob: dict[str, Any] | None) -> Address:
    data = blob if isinstance(blob, dict) else {}
    formatted = (
        data.get("formatted")
        or data.get("formatted_address")
        or data.get("address")
        or data.get("line1")
        or "Unknown"
    )
    lat = data.get("lat")
    lng = data.get("lng")
    try:
        lat_f = float(lat) if lat is not None else None
    except (TypeError, ValueError):
        lat_f = None
    try:
        lng_f = float(lng) if lng is not None else None
    except (TypeError, ValueError):
        lng_f = None
    return Address(
        formatted=str(formatted)[:512],
        line1=(data.get("line1") or data.get("street") or None),
        city=data.get("city"),
        region=data.get("region") or data.get("province") or data.get("state"),
        postal=data.get("postal") or data.get("postal_code"),
        country=str(data.get("country") or "CA")[:8],
        lat=lat_f,
        lng=lng_f,
        place_id=data.get("place_id"),
        contact_name=data.get("contact_name") or data.get("name") or data.get("contact"),
        phone=data.get("phone"),
    )


def persist_address(db: Session, blob: dict[str, Any] | None) -> Address:
    address = address_from_blob(blob)
    db.add(address)
    db.flush()
    return address


def _kind_for_rich_stop(index: int, total: int, blob: dict[str, Any]) -> str:
    stop_type = str(blob.get("type") or blob.get("kind") or "").lower()
    if stop_type == "pickup":
        return "pickup"
    if stop_type in {"dropoff", "drop", "delivery"}:
        return "drop"
    if index == 0:
        return "pickup"
    if index == total - 1:
        return "drop"
    return "stop"


def stop_plan(order: Order) -> list[tuple[int, str, dict[str, Any] | None]]:
    """Ordered (sequence, kind, address_blob) including mid-stops from compliance metadata."""
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    rich = meta.get("stops")
    if isinstance(rich, list):
        ordered = sorted(
            (s for s in rich if isinstance(s, dict)),
            key=lambda s: s.get("sequence", 0),
        )
        if ordered:
            n = len(ordered)
            return [(i, _kind_for_rich_stop(i, n, s), s) for i, s in enumerate(ordered)]

    rows: list[tuple[int, str, dict[str, Any] | None]] = [
        (0, "pickup", order.pickup if isinstance(order.pickup, dict) else None),
    ]
    mids = meta.get("additional_stops")
    seq = 1
    if isinstance(mids, list):
        for mid in mids:
            if isinstance(mid, dict):
                rows.append((seq, "stop", mid))
                seq += 1
    rows.append((seq, "drop", order.dropoff if isinstance(order.dropoff, dict) else None))
    return rows


def dual_write_stops(db: Session, order: Order) -> list[Stop]:
    """Idempotent pickup + mid + drop rows. JSON on the order stays until a later cleanup."""
    existing = db.query(Stop).filter(Stop.order_id == order.id).order_by(Stop.sequence).all()
    if existing:
        return existing
    stops: list[Stop] = []
    for sequence, kind, blob in stop_plan(order):
        address = persist_address(db, blob)
        stop = Stop(
            order_id=order.id,
            sequence=sequence,
            kind=kind,
            address_id=address.id,
            status="pending",
        )
        db.add(stop)
        stops.append(stop)
    db.flush()
    return stops

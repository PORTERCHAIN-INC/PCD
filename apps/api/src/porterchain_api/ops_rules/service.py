"""DB side of the doc 84 §7 P0 gaps."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.ops_rules import codes, rules
from porterchain_api.ops_rules.models import DriverEquipment, Location, LocationUnit, SafetyReport

log = logging.getLogger(__name__)
CUSTODY_KINDS = {"pickup": "picked_up", "picked_up": "picked_up", "handover_out": "handover_out",
                 "handover_in": "handover_in", "depot_in": "depot_in", "sorted": "sorted", "loaded": "loaded",
                 "delivered": "delivered", "return": "returned", "returned": "returned", "held": "held",
                 "exception": "exception",
                 # close-route dispositions
                 "return_to_depot": "returned", "reattempt": "held", "missing": "exception"}


def _id() -> str:
    return str(uuid.uuid4())


# ---- F1 custody events on the single timeline
def custody_event_type(kind: str) -> str:
    if kind not in CUSTODY_KINDS:
        raise ValueError(f"unknown_custody_kind:{kind}")
    return f"custody.{CUSTODY_KINDS[kind]}"


def emit_custody(parcel_id: str, kind: str, driver_id: str | None, payload: dict[str, Any]) -> str:
    et = custody_event_type(kind)
    try:
        from porterchain_api.platform.bus import publish_domain_event
        publish_domain_event(event_type=et, aggregate_type="parcel", aggregate_id=parcel_id,
                             actor_type="driver" if driver_id else "system", actor_id=driver_id,
                             payload={k: v for k, v in payload.items() if v is not None})
    except Exception:  # noqa: BLE001 - the custody row is the record; the bus relay retries via outbox
        log.warning("custody event publish failed", exc_info=True)
    return et


# ---- F3 locations
def upsert_location(db: Session, address: str, *, lat: float | None = None, lng: float | None = None,
                    kind: str = "building", access_notes: str | None = None, hours: dict | None = None) -> Location:
    from porterchain_api.batch_engine.planner import building_key
    key, _unit = building_key(address)
    loc = db.query(Location).filter(Location.building_key == key).one_or_none()
    if not loc:
        loc = Location(id=_id(), kind=kind, building_key=key, address=address, lat=lat, lng=lng, flags={})
        db.add(loc)
    if access_notes is not None:
        loc.access_notes = access_notes
    if hours is not None:
        loc.hours = hours
    if lat is not None:
        loc.lat, loc.lng = lat, lng
    db.flush()
    return loc


def set_unit_notes(db: Session, location_id: str, unit: str, notes: str) -> LocationUnit:
    u = db.query(LocationUnit).filter(LocationUnit.location_id == location_id, LocationUnit.unit == unit).one_or_none()
    if not u:
        u = LocationUnit(id=_id(), location_id=location_id, unit=unit)
        db.add(u)
    u.access_notes = notes
    db.flush()
    return u


def access_for(db: Session, building_key: str, unit: str | None = None) -> dict[str, Any]:
    loc = db.query(Location).filter(Location.building_key == building_key).one_or_none()
    if not loc:
        return {"known": False}
    u = (db.query(LocationUnit).filter(LocationUnit.location_id == loc.id, LocationUnit.unit == unit).one_or_none()
         if unit else None)
    return {"known": True, "location_id": loc.id, "access_notes": loc.access_notes, "hours": loc.hours,
            "unit_notes": u.access_notes if u else None, "unsafe": bool((loc.flags or {}).get("unsafe"))}


# ---- SC-043 equipment
def set_equipment(db: Session, driver_id: str, tags: list[str]) -> list[str]:
    bad = set(tags) - set(rules.EQUIPMENT)
    if bad:
        raise ValueError(f"unknown_equipment:{sorted(bad)[0]}")
    row = db.get(DriverEquipment, driver_id) or DriverEquipment(driver_id=driver_id, tags=[])
    row.tags = sorted(set(tags))
    db.add(row)
    db.flush()
    return row.tags


def equipment_check(db: Session, driver_id: str, required: list[str]) -> dict[str, Any]:
    row = db.get(DriverEquipment, driver_id)
    gap = rules.equipment_gap(required, row.tags if row else [])
    return {"ok": not gap, "missing": gap, **({"code": "equipment_missing"} if gap else {})}


# ---- safety stops (SC-034 / SC-068 / SC-107)
def safety_stop(db: Session, code: str, driver_id: str, *, order_id: str | None = None, route_id: str | None = None,
                address: str | None = None, parcels: list[str] | None = None, note: str | None = None,
                photo_keys: list[str] | None = None, police_report_no: str | None = None,
                signature_key: str | None = None) -> dict[str, Any]:
    req = rules.safety_requirements(codes.canonical(code))
    # The driver's signed statement is stored with the evidence media (keys are typed by prefix; no new column).
    photo_keys = [*(photo_keys or []), *([signature_key] if signature_key else [])]
    if "photo" in req["requires"] and not photo_keys:
        raise ValueError("photo_required")
    if "parcels" in req["requires"] and not parcels:
        raise ValueError("parcels_required")
    loc = None
    if address:
        loc = upsert_location(db, address)
        if req.get("flag_location"):
            loc.flags = {**(loc.flags or {}), "unsafe": {"by": driver_id, "at": datetime.now(UTC).isoformat(),
                                                         "note": note}}
    rep = SafetyReport(id=_id(), code=code, driver_id=driver_id, order_id=order_id, route_id=route_id,
                       location_id=loc.id if loc else None, parcels=list(parcels or []), note=note,
                       photo_keys=list(photo_keys or []), police_report_no=police_report_no)
    db.add(rep)
    if order_id:
        from porterchain_api.booking_models import OrderException
        db.add(OrderException(order_id=order_id, type=code, status="open", reported_by_type="driver",
                              reported_by_id=driver_id, evidence={"safety_report_id": rep.id, "note": note,
                                                                  "photos": list(photo_keys or [])}))
    if route_id:
        from porterchain_api.batch_engine.models import BatchException
        db.add(BatchException(id=_id(), route_id=route_id, kind=code, quantity=len(parcels or []) or 1,
                              driver_id=driver_id, detail={"safety_report_id": rep.id}, note=note))
    db.flush()
    return {"id": rep.id, "code": code, **req, "location_flagged": bool(loc and req.get("flag_location"))}


# ---- SC-025 unlabelled parcel at pickup
def unlabelled_parcel(db: Session, route_id: str, driver_id: str, *, photo_keys: list[str],
                      parcel_id: str | None = None) -> dict[str, Any]:
    """Driver writes a PorterChain short code on the parcel and photographs it (doc 84 Q6: no printer)."""
    if len(photo_keys) < 2:
        raise ValueError("photos_required:written_code_and_parcel")
    from porterchain_api.batch_engine.models import BatchException, BatchParcel, BatchRoute
    r = db.get(BatchRoute, route_id)
    if not r or r.driver_id != driver_id:
        raise PermissionError("not_your_route")
    code = rules.short_code()
    if parcel_id:
        p = db.get(BatchParcel, parcel_id)
        if not p or p.batch_id != r.batch_id:
            raise LookupError("parcel_not_found")
        from porterchain_api.batch_engine.planner import norm_label
        p.client_labels = [*(p.client_labels or []), norm_label(code)]
    db.add(BatchException(id=_id(), route_id=route_id, kind="unlabelled_parcel", driver_id=driver_id,
                          detail={"short_code": code, "photos": photo_keys, "parcel_id": parcel_id}))
    db.flush()
    return {"short_code": code, "requires": rules.unlabelled_requirements(), "linked_parcel_id": parcel_id}


# ---- SC-051 end of shift
def end_shift_check(db: Session, driver_id: str) -> dict[str, Any]:
    from porterchain_api.batch_engine.models import BatchParcel
    aboard = db.query(BatchParcel).filter(BatchParcel.holder_driver_id == driver_id,
                                          BatchParcel.status == "picked_up").all()
    return rules.end_of_shift([{"barcode": p.barcode, "handling": p.handling} for p in aboard])


# ---- SC-085 concealed damage claim
def concealed_damage_claim(db: Session, order: Any, *, reporter: str, photos: list[str], note: str,
                           window_days: int | None = None) -> Any:
    from porterchain_api.admin_engine.claims_write import add_claim
    delivered = getattr(order, "delivered_at", None) or getattr(order, "updated_at", None)
    if order.state not in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED") or delivered is None:
        raise ValueError("order_not_delivered")
    if delivered.tzinfo is None:
        delivered = delivered.replace(tzinfo=UTC)
    chk = rules.concealed_damage_check(delivered, datetime.now(UTC), photos, window_days)
    return add_claim(db, order_id=order.id, merchant_id=getattr(order, "merchant_id", None),
                     claim_type="concealed_damage", status=chk["status"], description=note[:4000],
                     evidence={"photos": photos, "reporter": reporter, **chk})

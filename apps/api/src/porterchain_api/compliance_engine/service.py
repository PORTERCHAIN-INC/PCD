"""Doc 80 §2 service: trips, DVIR, HOS log (driver app + offline queue)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.compliance_engine import rules
from porterchain_api.compliance_engine.models import DvirReport, HosEvent, VehicleTrip


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _parse_at(v: Any) -> datetime:
    if isinstance(v, datetime):
        return _aware(v)  # type: ignore[return-value]
    if not v:
        raise ValueError("hos_at_required")
    return _aware(datetime.fromisoformat(str(v).replace("Z", "+00:00")))  # type: ignore[return-value]


def heavy_trucks_enabled() -> bool:
    from porterchain_api.config import get_settings

    return bool(getattr(get_settings(), "compliance_heavy_trucks_enabled", False))


def create_trip(db: Session, driver_id: str, body: dict[str, Any]) -> VehicleTrip:
    plate = str(body.get("plate") or "").strip().upper()
    if not plate:
        raise ValueError("plate_required")
    rgw = body.get("rgw_kg")
    if not isinstance(rgw, int) or rgw <= 0:
        raise ValueError("rgw_required")
    if body.get("is_rental") and not body.get("rental_agreement_ref"):
        raise ValueError("rental_agreement_required")
    if not body.get("insurance_evidence_ref"):
        raise ValueError("insurance_evidence_required")
    t = VehicleTrip(
        id=str(uuid.uuid4()), driver_id=driver_id, plate=plate, jurisdiction=body.get("jurisdiction") or "ON",
        vin=body.get("vin"), is_rental=bool(body.get("is_rental")), rental_agreement_ref=body.get("rental_agreement_ref"),
        rental_days=body.get("rental_days"), rgw_kg=rgw, gvwr_kg=body.get("gvwr_kg"), curb_kg=body.get("curb_kg"),
        cvor_required=rules.cvor_required(rgw), insurance_evidence_ref=body.get("insurance_evidence_ref"),
        maintenance_note=body.get("maintenance_note"), declared_kg=int(body.get("declared_kg") or 0), status="draft",
    )
    db.add(t)
    db.flush()
    return t


def latest_dvir(db: Session, driver_id: str, plate: str) -> DvirReport | None:
    return db.execute(
        select(DvirReport).where(DvirReport.driver_id == driver_id, DvirReport.plate == plate)
        .order_by(DvirReport.inspected_at.desc())
    ).scalars().first()


def start_trip(db: Session, driver_id: str, trip_id: str, *, now: datetime | None = None) -> VehicleTrip:
    now = now or _now()
    t = db.get(VehicleTrip, trip_id)
    if t is None or t.driver_id != driver_id:
        raise LookupError("trip_not_found")
    if t.status != "draft":
        raise ValueError("trip_already_started")
    if t.cvor_required and not heavy_trucks_enabled():
        raise ValueError("cvor_not_issued")  # I82-3: no heavy trucks until CVOR
    rules.check_weight(t.declared_kg, rgw_kg=t.rgw_kg, gvwr_kg=t.gvwr_kg, curb_kg=t.curb_kg)
    hos = hos_today(db, driver_id, now=now)
    if not hos["can_take_offers"]:
        raise ValueError("hos_limit")
    d = latest_dvir(db, driver_id, t.plate)
    if t.cvor_required:
        if d is None or not rules.dvir_valid(_aware(d.inspected_at), d.major_defect, now):
            raise ValueError("dvir_required")
    elif d is not None and d.major_defect and now - _aware(d.inspected_at) <= rules.DVIR_VALID:  # type: ignore[operator]
        raise ValueError("major_defect")
    if d is not None:
        t.inspection_due_at = _aware(d.inspected_at) + rules.DVIR_VALID  # type: ignore[operator]
    t.status, t.started_at = "started", now
    db.flush()
    return t


def submit_dvir(db: Session, driver_id: str, body: dict[str, Any]) -> DvirReport:
    cid = body.get("client_id")
    if cid:
        dup = db.execute(select(DvirReport).where(DvirReport.client_id == cid)).scalar_one_or_none()
        if dup is not None:
            return dup
    heavy = bool(body.get("heavy")) or rules.cvor_required(body.get("rgw_kg"))
    res = rules.validate_dvir(body, heavy=heavy)
    at = _parse_at(body.get("inspected_at") or _now())
    r = DvirReport(
        id=str(uuid.uuid4()), client_id=cid, driver_id=driver_id, trip_id=body.get("trip_id"),
        plate=str(body["plate"]).upper(), jurisdiction=body.get("jurisdiction") or "ON",
        operator_name=body["operator_name"], inspected_at=at, location=body["location"],
        inspector_name=body["inspector_name"], odometer_km=int(body["odometer_km"]),
        kind="schedule1" if heavy else "walkaround", items=body.get("items") or {}, defects=res["defects"],
        major_defect=res["major_defect"], signed_statement=True, photos=body.get("photos"),
        retain_until=at + rules.DVIR_RETAIN,
    )
    db.add(r)
    db.flush()
    return r


def record_hos(db: Session, driver_id: str, body: dict[str, Any]) -> HosEvent:
    status = body.get("status")
    if status not in rules.STATUSES:
        raise ValueError("hos_bad_status")
    cid = body.get("client_id")
    if cid:
        dup = db.execute(select(HosEvent).where(HosEvent.client_id == cid)).scalar_one_or_none()
        if dup is not None:
            return dup
    e = HosEvent(id=str(uuid.uuid4()), client_id=cid, driver_id=driver_id, status=status, at=_parse_at(body.get("at")),
                 other_operator_today=body.get("other_operator_today"), start_location=body.get("start_location"))
    db.add(e)
    db.flush()
    return e


def hos_today(db: Session, driver_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    since = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    rows = db.execute(select(HosEvent).where(HosEvent.driver_id == driver_id, HosEvent.at >= since)
                      .order_by(HosEvent.at)).scalars().all()
    events = [{"status": r.status, "at": _aware(r.at)} for r in rows]
    out = rules.hos_summary(events, now)
    other = any(r.other_operator_today for r in rows)
    out["radius_exemption"] = not other  # s. 23(2)(b): lost if driving for another operator today
    out["full_daily_log_required"] = other
    out["daily_record"] = [{"status": e["status"], "at": e["at"].isoformat()} for e in events]
    return out


def trip_out(t: VehicleTrip) -> dict[str, Any]:
    return {"id": t.id, "plate": t.plate, "is_rental": t.is_rental, "rgw_kg": t.rgw_kg, "cvor_required": t.cvor_required,
            "status": t.status, "declared_kg": t.declared_kg,
            "inspection_due_at": t.inspection_due_at.isoformat() if t.inspection_due_at else None,
            "started_at": t.started_at.isoformat() if t.started_at else None}


def dvir_out(r: DvirReport) -> dict[str, Any]:
    return {"id": r.id, "plate": r.plate, "kind": r.kind, "major_defect": r.major_defect, "defects": r.defects,
            "inspected_at": _aware(r.inspected_at).isoformat(), "valid_until": (_aware(r.inspected_at) + rules.DVIR_VALID).isoformat(),  # type: ignore[union-attr]
            "retain_until": _aware(r.retain_until).isoformat()}  # type: ignore[union-attr]

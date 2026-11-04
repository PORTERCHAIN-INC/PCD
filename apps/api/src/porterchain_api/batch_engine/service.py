"""Batch lifecycle: create -> assign -> pickup (count+photo+handover) -> deliver/scan -> handover -> close."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.batch_engine import planner as P
from porterchain_api.flow_engine import flow_spec as fs
from porterchain_api.job_docs import service as JD
from porterchain_api.batch_engine.models import (
    BatchException, BatchHandover, BatchParcel, BatchRoute, CustodyEvent, DeliveryBatch,
)

_id = lambda: str(uuid.uuid4())  # noqa: E731
DONE = ("delivered", "return_to_depot", "reattempt", "missing")
HIDDEN = ("locked",)  # dependent leg before upstream pickup: no details, no notification


class LegLocked(Exception):
    pass


def _pd(p: BatchParcel) -> dict[str, Any]:
    return {"id": p.id, "barcode": p.barcode, "client_labels": p.client_labels, "route_id": p.route_id,
            "stop_seq": p.stop_seq, "building_key": p.building_key, "unit": p.unit, "address": p.address,
            "recipient": p.recipient, "handling": p.handling, "scan_required": p.scan_required,
            "status": p.status, "weight_kg": p.weight_kg, "holder_driver_id": p.holder_driver_id}


def _custody(db: Session, parcel: BatchParcel, kind: str, driver_id: str | None, ev: dict[str, Any],
             counterpart: str | None = None, ref: str | None = None) -> None:
    db.add(CustodyEvent(id=_id(), parcel_id=parcel.id, kind=kind, driver_id=driver_id, counterpart_id=counterpart,
                        lat=ev.get("lat"), lng=ev.get("lng"), photo_key=ev.get("photo_key"), ref_id=ref))
    from porterchain_api.ops_rules.service import emit_custody
    emit_custody(parcel.id, kind, driver_id, {"batch_id": parcel.batch_id, "barcode": parcel.barcode,
                                              "counterpart_id": counterpart, "ref_id": ref,
                                              "lat": ev.get("lat"), "lng": ev.get("lng")})


class DuplicateRows(ValueError):
    """SC-015: soft warning — the merchant confirms and re-submits with confirm_duplicates."""

    def __init__(self, warnings: list[dict[str, Any]]):
        super().__init__("duplicates_need_confirm")
        self.warnings = warnings


def _duplicate_warnings(db: Session, merchant_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Same address + same client reference as a parcel in this merchant's recent batches."""
    from porterchain_api.ops_rules.rules import dup_key, duplicate_warnings
    recent = [b.id for b in db.query(DeliveryBatch).filter(DeliveryBatch.merchant_id == merchant_id)
              .order_by(DeliveryBatch.created_at.desc()).limit(20).all()]
    existing = {dup_key(p.address, P.norm_label(lab)) for p in db.query(BatchParcel).filter(BatchParcel.batch_id.in_(recent)).all()
                for lab in (p.client_labels or [])} if recent else set()
    ref_rows = [{"row_no": r["row"], "address": r["address"], "reference": P.norm_label(r["client_labels"][0])}
                for r in rows if r["client_labels"]]
    return duplicate_warnings(ref_rows, existing)


def create_batch(db: Session, merchant_id: str, csv_text: str, *, vehicle_class: str = "cargo_van",
                 drivers: int = 1, bulk_job_id: str | None = None, pickup_source: str = "shop",
                 pickup_point: dict[str, Any] | None = None,
                 doc_flags: dict[str, Any] | None = None, confirm_duplicates: bool = False) -> DeliveryBatch:
    if pickup_source not in P.PICKUP_SOURCES or pickup_source == "driver":
        raise ValueError("bad_pickup_source")
    rows, errors = P.parse_csv(csv_text)
    if not rows:
        raise ValueError("no_valid_rows")
    taken: set[str] = set()
    for r in rows:
        for lab in r["client_labels"]:
            n = P.norm_label(lab)
            if n in taken:
                raise ValueError(f"duplicate_client_label:{lab}")
            taken.add(n)
    warnings = _duplicate_warnings(db, merchant_id, rows)
    if warnings and not confirm_duplicates:
        raise DuplicateRows(warnings)
    routes = _vrp_plan(rows, vehicle_class, drivers, pickup_point) if all(
        r.get("lat") is not None and r.get("lng") is not None for r in rows) else P.plan(
        rows, vehicle_class=vehicle_class, drivers=drivers)
    b = DeliveryBatch(id=_id(), merchant_id=merchant_id, bulk_job_id=bulk_job_id, status="planned",
                      plan={"errors": errors, "routes": len(routes), "waves": max(r["wave"] for r in routes),
                            "parcels": len(rows), "vehicle_class": vehicle_class, "drivers": drivers,
                            "doc_flags": dict(doc_flags or {}),
                            "pickup_docs": _batch_docs(db, merchant_id, doc_flags or {}),
                            "warnings": warnings})
    db.add(b)
    for r in routes:
        route = BatchRoute(id=_id(), batch_id=b.id, route_no=r["route_no"], wave=r["wave"],
                           vehicle_class=vehicle_class, status="planned", pickup_source=pickup_source,
                           pickup_point=pickup_point, notices=[], route_plan=r.get("eta"))
        db.add(route)
        for p in r["parcels"]:
            db.add(BatchParcel(id=_id(), batch_id=b.id, route_id=route.id, row_no=p["row"],
                               barcode=P.make_barcode(b.id, p["row"]),
                               client_labels=[x.strip() for x in p["client_labels"]],  # as printed; matched normalized
                               recipient=p["recipient"], address=p["address"], unit=p["unit"],
                               building_key=p["building_key"], stop_seq=p["stop_seq"], weight_kg=p["weight_kg"],
                               handling=p["handling"], scan_required=p["scan_required"],
                               lat=p.get("lat"), lng=p.get("lng")))
    db.flush()
    return b


def _vrp_plan(rows: list[dict[str, Any]], vehicle_class: str, drivers: int,
              pickup_point: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Coordinates present -> multi-vehicle VRP decides routes, waves and sequence (building-grouped)."""
    from porterchain_api.batch_engine import vrp
    if vehicle_class not in P.VEHICLE_CAPACITY:
        raise ValueError("unknown_vehicle_class")
    cap = P.VEHICLE_CAPACITY[vehicle_class]
    by_row = {}
    for r in rows:
        key, unit = P.building_key(r["address"])
        by_row[str(r["row"])] = {**r, "building_key": key, "unit": r.get("unit") or unit,
                                 "scan_required": bool(P.SCAN_REQUIRED & set(r["handling"]))}
    pp = pickup_point or {}
    start = (pp["lat"], pp["lng"]) if pp.get("lat") is not None else (rows[0]["lat"], rows[0]["lng"])
    vs = [vrp.Vehicle(id=f"v{i}", type=vehicle_class, cap_kg=cap["kg"], cap_boxes=cap["parcels"], start=start)
          for i in range(drivers)]
    jobs = [vrp.Job(id=k, loc=(r["lat"], r["lng"]), kg=r["weight_kg"], handling=r["handling"],
                    building_key=r["building_key"], parcels=[k]) for k, r in by_row.items()]
    res = vrp.solve(vs, jobs, max_waves=8)
    if res["unassigned"]:
        raise ValueError("parcel_exceeds_vehicle_capacity")
    out = []
    for i, rt in enumerate(res["routes"], start=1):
        parcels = [{**by_row[pid], "stop_seq": seq} for seq, st in enumerate(rt["stops"], start=1) for pid in st["parcels"]]
        out.append({"route_no": i, "wave": rt["wave"], "vehicle_class": vehicle_class, "stops": len(rt["stops"]),
                    "parcels": parcels, "kg": round(sum(p["weight_kg"] for p in parcels), 2),
                    "eta": {"duration_s": rt["duration_s"], "saved_s": res["saved_s"], "naive_s": res["naive_s"]}})
    return out


def _route(db: Session, route_id: str, driver_id: str | None = None) -> BatchRoute:
    r = db.get(BatchRoute, route_id)
    if not r:
        raise LookupError("route_not_found")
    if driver_id is not None and r.driver_id != driver_id:
        raise PermissionError("not_your_route")
    if driver_id is not None and r.status in HIDDEN:
        raise LegLocked("leg_locked")
    return r


def _pickup_parcels(db: Session, r: BatchRoute) -> list[BatchParcel]:
    """What this driver collects at pickup: own share + parcels it carries for dependent legs."""
    from sqlalchemy import or_
    db.flush()
    return db.query(BatchParcel).filter(or_(BatchParcel.route_id == r.id, BatchParcel.via_route_id == r.id)).order_by(
        BatchParcel.stop_seq, BatchParcel.barcode).all()


def _parcels(db: Session, route_id: str) -> list[BatchParcel]:
    db.flush()  # sessions here run with autoflush off
    return db.query(BatchParcel).filter(BatchParcel.route_id == route_id).order_by(
        BatchParcel.stop_seq, BatchParcel.barcode).all()


def assign(db: Session, route_id: str, driver_id: str) -> BatchRoute:
    r = _route(db, route_id)
    if r.status != "planned":
        raise ValueError("route_already_started")
    r.driver_id = driver_id
    return r


def find_parcel(db: Session, batch_id: str, code: str) -> BatchParcel | None:
    """Our barcode or any linked client label (Shopify order no., client tracking id)."""
    db.flush()
    p = db.query(BatchParcel).filter(BatchParcel.batch_id == batch_id, BatchParcel.barcode == code.strip()).first()
    if p:
        return p
    n = P.norm_label(code)
    for cand in db.query(BatchParcel).filter(BatchParcel.batch_id == batch_id).all():
        if n in {P.norm_label(x) for x in (cand.client_labels or [])}:
            return cand
    return None


def link_label(db: Session, batch_id: str, parcel_id: str, code: str) -> BatchParcel:
    """First scan of an unknown client label after lookup by address/recipient links it to our parcel."""
    if find_parcel(db, batch_id, code):
        raise ValueError("label_already_linked")
    p = db.get(BatchParcel, parcel_id)
    if not p or p.batch_id != batch_id:
        raise LookupError("parcel_not_found")
    p.client_labels = [*(p.client_labels or []), code.strip()]
    return p


def lookup(db: Session, batch_id: str, q: str) -> list[dict[str, Any]]:
    ql = q.strip().lower()
    if len(ql) < 3:
        raise ValueError("query_too_short")
    rows = db.query(BatchParcel).filter(BatchParcel.batch_id == batch_id).all()
    return [_pd(p) for p in rows if ql in (p.address or "").lower() or ql in (p.recipient or "").lower()][:10]


def _batch_docs(db: Session, merchant_id: str, flags: dict[str, Any]) -> list[str]:
    """Pickup document checklist from the merchant's business type (doc 70 matrix) + C-trigger flags."""
    from types import SimpleNamespace

    from porterchain_api.job_docs.service import required_for_order
    return required_for_order(db, SimpleNamespace(merchant_id=merchant_id, compliance_metadata=flags,
                                                  status="", stops=[]))


def route_docs(db: Session, r: BatchRoute) -> list[str]:
    b = db.get(DeliveryBatch, r.batch_id)
    return list((b.plan or {}).get("pickup_docs") or [])


def pickup_view(db: Session, route_id: str, driver_id: str, *, phase: str = "at_pickup") -> dict[str, Any]:
    r = _route(db, route_id, driver_id)
    if r.status == "awaiting_handover":
        raise ValueError("collect_from_driver")
    ps = _pickup_parcels(db, r)
    lo = P.load_order([_pd(p) for p in ps])
    must = [p.barcode for p in ps if p.scan_required]
    via = {p.barcode: p.route_id for p in ps if p.via_route_id == r.id}
    docs = route_docs(db, r)
    return {"pickup_source": r.pickup_source, "pickup_point": r.pickup_point, "carry_for": via,
            "documents": JD.checklist(db, docs, route_id=r.id, phase=phase),
            "instructions": JD.driver_step(db, driver_id, "pickup", route_id=r.batch_id),
            "flow_spec": {"pickup": fs.with_instructions(fs.with_pickup_docs(
                              fs.batch_pickup_flow(scan_required=bool(must)), docs),
                              bool(JD.driver_step(db, driver_id, "pickup", route_id=r.batch_id)["must_ack"])),
                          "delivery": fs.batch_delivery_flow(grouped=True), "close": fs.batch_close_flow(),
                          "handover_give": fs.batch_handover_flow("give"),
                          "handover_receive": fs.batch_handover_flow("receive")},
            "route_id": r.id, "status": r.status, "expected": len(ps),
            "parcels": [{**_pd(p), "load_position": lo[p.barcode]} for p in ps],
            "scan_required": must, "spot_sample": P.spot_sample(r.id, [p.barcode for p in ps if not p.scan_required])}


def scan(db: Session, route_id: str, driver_id: str, code: str, *, phase: str,
         scanned: list[str] | None = None) -> dict[str, Any]:
    """Scan advice + the instructions that apply to this parcel at the scan step."""
    out = _scan(db, route_id, driver_id, code, phase=phase, scanned=scanned)
    pid = (out.get("parcel") or {}).get("id") if isinstance(out.get("parcel"), dict) else out.get("parcel_id")
    if pid is None:
        p = find_parcel(db, _route(db, route_id, driver_id).batch_id, code)
        pid = p.id if p else None
    if pid:
        b = _route(db, route_id, driver_id).batch_id
        out["instructions"] = [i for i in JD.driver_step(db, driver_id, "scan", route_id=b, parcel_id=pid)["items"]
                               if i["parcel_id"] in (None, pid)]
    return out


def _scan(db: Session, route_id: str, driver_id: str, code: str, *, phase: str,
          scanned: list[str] | None = None) -> dict[str, Any]:
    r = _route(db, route_id, driver_id)
    p = find_parcel(db, r.batch_id, code)
    if p is None:
        db.add(BatchException(id=_id(), route_id=r.id, kind="unknown_label", detail={"code": code}, driver_id=driver_id))
        return P.scan_advice(None, route_id=r.id, phase=phase, driver_id=driver_id)
    dup = p.barcode in (scanned or [])
    if dup:
        db.add(BatchException(id=_id(), route_id=r.id, kind="duplicate_scan", detail={"barcode": p.barcode},
                              driver_id=driver_id))
    ho = db.query(BatchHandover).filter(BatchHandover.status == "pending",
                                        BatchHandover.from_route_id == r.id).all()
    to = next((h.to_driver_id for h in ho if p.id in h.parcel_ids), None)
    if to is None and p.via_route_id == r.id and p.route_id != r.id and phase != "pickup":
        to = db.get(BatchRoute, p.route_id).driver_id
    owner = None
    if p.route_id != r.id and p.route_id and p.via_route_id != r.id:
        owner = db.get(BatchRoute, p.route_id).driver_id
    lo = P.load_order([_pd(x) for x in _pickup_parcels(db, r)]).get(p.barcode)
    if p.via_route_id == r.id and phase == "pickup":
        pd = {**_pd(p), "route_id": r.id}
        out = P.scan_advice(pd, route_id=r.id, phase=phase, driver_id=driver_id, scanned_before=dup, load_position=lo)
        return {**out, "carry_for_driver_id": db.get(BatchRoute, p.route_id).driver_id}
    return P.scan_advice(_pd(p), route_id=r.id, phase=phase, driver_id=driver_id, scanned_before=dup,
                         pending_handover_to=to, load_position=lo, owner_driver_id=owner)


def confirm_pickup(db: Session, route_id: str, driver_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Count + one photo + merchant handover confirm; per-parcel scans only for pharmacy/high-value/contract;
    the random spot sample must be scanned; a count mismatch needs short/extra/damaged reported."""
    r = _route(db, route_id, driver_id)
    if r.status != "planned":
        raise ValueError("pickup_already_confirmed")
    view = pickup_view(db, route_id, driver_id)
    counted = int(body.get("count", -1))
    if counted < 0:
        raise ValueError("count_required")
    if not body.get("photo_key"):
        raise ValueError("photo_required")
    if not body.get("merchant_confirmed"):
        raise ValueError("merchant_handover_not_confirmed")
    JD.assert_pickup_docs(db, route_docs(db, r), route_id=r.id)
    JD.assert_acknowledged(db, driver_id, "pickup", route_id=r.batch_id)
    scans = set(body.get("scans") or [])
    missing_req = [b for b in view["scan_required"] if b not in scans]
    damaged = set(body.get("damaged") or [])
    missing = set(body.get("missing") or [])
    if missing_req and not set(missing_req) <= missing:
        raise ValueError("per_parcel_scan_required")
    if [b for b in view["spot_sample"] if b not in scans and b not in missing]:
        raise ValueError("spot_check_incomplete")
    excs = P.count_exceptions(view["expected"], counted, len(damaged))
    reported = {e.get("kind") for e in body.get("exceptions") or []}
    unreported = [e["kind"] for e in excs if e["kind"] in ("short", "extra") and e["kind"] not in reported]
    if unreported:
        raise ValueError(f"count_mismatch_unreported:{unreported[0]}")
    if excs and excs[0]["kind"] == "short" and len(missing) != excs[0]["quantity"]:
        raise ValueError("short_parcels_not_identified")
    for e in excs:
        db.add(BatchException(id=_id(), route_id=r.id, kind=e["kind"], quantity=e["quantity"], driver_id=driver_id,
                              detail={"damaged": sorted(damaged), "missing": sorted(missing)},
                              note=next((x.get("note") for x in body.get("exceptions") or [] if x.get("kind") == e["kind"]), None)))
    ev = {"lat": body.get("lat"), "lng": body.get("lng"), "photo_key": body["photo_key"]}
    for p in _pickup_parcels(db, r):
        if p.barcode in missing:
            p.status = "missing"
            continue
        p.status = "damaged" if p.barcode in damaged else "picked_up"
        p.holder_driver_id = driver_id
        _custody(db, p, "pickup", driver_id, ev, ref=r.id)
    r.status = "pickup_confirmed"
    r.pickup = {"count": counted, "expected": view["expected"], "photo_key": body["photo_key"],
                "merchant_confirmed": True, "merchant_name": body.get("merchant_name"),
                "spot_checked": sorted(scans), "exceptions": excs, "lat": ev["lat"], "lng": ev["lng"]}
    deps = _resolve_dependents(db, r, ok=True)
    db.flush()
    return {"route_id": r.id, "status": r.status, "exceptions": excs, "dependents": deps}


def delivery_stops(db: Session, route_id: str, driver_id: str) -> list[dict[str, Any]]:
    """Locked until pickup is confirmed. Same-building parcels are one stop."""
    r = _route(db, route_id, driver_id)
    if r.status not in ("pickup_confirmed", "closed"):
        raise ValueError("pickup_not_confirmed")
    stops: dict[str, dict[str, Any]] = {}
    for p in _parcels(db, r.id):
        if p.status not in ("picked_up", "damaged", "delivered"):
            continue
        s = stops.setdefault(p.building_key, {"building_key": p.building_key, "address": p.address,
                                              "stop_seq": p.stop_seq, "parcels": []})
        s["stop_seq"] = min(s["stop_seq"], p.stop_seq)
        s["parcels"].append(_pd(p))
    out = sorted(stops.values(), key=lambda s: s["stop_seq"])
    for s in out:
        s["remaining"] = sum(1 for p in s["parcels"] if p["status"] != "delivered")
        s["handling"] = sorted({h for p in s["parcels"] for h in p["handling"]})
        etas = (r.route_plan or {}).get("etas") or {}
        s["eta_s"] = min((etas[p["id"]] for p in s["parcels"] if p["id"] in etas), default=None)
        s["flow_spec"] = fs.batch_delivery_flow(grouped=len(s["parcels"]) > 1, handling=s["handling"])
    return out


def deliver(db: Session, route_id: str, driver_id: str, codes: list[str], body: dict[str, Any] | None = None,
            *, building_key: str | None = None) -> dict[str, Any]:
    """Scan each parcel; a grouped-building scan must cover every open parcel for that building."""
    body = body or {}
    r = _route(db, route_id, driver_id)
    if r.status != "pickup_confirmed":
        raise ValueError("pickup_not_confirmed")
    found = []
    for c in codes:
        p = find_parcel(db, r.batch_id, c)
        if not p or p.route_id != r.id:
            raise ValueError(f"not_on_route:{c}")
        if p.status == "delivered":
            raise ValueError(f"already_delivered:{p.barcode}")
        found.append(p)
    if building_key is not None:
        open_ = {p.id for p in _parcels(db, r.id) if p.building_key == building_key and p.status in ("picked_up", "damaged")}
        got = {p.id for p in found}
        if got - open_:
            raise ValueError("parcel_not_in_building")
        if open_ - got:
            raise ValueError("building_scan_incomplete")
    for p in found:
        JD.assert_acknowledged(db, driver_id, "delivery", route_id=r.batch_id, parcel_id=p.id)
    for p in found:
        p.status = "delivered"
        p.holder_driver_id = None
        _custody(db, p, "delivered", driver_id, body, ref=r.id)
    db.flush()
    return {"delivered": [p.barcode for p in found]}


_DONE_ROUTE = ("closed", "cancelled")
_DONE_PARCEL = ("delivered", "return_to_depot")


def _maybe_complete_batch(db: Session, batch_id: str) -> None:
    """A batch is completed once every route is closed and every parcel is delivered or returned to depot."""
    b = db.get(DeliveryBatch, batch_id)
    if not b or b.status == "completed":
        return
    routes = db.query(BatchRoute).filter(BatchRoute.batch_id == batch_id).all()
    if not routes or any(x.status not in _DONE_ROUTE for x in routes):
        return
    parcels = db.query(BatchParcel).filter(BatchParcel.batch_id == batch_id).all()
    if all(p.status in _DONE_PARCEL for p in parcels):
        b.status = "completed"
        db.flush()


def close_route(db: Session, route_id: str, driver_id: str, dispositions: dict[str, str],
                body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Leftover parcels must each be sent to return (depot) or re-attempt before closing."""
    r = _route(db, route_id, driver_id)
    if r.status != "pickup_confirmed":
        raise ValueError("pickup_not_confirmed")
    carry = [p.barcode for p in db.query(BatchParcel).filter(BatchParcel.via_route_id == r.id,
             BatchParcel.holder_driver_id == driver_id, BatchParcel.status.in_(("picked_up", "damaged"))).all()]
    if carry:
        raise ValueError(f"handover_pending:{carry[0]}")
    left = [p for p in _parcels(db, r.id) if p.status in ("picked_up", "damaged")]
    need = [p.barcode for p in left if p.barcode not in dispositions]
    if need:
        raise ValueError(f"leftover_without_disposition:{need[0]}")
    for p in left:
        d = dispositions[p.barcode]
        if d not in ("return", "reattempt"):
            raise ValueError("bad_disposition")
        p.status = "return_to_depot" if d == "return" else "reattempt"
        _custody(db, p, d, driver_id, body or {}, ref=r.id)
    r.status = "closed"
    db.flush()
    _maybe_complete_batch(db, r.batch_id)
    return {"route_id": r.id, "status": "closed",
            "returned": [p.barcode for p in left if p.status == "return_to_depot"],
            "reattempt": [p.barcode for p in left if p.status == "reattempt"]}


def start_handover(db: Session, route_id: str, driver_id: str, to_driver_id: str, codes: list[str],
                   body: dict[str, Any]) -> BatchHandover:
    r = _route(db, route_id, driver_id)
    if r.status != "pickup_confirmed":
        raise ValueError("pickup_not_confirmed")
    if to_driver_id == driver_id:
        raise ValueError("handover_to_self")
    place = body.get("place_kind", "meeting_point")
    if place not in ("meeting_point", "depot"):
        raise ValueError("bad_place_kind")
    if not body.get("photo_key") or body.get("lat") is None or body.get("lng") is None:
        raise ValueError("handover_needs_photo_and_location")
    ids = []
    for c in codes:
        p = find_parcel(db, r.batch_id, c)
        if (not p or (p.route_id != r.id and p.via_route_id != r.id) or p.holder_driver_id != driver_id
                or p.status not in ("picked_up", "damaged")):
            raise ValueError(f"not_handoverable:{c}")
        ids.append(p.id)
    if not ids:
        raise ValueError("no_parcels")
    h = BatchHandover(id=_id(), batch_id=r.batch_id, from_route_id=r.id, from_driver_id=driver_id,
                      to_driver_id=to_driver_id, parcel_ids=ids, place_kind=place,
                      give={k: body.get(k) for k in ("lat", "lng", "photo_key")})
    db.add(h)
    db.flush()
    return h


def accept_handover(db: Session, handover_id: str, driver_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """B scans every parcel or counts + confirms. Custody moves A -> B; parcels join B's route."""
    h = db.get(BatchHandover, handover_id)
    if not h or h.to_driver_id != driver_id:
        raise LookupError("handover_not_found")
    if h.status != "pending":
        raise ValueError("handover_not_pending")
    if not body.get("photo_key") or body.get("lat") is None or body.get("lng") is None:
        raise ValueError("handover_needs_photo_and_location")
    parcels = [db.get(BatchParcel, i) for i in h.parcel_ids]
    mode = body.get("mode")
    if mode == "scan":
        got = {(find_parcel(db, h.batch_id, c) or BatchParcel(id="?")).id for c in body.get("scans") or []}
        if got != set(h.parcel_ids):
            raise ValueError("handover_scan_mismatch")
    elif mode == "count":
        if int(body.get("count", -1)) != len(parcels) or not body.get("confirmed"):
            raise ValueError("handover_count_mismatch")
        must = [p.barcode for p in parcels if p.scan_required]
        if [b for b in must if b not in (body.get("scans") or [])]:
            raise ValueError("per_parcel_scan_required")
    else:
        raise ValueError("bad_mode")
    src = db.get(BatchRoute, h.from_route_id)
    owned = {p.route_id for p in parcels if p.route_id != src.id}
    dest = None
    if len(owned) == 1:
        cand = db.get(BatchRoute, owned.pop())
        if cand and cand.driver_id == driver_id and cand.status in ("awaiting_handover", "pickup_confirmed"):
            dest = cand
            dest.status = "pickup_confirmed"
    dest = dest or (db.query(BatchRoute).filter(BatchRoute.batch_id == h.batch_id, BatchRoute.driver_id == driver_id,
                                        BatchRoute.status == "pickup_confirmed").first())
    if dest is None:
        n = db.query(BatchRoute).filter(BatchRoute.batch_id == h.batch_id).count()
        dest = BatchRoute(id=_id(), batch_id=h.batch_id, route_no=n + 1, wave=src.wave, vehicle_class=src.vehicle_class,
                          driver_id=driver_id, status="pickup_confirmed",
                          pickup={"via_handover": h.id, "count": len(parcels)})
        db.add(dest)
        db.flush()
    for p in parcels:
        _custody(db, p, "handover_out", h.from_driver_id, h.give, counterpart=driver_id, ref=h.id)
        _custody(db, p, "handover_in", driver_id, body, counterpart=h.from_driver_id, ref=h.id)
        p.route_id = dest.id
        p.via_route_id = None
        p.holder_driver_id = driver_id
    if dest.status == "pickup_confirmed" and dest.pickup_source == "driver":
        plan_route(db, dest, t0=_now_local_s())
    h.status = "accepted"
    h.to_route_id = dest.id
    h.receive = {k: body.get(k) for k in ("lat", "lng", "photo_key", "signature_key", "mode", "count")}
    db.flush()
    return {"handover_id": h.id, "to_route_id": dest.id, "parcels": len(parcels)}


def custody_chain(db: Session, parcel_id: str) -> list[dict[str, Any]]:
    rank = {"pickup": 0, "handover_out": 1, "handover_in": 2, "delivered": 3, "return": 3, "reattempt": 3}
    rows = sorted(db.query(CustodyEvent).filter(CustodyEvent.parcel_id == parcel_id).all(),
                  key=lambda e: (e.at, rank.get(e.kind, 9)))
    return [{"kind": e.kind, "driver_id": e.driver_id, "counterpart_id": e.counterpart_id, "lat": e.lat, "lng": e.lng,
             "photo_key": e.photo_key, "ref_id": e.ref_id, "at": e.at.isoformat() if e.at else None} for e in rows]


def batch_out(db: Session, b: DeliveryBatch) -> dict[str, Any]:
    routes = db.query(BatchRoute).filter(BatchRoute.batch_id == b.id).order_by(BatchRoute.route_no).all()
    return {"id": b.id, "status": b.status, "plan": b.plan,
            "routes": [{"id": r.id, "route_no": r.route_no, "wave": r.wave, "driver_id": r.driver_id,
                        "status": r.status, "parcels": len(_parcels(db, r.id))} for r in routes]}


def _notify(r: BatchRoute, kind: str, **data: Any) -> None:
    from datetime import UTC, datetime
    r.notices = [*(r.notices or []), {"kind": kind, "at": datetime.now(UTC).isoformat(), **data}]
    from sqlalchemy.orm import object_session
    db = object_session(r)
    if db is not None:
        from porterchain_api.notification_engine.notice_push import push_notice
        push_notice(db, r.driver_id, kind, r.id)


def make_dependent(db: Session, route_id: str, upstream_route_id: str, handover_point: dict[str, Any]) -> BatchRoute:
    """Route B's parcels are collected by A and handed over at a meeting point or depot.
    B stays locked (hidden, no notification) until A confirms pickup."""
    b, a = _route(db, route_id), _route(db, upstream_route_id)
    if a.batch_id != b.batch_id or a.id == b.id:
        raise ValueError("bad_dependency")
    if b.status != "planned" or a.status != "planned":
        raise ValueError("route_already_started")
    if handover_point.get("lat") is None or handover_point.get("lng") is None:
        raise ValueError("handover_point_required")
    if handover_point.get("kind", "meeting_point") not in ("meeting_point", "depot"):
        raise ValueError("bad_place_kind")
    for p in _parcels(db, b.id):
        p.via_route_id = a.id
    b.status, b.pickup_source, b.depends_on_route_id = "locked", "driver", a.id
    b.pickup_point = {"kind": "meeting_point", **handover_point}
    db.flush()
    return b


def _resolve_dependents(db: Session, a: BatchRoute, *, ok: bool) -> list[dict[str, Any]]:
    out = []
    for b in db.query(BatchRoute).filter(BatchRoute.depends_on_route_id == a.id, BatchRoute.status == "locked").all():
        mine = db.query(BatchParcel).filter(BatchParcel.route_id == b.id).all()
        got = [p for p in mine if ok and p.status in ("picked_up", "damaged")]
        lost = [p for p in mine if p not in got]
        for p in lost:
            p.status = "missing"
            p.via_route_id = None
        if not got:
            b.status = "cancelled"
            _notify(b, "leg_cancelled", reason="upstream_pickup_failed" if not ok else "upstream_short_all")
        else:
            b.status = "awaiting_handover"
            eta = plan_route(db, b, upstream=a)
            _notify(b, "leg_unlocked", parcels=len(got), from_driver_id=a.driver_id,
                    handover_point=b.pickup_point, upstream_eta_s=eta.get("start_s"))
            if lost:
                _notify(b, "leg_adjusted", removed=[p.barcode for p in lost])
        out.append({"route_id": b.id, "status": b.status, "parcels": len(got), "removed": len(lost)})
    return out


def fail_pickup(db: Session, route_id: str, driver_id: str, reason: str) -> dict[str, Any]:
    r = _route(db, route_id, driver_id)
    if r.status != "planned":
        raise ValueError("pickup_already_confirmed")
    if not reason:
        raise ValueError("reason_required")
    for p in _pickup_parcels(db, r):
        if p.route_id == r.id:
            p.status = "missing"
    r.status = "pickup_failed"
    r.pickup = {"failed": True, "reason": reason}
    deps = _resolve_dependents(db, r, ok=False)
    db.flush()
    return {"route_id": r.id, "status": r.status, "dependents": deps}


def _now_local_s() -> float:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    n = datetime.now(ZoneInfo("America/Toronto"))
    return n.hour * 3600 + n.minute * 60 + n.second


def plan_route(db: Session, r: BatchRoute, *, upstream: BatchRoute | None = None,
               t0: float | None = None) -> dict[str, Any]:
    """Re-optimise one route with the VRP (start at the pickup / handover point; dependent legs start at
    A's ETA there). Writes stop_seq + route_plan (ETAs, saved vs naive)."""
    from porterchain_api.batch_engine import vrp
    ps = [p for p in _parcels(db, r.id) if p.status not in DONE and p.lat is not None and p.lng is not None]
    pt = r.pickup_point or {}
    start = (pt.get("lat"), pt.get("lng")) if pt.get("lat") is not None else (
        (ps[0].lat, ps[0].lng) if ps else (43.6532, -79.3832))
    now = t0 if t0 is not None else _now_local_s()
    if upstream is not None:
        up = upstream.pickup or {}
        src = (up.get("lat"), up.get("lng")) if up.get("lat") is not None else start
        now += vrp.Travel()(src, start, now, upstream.vehicle_class) + vrp.SERVICE_S["driver"]
    cap = P.VEHICLE_CAPACITY.get(r.vehicle_class, P.VEHICLE_CAPACITY["cargo_van"])
    v = vrp.Vehicle(id=r.id, type=r.vehicle_class, cap_kg=cap["kg"], cap_boxes=cap["parcels"], start=start,
                    shift_start_s=now, shift_s=24 * 3600 - now if now < 24 * 3600 else 3600, driver_id=r.driver_id)
    jobs = [vrp.Job(id=p.id, loc=(p.lat, p.lng), kg=p.weight_kg, handling=list(p.handling or []),
                    building_key=p.building_key, parcels=[p.id]) for p in ps]
    res = vrp.solve([v], jobs, max_waves=1) if jobs else {"routes": [], "saved_s": 0, "naive_s": 0, "total_s": 0}
    seq_of: dict[str, int] = {}
    for rt in res["routes"]:
        for i, s in enumerate(rt["stops"], start=1):
            for pid in s["parcels"]:
                seq_of[pid] = i
    for p in ps:
        if p.id in seq_of:
            p.stop_seq = seq_of[p.id]
    r.route_plan = {"start_s": round(now), "start": list(start), "total_s": res["total_s"], "naive_s": res["naive_s"],
                    "saved_s": res["saved_s"], "solver": res.get("solver", "builtin"),
                    "etas": {pid: s["arrive_s"] for rt in res["routes"] for s in rt["stops"] for pid in s["parcels"]}}
    return r.route_plan


def route_summary(db: Session, route_id: str, driver_id: str) -> dict[str, Any]:
    r = _route(db, route_id, driver_id)
    return {"id": r.id, "status": r.status, "wave": r.wave, "pickup_source": r.pickup_source,
            "pickup_point": r.pickup_point, "depends_on_route_id": r.depends_on_route_id,
            "route_plan": r.route_plan, "notices": r.notices or [],
            "parcels": [_pd(p) for p in _parcels(db, r.id)]}


def live_reoptimise(db: Session, route_id: str, driver_id: str, event: dict[str, Any]) -> dict[str, Any]:
    """Failed stop (-> re-attempt later or return), delay, or after a handover: re-plan what's left."""
    r = _route(db, route_id, driver_id)
    if r.status != "pickup_confirmed":
        raise ValueError("pickup_not_confirmed")
    kind = event.get("type")
    t0 = _now_local_s()
    if kind == "failed_stop":
        codes = event.get("codes") or []
        for c in codes:
            p = find_parcel(db, r.batch_id, c)
            if not p or p.route_id != r.id:
                raise ValueError(f"not_on_route:{c}")
            if event.get("reattempt"):
                p.stop_seq = 10_000  # pushed to the end of today's run
            else:
                p.status = "return_to_depot"
                _custody(db, p, "return", driver_id, event, ref=r.id)
    elif kind == "delay":
        t0 += float(event.get("seconds") or 0)
    elif kind not in ("handover", "new_order", "refresh"):
        raise ValueError("unknown_event")
    if event.get("lat") is not None and event.get("lng") is not None:
        r.pickup_point = {**(r.pickup_point or {}), "lat": event["lat"], "lng": event["lng"], "kind": "current"}
    plan = plan_route(db, r, t0=t0)
    if kind == "failed_stop" and event.get("reattempt"):
        for c in event.get("codes") or []:
            p = find_parcel(db, r.batch_id, c)
            p.stop_seq = max(x.stop_seq for x in _parcels(db, r.id)) + 1
    db.flush()
    return {"route_id": r.id, "event": kind, "route_plan": plan}

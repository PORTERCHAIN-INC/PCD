"""Bulk batches: CSV -> parcels/barcodes, building grouping, capacity split/waves, pickup by count+photo+handover,
spot checks, count exceptions, grouped delivery scans, leftovers, driver handovers + custody, dependent legs,
label intelligence (our + client labels)."""
from __future__ import annotations

import uuid

import pytest

from porterchain_api.batch_engine import planner as P
from porterchain_api.batch_engine import service as svc
from porterchain_api.batch_engine.models import BatchException, BatchParcel, BatchRoute
from porterchain_api.flow_engine import flow_spec as fs

CSV = """address,recipient,weight_kg,handling,client_label,lat,lng
"Unit 5, 100 King St W, Toronto",Ana,2,fragile,#1001,43.6487,-79.3817
"Unit 9, 100 King St W, Toronto",Ben,1,,SHOP-1002,43.6487,-79.3817
"7-100 King St W, Toronto",Cy,1,signature,,43.6487,-79.3817
"20 Queen St E, Toronto",Di,3,pharmacy,CLI-77,43.6526,-79.3780
"300 Front St W, Toronto",Ed,1,upright;cold,,43.6431,-79.3889
"55 Bloor St W, Toronto",Fay,4,dolly,,43.6697,-79.3888
"""


def _m():
    return str(uuid.uuid4())


# ---------- pure planner ----------

def test_csv_parse_and_errors():
    rows, errors = P.parse_csv("address,weight_kg,handling\n,1,\n1 A St,x,\n2 B St,1,teleport\n3 C St,1,fragile\n")
    assert [e["error"] for e in errors] == ["address_required", "weight_invalid", "unknown_handling:teleport"]
    assert rows[0]["handling"] == ["fragile"]


def test_building_grouping_capacity_split_and_waves():
    rows = [{"row": i, "address": f"Unit {i}, 1 Yonge St", "weight_kg": 1, "handling": [], "client_labels": []}
            for i in range(1, 31)]
    rows += [{"row": 100 + i, "address": f"{i} Other Rd", "weight_kg": 1, "handling": [], "client_labels": []}
             for i in range(1, 31)]
    out = P.plan(rows, vehicle_class="car", drivers=1)  # 40 parcels per car
    assert len(out) == 2 and [r["wave"] for r in out] == [1, 2]
    first = [p for p in out[0]["parcels"] if p["building_key"] == "1 YONGE ST"]
    assert len(first) == 30 and len({p["stop_seq"] for p in first}) == 1  # building kept together, one stop
    assert [r["wave"] for r in P.plan(rows, vehicle_class="car", drivers=2)] == [1, 1]
    with pytest.raises(ValueError, match="parcel_exceeds"):
        P.plan([{"row": 1, "address": "x", "weight_kg": 999, "handling": [], "client_labels": []}], vehicle_class="car")


def test_load_order_sample_and_count_exceptions():
    ps = [{"barcode": f"B{i}", "stop_seq": i} for i in range(1, 6)]
    assert P.load_order(ps)["B5"] == 1 and P.load_order(ps)["B1"] == 5  # last stop loaded first
    s1 = P.spot_sample("route-x", [f"B{i}" for i in range(20)])
    assert s1 == P.spot_sample("route-x", [f"B{i}" for i in range(20)]) and 3 <= len(s1) <= 5
    assert P.count_exceptions(10, 8, 1) == [{"kind": "short", "quantity": 2}, {"kind": "damaged", "quantity": 1}]
    assert P.count_exceptions(10, 11) == [{"kind": "extra", "quantity": 1}]
    assert P.norm_label("#10-01 ") == "1001"


# ---------- service flow ----------

def _batch(db, csv=CSV, **kw):
    b = svc.create_batch(db, _m(), csv, pickup_point={"lat": 43.65, "lng": -79.38}, **kw)
    routes = db.query(BatchRoute).filter(BatchRoute.batch_id == b.id).order_by(BatchRoute.route_no).all()
    return b, routes


def _confirm(db, r, d, view, **over):
    body = {"count": view["expected"], "photo_key": "photo/1", "merchant_confirmed": True, "lat": 43.65, "lng": -79.38,
            "scans": sorted(set(view["spot_sample"]) | set(view["scan_required"]))}
    body.update(over)
    return svc.confirm_pickup(db, r.id, d, body)


def test_create_gives_one_parcel_and_barcode_per_row_grouped_by_building(db):
    b, routes = _batch(db)
    parcels = db.query(BatchParcel).filter(BatchParcel.batch_id == b.id).all()
    assert len(parcels) == 6 and len({p.barcode for p in parcels}) == 6
    king = [p for p in parcels if p.building_key == "100 KING ST W"]
    assert len(king) == 3 and len({p.stop_seq for p in king}) == 1 and {p.unit for p in king} == {"5", "9", "7"}
    assert [p.scan_required for p in parcels if "pharmacy" in p.handling] == [True]
    assert routes[0].route_plan["saved_s"] >= 0  # VRP path used because coordinates were given
    with pytest.raises(ValueError, match="bad_pickup_source"):
        svc.create_batch(db, _m(), CSV, pickup_source="moon")
    for src in ("house", "shop", "warehouse", "storage"):
        assert svc.create_batch(db, _m(), "address\n1 A St\n", pickup_source=src).id


def test_pickup_gates_count_photo_handover_spot_and_per_parcel(db):
    b, (r,) = _batch(db)
    d = "drv-a"
    svc.assign(db, r.id, d)
    v = svc.pickup_view(db, r.id, d)
    assert v["expected"] == 6 and len(v["parcels"]) == 6 and v["scan_required"]
    assert {p["load_position"] for p in v["parcels"]} == set(range(1, 7))
    assert v["flow_spec"]["pickup"]["flow_id"] == "pickup_batch"
    for over, err in (({"photo_key": None}, "photo_required"), ({"merchant_confirmed": False}, "merchant_handover"),
                      ({"scans": v["spot_sample"]}, "per_parcel_scan_required"),
                      ({"scans": v["scan_required"]}, "spot_check_incomplete"),
                      ({"count": 5}, "count_mismatch_unreported:short")):
        if over.get("scans") == v["scan_required"] and set(v["spot_sample"]) <= set(v["scan_required"]):
            continue
        with pytest.raises(ValueError, match=err):
            _confirm(db, r, d, v, **over)
    with pytest.raises(ValueError, match="pickup_not_confirmed"):
        svc.delivery_stops(db, r.id, d)  # stop list locked until pickup confirmed
    out = _confirm(db, r, d, v)
    assert out["status"] == "pickup_confirmed" and out["exceptions"] == []


def test_short_extra_damaged_exceptions(db):
    b, (r,) = _batch(db)
    svc.assign(db, r.id, "d1")
    v = svc.pickup_view(db, r.id, "d1")
    spare = next(p["barcode"] for p in v["parcels"] if not p["scan_required"])
    dmg = next(p["barcode"] for p in v["parcels"] if p["barcode"] != spare)
    with pytest.raises(ValueError, match="short_parcels_not_identified"):
        _confirm(db, r, "d1", v, count=5, exceptions=[{"kind": "short"}])
    out = _confirm(db, r, "d1", v, count=5, exceptions=[{"kind": "short", "note": "1 missing"}], missing=[spare],
                   damaged=[dmg])
    assert {e["kind"] for e in out["exceptions"]} == {"short", "damaged"}
    kinds = {e.kind for e in db.query(BatchException).filter(BatchException.route_id == r.id)}
    assert {"short", "damaged"} <= kinds
    b2, (r2,) = _batch(db)
    svc.assign(db, r2.id, "d2")
    v2 = svc.pickup_view(db, r2.id, "d2")
    assert _confirm(db, r2, "d2", v2, count=7, exceptions=[{"kind": "extra"}])["exceptions"][0]["kind"] == "extra"


def test_grouped_building_scan_each_scan_and_leftovers(db):
    b, (r,) = _batch(db)
    svc.assign(db, r.id, "d")
    _confirm(db, r, "d", svc.pickup_view(db, r.id, "d"))
    stops = svc.delivery_stops(db, r.id, "d")
    king = next(s for s in stops if s["building_key"] == "100 KING ST W")
    assert len(king["parcels"]) == 3 and king["flow_spec"]["flow_id"] == "delivery_batch_building"
    codes = [p["barcode"] for p in king["parcels"]]
    with pytest.raises(ValueError, match="building_scan_incomplete"):
        svc.deliver(db, r.id, "d", codes[:2], building_key="100 KING ST W")
    svc.deliver(db, r.id, "d", codes, building_key="100 KING ST W")
    with pytest.raises(ValueError, match="already_delivered"):
        svc.deliver(db, r.id, "d", codes[:1])
    single = next(s for s in stops if len(s["parcels"]) == 1)
    svc.deliver(db, r.id, "d", [single["parcels"][0]["barcode"]])
    left = [p.barcode for p in svc._parcels(db, r.id) if p.status == "picked_up"]
    with pytest.raises(ValueError, match="leftover_without_disposition"):
        svc.close_route(db, r.id, "d", {left[0]: "return"})
    disp = {c: ("return" if i % 2 else "reattempt") for i, c in enumerate(left)}
    out = svc.close_route(db, r.id, "d", disp)
    assert len(out["returned"]) + len(out["reattempt"]) == len(left)


def test_driver_to_driver_handover_custody_chain(db):
    b, (r,) = _batch(db)
    svc.assign(db, r.id, "A")
    _confirm(db, r, "A", svc.pickup_view(db, r.id, "A"))
    give = [p.barcode for p in svc._parcels(db, r.id)][:2]
    with pytest.raises(ValueError, match="photo_and_location"):
        svc.start_handover(db, r.id, "A", "B", give, {"place_kind": "depot"})
    h = svc.start_handover(db, r.id, "A", "B", give, {"place_kind": "depot", "lat": 43.7, "lng": -79.3, "photo_key": "g"})
    adv = svc.scan(db, r.id, "A", give[0], phase="delivery")
    assert adv["action"] == "hand_to_driver" and adv["to_driver_id"] == "B"
    with pytest.raises(ValueError, match="handover_scan_mismatch"):
        svc.accept_handover(db, h.id, "B", {"mode": "scan", "scans": give[:1], "lat": 43.7, "lng": -79.3, "photo_key": "r"})
    with pytest.raises(ValueError, match="handover_count_mismatch"):
        svc.accept_handover(db, h.id, "B", {"mode": "count", "count": 1, "confirmed": True, "lat": 1, "lng": 1, "photo_key": "r"})
    out = svc.accept_handover(db, h.id, "B", {"mode": "scan", "scans": give, "lat": 43.7, "lng": -79.3, "photo_key": "r"})
    assert out["parcels"] == 2
    assert len(svc._parcels(db, r.id)) == 4  # A's list shrinks
    b_stops = svc.delivery_stops(db, out["to_route_id"], "B")
    assert sorted(p["barcode"] for s in b_stops for p in s["parcels"]) == sorted(give)
    p0 = svc.find_parcel(db, b.id, give[0])
    chain = [e["kind"] for e in svc.custody_chain(db, p0.id)]
    assert chain[0] == "pickup" and {"handover_out", "handover_in"} <= set(chain)
    ev = [e for e in svc.custody_chain(db, p0.id) if e["kind"] == "handover_in"][0]
    assert ev["driver_id"] == "B" and ev["counterpart_id"] == "A" and ev["photo_key"] == "r" and ev["at"]


def _two_routes(db):
    csv = "address,weight_kg,lat,lng\n" + "".join(f"{i} Far Rd,1,43.{60 + i},-79.{30 + i}\n" for i in range(1, 9))
    b, routes = _batch(db, csv, drivers=2, vehicle_class="car")
    if len(routes) < 2 or not svc._parcels(db, routes[1].id):
        a = routes[0]
        for extra in routes[1:]:
            extra.status = "closed"
        ps = svc._parcels(db, a.id)
        nb = BatchRoute(id=str(uuid.uuid4()), batch_id=b.id, route_no=2, wave=1, vehicle_class="car", status="planned",
                        notices=[])
        db.add(nb)
        db.flush()
        for p in ps[len(ps) // 2:]:
            p.route_id = nb.id
        routes = [a, nb]
    return b, routes[0], routes[1]


def test_dependent_leg_locked_until_upstream_pickup_then_unlocked(db):
    b, a, bb = _two_routes(db)
    svc.assign(db, a.id, "A")
    svc.assign(db, bb.id, "B")
    svc.make_dependent(db, bb.id, a.id, {"lat": 43.70, "lng": -79.35, "kind": "meeting_point"})
    with pytest.raises(svc.LegLocked):
        svc.route_summary(db, bb.id, "B")  # no details
    assert db.get(BatchRoute, bb.id).notices == []  # no notification yet
    v = svc.pickup_view(db, a.id, "A")
    assert len(v["carry_for"]) == len(svc._parcels(db, bb.id)) and v["expected"] == 8
    carried = next(iter(v["carry_for"]))
    adv = svc.scan(db, a.id, "A", carried, phase="pickup")
    assert adv["action"] == "load" and adv["carry_for_driver_id"] == "B"
    out = _confirm(db, a, "A", v)
    assert out["dependents"][0]["status"] == "awaiting_handover"
    s = svc.route_summary(db, bb.id, "B")
    assert s["notices"][0]["kind"] == "leg_unlocked" and s["route_plan"]["start"] == [43.70, -79.35]
    assert s["route_plan"]["start_s"] > 0 and all(p["route_id"] == bb.id for p in s["parcels"])  # only B's parcels
    with pytest.raises(ValueError, match="pickup_not_confirmed"):
        svc.delivery_stops(db, bb.id, "B")
    assert svc.scan(db, a.id, "A", carried, phase="delivery")["action"] == "hand_to_driver"
    with pytest.raises(ValueError, match="handover_pending"):
        svc.close_route(db, a.id, "A", {p.barcode: "return" for p in svc._parcels(db, a.id)})
    codes = list(v["carry_for"])
    h = svc.start_handover(db, a.id, "A", "B", codes, {"lat": 43.7, "lng": -79.35, "photo_key": "g"})
    res = svc.accept_handover(db, h.id, "B", {"mode": "count", "count": len(codes), "confirmed": True,
                                              "lat": 43.7, "lng": -79.35, "photo_key": "r"})
    assert res["to_route_id"] == bb.id and db.get(BatchRoute, bb.id).status == "pickup_confirmed"
    assert svc.delivery_stops(db, bb.id, "B")


def test_dependent_leg_cancelled_or_adjusted_when_upstream_fails_or_short(db):
    b, a, bb = _two_routes(db)
    svc.assign(db, a.id, "A")
    svc.assign(db, bb.id, "B")
    svc.make_dependent(db, bb.id, a.id, {"lat": 43.7, "lng": -79.35})
    out = svc.fail_pickup(db, a.id, "A", "shop_closed")
    assert out["dependents"][0]["status"] == "cancelled"
    assert db.get(BatchRoute, bb.id).notices[0]["kind"] == "leg_cancelled"
    b2, a2, bb2 = _two_routes(db)
    svc.assign(db, a2.id, "A")
    svc.assign(db, bb2.id, "B")
    svc.make_dependent(db, bb2.id, a2.id, {"lat": 43.7, "lng": -79.35})
    v = svc.pickup_view(db, a2.id, "A")
    gone = next(iter(v["carry_for"]))
    out = _confirm(db, a2, "A", v, count=v["expected"] - 1, exceptions=[{"kind": "short"}], missing=[gone])
    assert out["dependents"][0]["removed"] == 1
    kinds = [n["kind"] for n in db.get(BatchRoute, bb2.id).notices]
    assert kinds == ["leg_unlocked", "leg_adjusted"]


# ---------- label intelligence ----------

def test_scan_advice_our_and_client_labels(db):
    b, (r,) = _batch(db)
    svc.assign(db, r.id, "d")
    v = svc.pickup_view(db, r.id, "d")
    adv = svc.scan(db, r.id, "d", "1001", phase="pickup")  # Shopify '#1001' printed as 1001
    assert adv["action"] == "load" and adv["load_position"] >= 1 and "fragile" in adv["handling"]
    assert svc.scan(db, r.id, "d", "shop-1002", phase="pickup")["action"] == "load"
    ours = v["parcels"][0]["barcode"]
    assert svc.scan(db, r.id, "d", ours, phase="pickup", scanned=[ours])["action"] == "duplicate"
    unk = svc.scan(db, r.id, "d", "ZZ-NOPE", phase="pickup")
    assert unk["action"] == "unknown_label" and unk["exception"] and "lookup_address" in unk["next"]
    hits = svc.lookup(db, b.id, "front st")
    assert len(hits) == 1
    svc.link_label(db, b.id, hits[0]["id"], "ZZ-NOPE")  # first scan links the client label
    assert svc.scan(db, r.id, "d", "zz nope", phase="pickup")["parcel_id"] == hits[0]["id"]
    with pytest.raises(ValueError, match="label_already_linked"):
        svc.link_label(db, b.id, hits[0]["id"], "1001")
    _confirm(db, r, "d", v)
    pharm = next(p for p in v["parcels"] if "pharmacy" in p["handling"])
    a = svc.scan(db, r.id, "d", "CLI-77", phase="delivery")
    assert a["action"] == "deliver" and a["stop_seq"] == pharm["stop_seq"] and "pharmacy" in a["handling"]
    svc.deliver(db, r.id, "d", ["CLI-77"])
    assert svc.scan(db, r.id, "d", "CLI-77", phase="delivery")["action"] == "already_delivered"
    other_b, (o,) = _batch(db, "address,client_label\n1 Elsewhere,OTHER-1\n")
    assert svc.scan(db, r.id, "d", "OTHER-1", phase="delivery")["action"] == "unknown_label"  # other batch


def test_scan_advice_not_this_route_and_return():
    p = {"id": "p", "barcode": "B", "stop_seq": 2, "building_key": "K", "handling": [], "status": "picked_up",
         "route_id": "r2"}
    assert P.scan_advice(p, route_id="r1", phase="delivery", driver_id="d", owner_driver_id="x")["owner_driver_id"] == "x"
    assert P.scan_advice({**p, "status": "reattempt"}, route_id="r1", phase="delivery", driver_id="d")["action"] == "return_to_depot"


def test_flow_specs_for_batches():
    assert [s["card"] for s in fs.batch_pickup_flow(scan_required=False)["steps"]][:3] == [
        "arrive_geofence", "batch_parcel_list", "spot_check"]
    assert "scan_packages" in [s["card"] for s in fs.batch_pickup_flow(scan_required=True)["steps"]]
    d = fs.batch_delivery_flow(grouped=True, handling=["pharmacy"])
    assert [s["card"] for s in d["steps"]][:3] == ["navigate", "arrive_geofence", "building_scan"]
    assert d["steps"][0]["block_if"] == ["pickup_not_confirmed"] and "id_check" in [s["card"] for s in d["steps"]]


def test_batch_routes_registered():
    from porterchain_api.main import app
    paths = set(app.openapi()["paths"])
    for p in ("/v1/merchant/batches", "/v1/admin/batches/routes/{route_id}/assign", "/v1/admin/batches/optimise",
              "/v1/admin/batches/routes/{route_id}/depends-on", "/v1/admin/batches/parcels/{parcel_id}/custody"):
        assert p in paths, p
    assert any(p.endswith("/batches/routes/{route_id}/pickup/confirm") for p in paths)
    assert any(p.endswith("/batches/handovers/{handover_id}/accept") for p in paths)
    assert any(p.endswith("/batches/routes/{route_id}/reoptimise") for p in paths)


def test_csv_unquoted_commas_is_row_error_not_crash():
    rows, errors = P.parse_csv("address,recipient,weight_kg\n1 Yonge St, Toronto, ON,Alice,2\n\"2 Bay St, Toronto\",Bob,1\n")
    assert errors == [{"row": 1, "error": "too_many_columns:quote_values_with_commas"}]
    assert [r["address"] for r in rows] == ["2 Bay St, Toronto"]


def test_batch_completes_when_all_delivered_or_returned_and_routes_closed(db):
    from porterchain_api.batch_engine.models import DeliveryBatch
    b, (r,) = _batch(db)
    svc.assign(db, r.id, "d")
    _confirm(db, r, "d", svc.pickup_view(db, r.id, "d"))
    stops = svc.delivery_stops(db, r.id, "d")
    for s in stops[:-1]:
        svc.deliver(db, r.id, "d", [p["barcode"] for p in s["parcels"]], building_key=s["building_key"])
    assert db.get(DeliveryBatch, b.id).status != "completed"
    left = [p.barcode for p in svc._parcels(db, r.id) if p.status == "picked_up"]
    svc.close_route(db, r.id, "d", {c: "return" for c in left})
    assert db.get(DeliveryBatch, b.id).status == "completed"


def test_batch_not_completed_when_parcel_left_for_reattempt(db):
    from porterchain_api.batch_engine.models import DeliveryBatch
    b, (r,) = _batch(db)
    svc.assign(db, r.id, "d")
    _confirm(db, r, "d", svc.pickup_view(db, r.id, "d"))
    left = [p.barcode for p in svc._parcels(db, r.id) if p.status == "picked_up"]
    svc.close_route(db, r.id, "d", {c: "reattempt" for c in left})
    assert db.get(DeliveryBatch, b.id).status != "completed"

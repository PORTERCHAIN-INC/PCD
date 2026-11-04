"""Bulk scenario rules (batch_engine.scenarios)."""
from __future__ import annotations

import pytest

from porterchain_api.batch_engine import scenarios as S


def _p(i, **kw):
    return {"barcode": f"B{i:03d}", "handling": [], **kw}


def test_verification_by_risk():
    low = [_p(i) for i in range(20)]
    v = S.verification("r1", low)
    assert v["level"] == "low" and not v["scan_all"] and 3 <= len(v["spot_scan"]) <= 5
    assert v == S.verification("r1", low)  # deterministic per route
    for h in ("pharmacy", "high_value", "contract", "customs"):
        assert S.verification("r2", [_p(1, handling=[h])])["level"] == "high"
    mixed = S.verification("r3", low + [_p(99, handling=["customs"])])
    assert mixed["level"] == "mixed" and "B099" in mixed["must_scan"]
    b = S.verification_blockers(mixed, counted=None, photo=False, merchant_confirmed=False, scanned=set())
    assert {"count_required", "photo_required", "merchant_confirm_required", "scan_required:B099"} <= set(b)
    assert S.verification_blockers(mixed, counted=21, photo=True, merchant_confirmed=True,
                                   scanned=set(mixed["must_scan"])) == []


def test_split_one_pickup_across_drivers():
    ps = [_p(i, zone="east" if i % 2 else "west") for i in range(10)] + [_p(50, zone="north")]
    out = S.split_pickup(ps, {"rA": {"zones": ["east"]}, "rB": {"zones": ["west"]}})
    assert len(out["rA"]) == 5 and len(out["rB"]) == 5 and out["unassigned"] == ["B050"]


def test_cross_dock_sorts_by_zone():
    ps = [_p(1, zone="z1"), _p(2, zone="z2"), _p(3, zone="z1"), _p(4, zone="zz")]
    out = S.cross_dock(ps, {"z1": "o1", "z2": "o2"})
    assert out["outbound"] == {"o1": ["B001", "B003"], "o2": ["B002"]} and out["return_to_sender_same_day"] == ["B004"] and out["depot_storage"] is False
    assert out["custody_steps"][1] == "handover_out"


def test_multi_pickup_consolidation():
    pk = [{"id": "p1", "status": "confirmed", "counted": 4}, {"id": "p2", "status": "pending"}]
    c = S.consolidate(pk, {"id": "d"})
    assert c["locked"] and c["waiting_on"] == ["p2"]
    pk[1].update(status="confirmed", counted=6)
    c = S.consolidate(pk, {"id": "d"})
    assert not c["locked"] and c["expected_at_drop"] == 10 and c["stops"][-1] == "d"


def test_partial_pickup_schedules_second():
    out = S.partial_pickup(["a", "b", "c"], ["a"], next_slot="2026-10-30T14:00")
    assert out["second_pickup"] == {"barcodes": ["b", "c"], "slot": "2026-10-30T14:00", "status": "scheduled"}
    assert S.partial_pickup(["a", "b"], ["a"], next_slot=None)["ask_admin"]
    assert S.partial_pickup(["a"], ["a"], next_slot=None)["status"] == "complete"


def test_reverse_pickup_same_route():
    stops = [{"id": "s1", "deliver": 5, "building_key": "x"}, {"id": "s2", "deliver": 5, "building_key": "y"}]
    out = S.add_reverse_pickup(stops, {"id": "ret", "collect": 3, "building_key": "y"}, capacity=10)
    assert [s["id"] for s in out] == ["s1", "s2", "ret"]  # merged at its building
    out = S.add_reverse_pickup(stops, {"id": "ret", "collect": 3}, capacity=10)
    assert [s["id"] for s in out] == ["s1", "ret", "s2"]  # first point with room
    with pytest.raises(ValueError):
        S.add_reverse_pickup(stops, {"id": "ret", "collect": 11}, capacity=10)


def test_failed_delivery_per_merchant_rule():
    assert S.failed_disposition({"attempts": 1}, None)["action"] == "reattempt"
    assert S.failed_disposition({"attempts": 2}, None)["action"] == "return_to_sender"
    rule = {"order": ["neighbour", "locker", "depot"], "neighbour_ok": True, "locker_ok": True}
    assert S.failed_disposition({}, rule)["action"] == "neighbour"
    rx = S.failed_disposition({"handling": ["pharmacy"]}, rule)  # doc 70: same-day back to pharmacy
    assert rx["action"] == "return_to_sender" and rx["same_day"]
    assert S.failed_disposition({"handling": ["high_value"]}, rule)["action"] == "return_to_sender"  # never neighbour/locker
    assert S.failed_disposition({}, {**rule, "neighbour_ok": False})["action"] == "locker"


def test_oversize_reassign():
    d = [{"id": "d1", "vehicle_class": "suv"}, {"id": "d2", "vehicle_class": "box_truck"},
         {"id": "d3", "vehicle_class": "cargo_van", "available": False}]
    assert S.reassign_oversize({"weight_kg": 10}, "car", d)["action"] == "keep"
    r = S.reassign_oversize({"weight_kg": 60, "longest_cm": 120}, "car", d)
    assert r["driver_id"] == "d2" and r["dolly"]
    assert S.reassign_oversize({"weight_kg": 999}, "car", d)["action"] == "ask_admin"


def test_containers_counted_not_parcels():
    cs = [{"id": "c1", "kind": "cage", "parcels": ["a", "b"]}, {"id": "c2", "kind": "tote", "parcels": ["c"]},
          {"id": "c3", "kind": "pallet", "parcels": ["d"] * 20, "seal": "S1", "seal_seen": "S9"}]
    out = S.container_count(cs, {"cage": 1, "tote": 0, "pallet": 1})
    assert out["parcels"] == 23 and out["exceptions"] == [{"kind": "short", "container": "tote", "quantity": 1}]
    assert out["open_and_scan"] == ["c3"]
    with pytest.raises(ValueError):
        S.container_count([{"id": "x", "kind": "bag"}])


def test_mixed_business_types_keep_rules():
    rx = S.stop_rules({"business_type": "pharmacy"})
    retail = S.stop_rules({"business_type": "retail", "handling": ["fragile"]})
    assert rx["scan_required"] and "pharmacy_custody" in rx["docs"]
    assert not retail["scan_required"] and retail["docs"] == [] and retail["handling"] == ["fragile"]
    assert S.stop_rules({"business_type": "customs"})["docs"] == ["commercial_invoice", "cbsa_release"]


def test_driver_unavailable_reassigns_with_handover():
    rem = [_p(1), _p(2, handling=["pharmacy"])]
    ds = [{"id": "me", "vehicle_class": "car", "lat": 43.6, "lng": -79.4},
          {"id": "far", "vehicle_class": "car", "lat": 43.9, "lng": -79.0},
          {"id": "near", "vehicle_class": "car", "lat": 43.61, "lng": -79.41},
          {"id": "full", "vehicle_class": "car", "lat": 43.6, "lng": -79.4, "load": 40}]
    r = S.reassign_remaining(rem, "me", ds, {"lat": 43.6, "lng": -79.4})
    assert r["to_driver_id"] == "near" and r["handover"]["custody"] == "scan_each"
    assert S.reassign_remaining(rem, "me", ds[:1], {"lat": 0, "lng": 0})["action"] == "ask_admin"


def test_time_window_clash():
    st = [{"id": "a", "window_end": 5000}, {"id": "b", "window_end": 1000}]
    assert S.resolve_windows(st, start_s=0)["action"] == "resequenced"
    assert S.resolve_windows(st[::-1], start_s=0)["action"] == "keep"
    r = S.resolve_windows([{"id": "a", "window_end": 100}, {"id": "b", "window_end": 200}], start_s=0)
    assert r["action"] == "ask_admin" and r["clashes"]


def test_admin_scenario_and_list_endpoints(db):
    from fastapi.testclient import TestClient

    from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.db import get_db
    from porterchain_api.main import app

    def client(role):
        ctx = AdminContext(user=AdminUser(auth_subject=f"pc-{role}", email=f"{role}@x.test", role=role),
                           role=parse_admin_role(role))
        app.dependency_overrides[get_admin_context] = lambda: ctx
        app.dependency_overrides[get_db] = lambda: db
        return TestClient(app)
    try:
        c = client("dispatcher")
        r = c.post("/v1/admin/batches/scenarios/failed_disposition", json={"parcel": {"attempts": 2}, "rule": None})
        assert r.status_code == 200 and r.json()["result"]["action"] == "return_to_sender"
        assert c.post("/v1/admin/batches/scenarios/nope", json={}).status_code == 404
        assert c.post("/v1/admin/batches/scenarios/stop_rules", json={"bad": 1}).status_code == 422
        assert c.get("/v1/admin/batches").status_code == 200
        assert client("sales").get("/v1/admin/batches").status_code == 403
    finally:
        app.dependency_overrides.clear()

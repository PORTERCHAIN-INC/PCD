"""Doc 80 A-VC: CVOR threshold, DVIR, HOS, weight block, trip record, offline replay."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from porterchain_api.compliance_engine import rules
from porterchain_api.compliance_engine import service as comp
from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor
from unittest.mock import MagicMock

NOW = datetime(2026, 10, 29, 18, 0, tzinfo=UTC)
CIVIC = {"plate": "abcd123", "rgw_kg": 1800, "gvwr_kg": 1800, "curb_kg": 1300, "insurance_evidence_ref": "pink-slip"}
TRUCK = {"plate": "TRK999", "rgw_kg": 7000, "is_rental": True, "rental_agreement_ref": "UH-1", "rental_days": 1,
         "insurance_evidence_ref": "cargo-cert"}


def _dvir(plate, heavy=False, major=False, at=None, **kw):
    items = {i: "ok" for i in (rules.SCHEDULE_1 if heavy else rules.WALKAROUND)}
    if major:
        items["tires" if heavy else "front"] = "major"
    return {"plate": plate, "operator_name": "PorterChain", "location": "Toronto", "inspector_name": "Ravi",
            "odometer_km": 12000, "signed_statement": True, "items": items, "heavy": heavy,
            "inspected_at": (at or NOW).isoformat(), **kw}


def test_cvor_threshold_and_eld():
    assert not rules.cvor_required(4500) and rules.cvor_required(4501)
    assert not rules.eld_required(is_rental=True, rental_days=30, radius_ok=False)
    assert rules.eld_required(is_rental=True, rental_days=31, radius_ok=False)
    assert not rules.eld_required(is_rental=False, rental_days=None, radius_ok=True)


def test_weight_block():
    rules.check_weight(400, rgw_kg=1800, gvwr_kg=1800, curb_kg=1300)
    with pytest.raises(ValueError, match="vehicle_overweight"):
        rules.check_weight(420, rgw_kg=1800, gvwr_kg=1800, curb_kg=1300)


def test_dvir_validation():
    with pytest.raises(ValueError, match="dvir_not_signed"):
        rules.validate_dvir({**_dvir("X"), "signed_statement": False}, heavy=False)
    with pytest.raises(ValueError, match="dvir_incomplete"):
        rules.validate_dvir(_dvir("X"), heavy=True)
    assert rules.validate_dvir(_dvir("X", heavy=True, major=True), heavy=True)["major_defect"]
    assert rules.dvir_valid(NOW - timedelta(hours=23), False, NOW)
    assert not rules.dvir_valid(NOW - timedelta(hours=25), False, NOW)


def test_hos_warn_and_block():
    start = NOW - timedelta(hours=14, minutes=30)
    ev = [{"status": "off_duty", "at": start - timedelta(hours=10)}, {"status": "driving", "at": start}]
    s = rules.hos_summary(ev, NOW)
    assert "driving" in s["blocked"] and not s["can_take_offers"]
    ev = [{"status": "off_duty", "at": NOW - timedelta(hours=22)}, {"status": "on_duty", "at": NOW - timedelta(hours=12, minutes=30)},
          {"status": "driving", "at": NOW - timedelta(hours=12)}]
    s = rules.hos_summary(ev, NOW)
    assert s["warnings"] == ["driving"] and s["can_take_offers"]


def test_trip_requires_record_and_civic_starts(db):
    with pytest.raises(ValueError, match="insurance_evidence_required"):
        comp.create_trip(db, "drv-1", {**CIVIC, "insurance_evidence_ref": None})
    with pytest.raises(ValueError, match="rental_agreement_required"):
        comp.create_trip(db, "drv-1", {**TRUCK, "rental_agreement_ref": None})
    t = comp.create_trip(db, "drv-1", {**CIVIC, "declared_kg": 300})
    assert t.plate == "ABCD123" and not t.cvor_required
    assert comp.start_trip(db, "drv-1", t.id, now=NOW).status == "started"
    over = comp.create_trip(db, "drv-1", {**CIVIC, "declared_kg": 500})
    with pytest.raises(ValueError, match="vehicle_overweight"):
        comp.start_trip(db, "drv-1", over.id, now=NOW)


def test_heavy_truck_blocked_until_cvor_then_needs_dvir(db, monkeypatch):
    t = comp.create_trip(db, "drv-2", TRUCK)
    assert t.cvor_required
    with pytest.raises(ValueError, match="cvor_not_issued"):
        comp.start_trip(db, "drv-2", t.id, now=NOW)
    monkeypatch.setattr(comp, "heavy_trucks_enabled", lambda: True)
    with pytest.raises(ValueError, match="dvir_required"):
        comp.start_trip(db, "drv-2", t.id, now=NOW)
    comp.submit_dvir(db, "drv-2", _dvir("TRK999", heavy=True, major=True, at=NOW - timedelta(hours=1)))
    with pytest.raises(ValueError, match="dvir_required"):
        comp.start_trip(db, "drv-2", t.id, now=NOW)
    r = comp.submit_dvir(db, "drv-2", _dvir("TRK999", heavy=True, at=NOW - timedelta(minutes=10)))
    assert r.kind == "schedule1" and comp.dvir_out(r)["retain_until"] > NOW.isoformat()
    started = comp.start_trip(db, "drv-2", t.id, now=NOW)
    assert started.inspection_due_at is not None


def test_hos_offline_replay_is_idempotent_and_keeps_phone_time(db):
    ex = DriverOfflineExecutor(platform=MagicMock())
    drv = SimpleNamespace(id="drv-3")
    at = (datetime.now(UTC) - timedelta(hours=2)).replace(microsecond=0)
    payload = {"client_id": "11111111-1111-4111-8111-111111111111", "status": "on_duty", "at": at.isoformat(),
               "other_operator_today": True}
    ex.execute(db, drv, "hos_event", payload)
    ex.execute(db, drv, "hos_event", payload)
    out = comp.hos_today(db, "drv-3")
    assert len(out["daily_record"]) == 1
    assert out["daily_record"][0]["at"] == at.isoformat()
    assert out["full_daily_log_required"] and not out["radius_exemption"]
    with pytest.raises(ValueError, match="hos_bad_status"):
        comp.record_hos(db, "drv-3", {"status": "napping", "at": at.isoformat()})


def test_routes_registered():
    from porterchain_api.main import app

    paths = set(app.openapi()["paths"])
    for p in ("/driver-api/v1/compliance/trips", "/driver-api/v1/compliance/trips/{trip_id}/start",
              "/driver-api/v1/compliance/dvir", "/driver-api/v1/compliance/hos/events", "/driver-api/v1/compliance/hos/today"):
        assert p in paths, p

"""End-to-end over HTTP (real routers + Postgres): signed labels, scan gates, lookup,
ownership, offline replay, rate limit and audit rows. Build-29 request shape included."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import porterchain_api.main as main
from porterchain_api.admin_models import Driver
from porterchain_api.auth.driver import get_driver_context
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import DomainEvent, Order, Package
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.driver_engine import scan_audit
from porterchain_api.driver_engine.rbac import DriverContext
from porterchain_api.merchant_models import Merchant
from porterchain_api.reporting.label_service import LabelService
from porterchain_api.reporting.qr_codec import encode_label_qr

D = "/driver-api/v1"


def _driver(db):
    s = uuid4().hex[:8]
    d = Driver(email=f"e2e-{s}@test.local", full_name=f"E2E {s}", status="APPROVED",
               clerk_user_id=f"clerk_e2e_{s}", phone="+14165550199")
    db.add(d)
    db.flush()
    return d


def _order(db, merchant_id, driver_id, boxes=2):
    o = Order(order_number=generate_order_number(), tracking_number=generate_tracking_number(),
              state="DRIVER_ASSIGNED", merchant_id=merchant_id, amount_cents=1000, currency="cad",
              pickup={"street": "8500 Mount Pleasant Wy", "city": "Milton", "postal_code": "L9E 1J7"},
              dropoff={"street": "1 King St W", "postal_code": "M5H 1A1"},
              scheduled_at=datetime.now(UTC), assigned_driver_id=driver_id)
    db.add(o)
    db.flush()
    for i in range(1, boxes + 1):
        db.add(Package(order_id=o.id, parcel_index=i, total_parcels=boxes,
                       tracking_suffix=f"{o.tracking_number}-{i}", status="manifested"))
    db.flush()
    return o


@pytest.fixture
def world(db, monkeypatch):
    db.commit = db.flush  # keep everything inside the test transaction
    s = uuid4().hex[:8]
    m = Merchant(company_name=f"E2E {s}", email=f"m-{s}@test.local", status=MerchantStatus.ACTIVE.value)
    db.add(m)
    db.flush()
    me, other = _driver(db), _driver(db)
    mine = _order(db, m.id, me.id)
    theirs = _order(db, m.id, other.id)
    unassigned = _order(db, m.id, None)
    who = {"d": me}
    main.app.dependency_overrides[get_db] = lambda: db
    main.app.dependency_overrides[get_driver_context] = lambda: DriverContext(driver=who["d"])
    monkeypatch.setattr(scan_audit, "check_fixed_window", None, raising=False)
    from porterchain_api.platform import rate_limit
    counts: dict[str, int] = {}

    def fake_window(key, limit, window=None):
        counts[key] = counts.get(key, 0) + 1
        return counts[key] <= limit, counts[key], None

    monkeypatch.setattr(rate_limit, "check_fixed_window", fake_window)
    yield {"db": db, "me": me, "other": other, "mine": mine, "theirs": theirs,
           "unassigned": unassigned, "who": who, "client": TestClient(main.app)}
    main.app.dependency_overrides.pop(get_db, None)
    main.app.dependency_overrides.pop(get_driver_context, None)


def _labels(db, order):
    pkgs = db.query(Package).filter(Package.order_id == order.id).order_by(Package.parcel_index).all()
    return LabelService()._page_dicts(order, pkgs, merchant_name="E2E"), pkgs


def _audit(db, driver_id):
    return [e.payload for e in db.query(DomainEvent).filter(
        DomainEvent.event_type == scan_audit.SCAN_EVENT, DomainEvent.aggregate_id == driver_id)]


def test_e2e_label_scan_flows(world):
    db, c, me, mine = world["db"], world["client"], world["me"], world["mine"]
    pages, pkgs = _labels(db, mine)
    # Labels carry only the signed opaque code.
    for p in pages:
        assert p["qr_payload"].startswith("PC1.")
        assert mine.id not in p["qr_payload"] and "|" not in p["qr_payload"]

    gps = {"lat": 43.52, "lng": -79.88, "accuracy_m": 8}
    # Build-29 request shape exactly: {qr_payload, phase}
    r = c.post(f"{D}/orders/{mine.id}/packages/scan", json={"qr_payload": pages[0]["qr_payload"], "phase": "pickup"})
    assert r.status_code == 200, r.text
    assert r.json()["scanned"] == 1 and r.json()["required"] == 2
    # Old printed label (LOGISTICSv1) still scans
    legacy = encode_label_qr(order_id=mine.id, package_id=pkgs[1].id)
    r = c.post(f"{D}/orders/{mine.id}/packages/scan", json={"qr_payload": legacy, "phase": "pickup", **gps})
    assert r.status_code == 200 and r.json()["complete"] is True
    # Forged: valid shape, wrong signature -> build-29-compatible code
    forged = pages[0]["qr_payload"][:-4] + "AAAA"
    r = c.post(f"{D}/orders/{mine.id}/packages/scan", json={"qr_payload": forged, "phase": "delivery"})
    assert r.status_code == 400 and "unknown_package" in r.json()["detail"]
    assert r.json()["detail"].startswith("invalid_label_qr")
    # Another driver's parcel scanned against my order -> wrong stop / mismatch
    tpages, _ = _labels(db, world["theirs"])
    r = c.post(f"{D}/orders/{mine.id}/packages/scan", json={"qr_payload": tpages[0]["qr_payload"], "phase": "pickup"})
    assert r.status_code == 400 and r.json()["detail"] == "qr_order_mismatch"
    # Acting on another driver's order / an unassigned order -> 403
    for o in (world["theirs"], world["unassigned"]):
        r = c.post(f"{D}/orders/{o.id}/packages/scan", json={"qr_payload": tpages[0]["qr_payload"], "phase": "pickup"})
        assert r.status_code == 403
        assert c.get(f"{D}/orders/{o.id}/pickup-checklist").status_code == 403

    # Scan-anytime lookup: mine OK (+wrong-stop warning), theirs/forged/unassigned not_yours
    r = c.post(f"{D}/scan/lookup", json={"code": pages[0]["qr_payload"], **gps})
    assert r.status_code == 200 and r.json()["parcel"]["status"] == "picked_up"
    assert r.json()["next_phase"] == "delivery" and r.json()["warning"] is None
    r = c.post(f"{D}/scan/lookup", json={"code": pages[0]["qr_payload"], "expected_order_id": "other"})
    assert r.json()["warning"] == "wrong_stop"
    upages, _ = _labels(db, world["unassigned"])
    for code in (tpages[0]["qr_payload"], forged, upages[0]["qr_payload"], "nonsense"):
        r = c.post(f"{D}/scan/lookup", json={"code": code})
        assert r.status_code == 404 and r.json()["detail"] == {"code": "not_yours"}
        assert "order" not in r.text and "parcel" not in r.text

    # Delivery scan + offline replay of the second box
    r = c.post(f"{D}/orders/{mine.id}/packages/scan", json={"qr_payload": pages[0]["qr_payload"], "phase": "delivery"})
    assert r.status_code == 200
    from porterchain_api.driver_engine.offline_executor import DriverOfflineExecutor
    DriverOfflineExecutor().execute(db, me, "package_scan", {
        "order_id": mine.id, "qr_payload": pages[1]["qr_payload"], "phase": "delivery",
        "scanned_at": "2026-10-15T23:00:00-04:00", **gps})
    db.refresh(pkgs[1])
    assert pkgs[1].status == "delivered"

    # History endpoint (portal) and audit rows: driver, GPS, client time, results
    hist = c.get(f"{D}/scan/history").json()["items"]
    assert hist and {"ok", "wrong_stop", "not_yours"} <= {h["result"] for h in hist}
    rows = _audit(db, me.id)
    assert any(p["offline_replay"] and p["scanned_at_client"] for p in rows)
    assert any(p["lat"] == 43.52 and p["lng"] == -79.88 for p in rows)
    assert all(p.get("order_id") is None for p in rows if p["result"] == "not_yours")


def test_e2e_rate_limit(world):
    c, mine = world["client"], world["mine"]
    pages, _ = _labels(world["db"], mine)
    codes = [c.post(f"{D}/scan/lookup", json={"code": pages[0]["qr_payload"]}).status_code
             for _ in range(scan_audit.SCAN_LIMIT_PER_MINUTE + 1)]
    assert codes[-1] == 429 and set(codes[:-1]) == {200}

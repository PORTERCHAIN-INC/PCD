"""Pickup document checklist (doc 80/81) + per-order/per-parcel instructions with visibility, edit log, acks."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from porterchain_api.batch_engine import service as svc
from porterchain_api.batch_engine.models import BatchException, BatchParcel, BatchRoute
from porterchain_api.flow_engine import flow_spec as fs
from porterchain_api.job_docs import rules as R
from porterchain_api.job_docs import service as JD

CSV = "address,recipient,weight_kg,lat,lng\n\"1 A St, Toronto\",Ana,1,43.65,-79.38\n\"2 B St, Toronto\",Ben,1,43.66,-79.39\n"
SIG = {"media_key": "doc/1", "shipper_name": "Sam Shipper", "shipper_signature_key": "sig/1"}


def test_required_docs_rules():
    assert R.required_pickup_docs({"pod"}, {}) == []
    assert R.required_pickup_docs({"bol", "packing_slip"}, {}) == ["bol", "packing_list", "signed_handover"]
    assert R.required_pickup_docs({"customs_docs"}, {}) == []  # only for released customs goods
    full = R.required_pickup_docs({"customs_docs", "rx_custody_log", "tdg"}, {"customs_released": True,
                                                                         "dangerous_goods": True})
    assert full == ["commercial_invoice", "cbsa_release", "pharmacy_custody", "dg_declaration", "seal_number",
                    "signed_handover"]
    for body, err in (({}, "photo_or_scan_required"), ({"scan_code": "X"}, "shipper_name_required"),
                      ({"scan_code": "X", "shipper_name": "S"}, "shipper_signature_required")):
        with pytest.raises(ValueError, match=err):
            R.validate_capture("bol", body)
    with pytest.raises(ValueError, match="seal_no_required"):
        R.validate_capture("seal_number", SIG)
    assert R.gate(["bol", "packing_list"], {"bol": "captured", "packing_list": "missing"}) == []
    assert R.gate(["bol"], {"bol": "missing"}) == ["bol"]  # blocking stays blocking
    assert "Bill of lading" in R.reminders(["bol"], {}, "before_arrival")[0]
    assert R.reminders(["bol"], {"bol": "captured"}, "at_pickup") == []
    assert R.reminders(["bol"], {}, "at_pickup", "fr")[0].startswith("À la collecte")


def test_flow_inserts_docs_and_instructions_cards():
    base = fs.batch_pickup_flow(scan_required=False)
    spec = fs.with_pickup_docs(base, ["bol"])
    cards = [s["card"] for s in spec["steps"]]
    assert "pickup_docs" in cards and spec["pickup_docs"] == ["bol"]
    assert fs.with_pickup_docs(base, []) is base
    assert fs.with_instructions(base, True)["steps"][0]["card"] == "instructions"


def _batch(db, flags=None):
    b = svc.create_batch(db, str(uuid.uuid4()), CSV, pickup_point={"lat": 43.65, "lng": -79.38}, doc_flags=flags)
    r = db.query(BatchRoute).filter(BatchRoute.batch_id == b.id).first()
    svc.assign(db, r.id, "drv")
    return b, r


def _confirm(db, r):
    v = svc.pickup_view(db, r.id, "drv")
    return svc.confirm_pickup(db, r.id, "drv", {"count": v["expected"], "photo_key": "p", "merchant_confirmed": True,
                                                 "scans": sorted(set(v["spot_sample"]) | set(v["scan_required"]))})


def test_batch_pickup_blocked_until_docs_captured(db, monkeypatch):
    monkeypatch.setattr(svc, "_batch_docs", lambda *_a, **_k: ["bol", "packing_list", "seal_number", "signed_handover"])
    b, r = _batch(db)
    v = svc.pickup_view(db, r.id, "drv", phase="before_arrival")
    assert [i["doc_type"] for i in v["documents"]["items"]] == ["bol", "packing_list", "seal_number", "signed_handover"]
    assert v["documents"]["reminders"][0].startswith("Before you arrive")
    assert "pickup_docs" in [s["card"] for s in v["flow_spec"]["pickup"]["steps"]]
    with pytest.raises(ValueError, match="pickup_documents_missing:bol"):
        _confirm(db, r)
    req = svc.route_docs(db, r)
    with pytest.raises(ValueError, match="document_not_required"):
        JD.capture(db, req, "dg_declaration", SIG, "drv", route_id=r.id)
    JD.capture(db, req, "bol", SIG, "drv", route_id=r.id)
    JD.capture(db, req, "seal_number", {**SIG, "seal_no": "S-991"}, "drv", route_id=r.id)
    JD.capture(db, req, "signed_handover", SIG, "drv", route_id=r.id)
    with pytest.raises(ValueError, match="pickup_documents_missing:packing_list"):
        _confirm(db, r)
    JD.report_missing(db, req, "packing_list", "shipper has none", "drv", route_id=r.id)  # non-blocking -> exception
    assert db.query(BatchException).filter(BatchException.route_id == r.id,
                                           BatchException.kind == "document_missing").count() == 1
    assert _confirm(db, r)["status"] == "pickup_confirmed"
    docs = JD.documents_out(db, route_id=r.id)
    assert {d["doc_type"] for d in docs} == {"bol", "seal_number", "signed_handover", "packing_list"}
    assert next(d for d in docs if d["doc_type"] == "seal_number")["seal_no"] == "S-991"


def test_batch_doc_flags_from_business_matrix(db):
    b, r = _batch(db, {"bol_required": True})
    assert "bol" in svc.route_docs(db, r) and svc.route_docs(db, r)[-1] == "signed_handover"
    b2, r2 = _batch(db)
    assert svc.route_docs(db, r2) == []  # plain batch: nothing extra beyond count+photo+handover


def test_instructions_visibility_privacy_ack_and_log(db):
    b, r = _batch(db)
    p = db.query(BatchParcel).filter(BatchParcel.route_id == r.id).first()
    must = JD.add_instruction(db, "merchant", "m1", {"text": "Dock 4, ring bell", "priority": "must_read",
                                                     "steps": ["pickup"]}, route_id=b.id)
    JD.add_instruction(db, "merchant", "m1", {"text": "PO terms net-30, margin 22%", "business": True,
                                              "steps": ["pickup"], "visibility": ["driver", "merchant", "admin"]},
                       route_id=b.id)
    JD.add_instruction(db, "partner", "pt1", {"text": "Fragile glass", "steps": ["scan"], "parcel_id": p.id,
                                              "priority": "high"}, route_id=b.id)
    JD.add_instruction(db, "admin", "a1", {"text": "Ops only", "visibility": ["admin"]}, route_id=b.id)
    step = JD.driver_step(db, "drv", "pickup", route_id=b.id)
    texts = [i["text"] for i in step["items"]]
    assert texts == ["Dock 4, ring bell"]  # business + admin-only hidden from drivers
    assert "visibility" not in step["items"][0] and step["must_ack"] == [must.id]
    v = svc.pickup_view(db, r.id, "drv")
    assert v["flow_spec"]["pickup"]["steps"][0]["card"] == "instructions"
    with pytest.raises(ValueError, match="instruction_not_acknowledged"):
        _confirm(db, r)
    JD.acknowledge(db, must.id, "drv")
    assert _confirm(db, r)["status"] == "pickup_confirmed"
    adv = svc.scan(db, r.id, "drv", p.barcode, phase="delivery")
    assert [i["text"] for i in adv["instructions"]] == ["Fragile glass"]
    # edit -> version bump re-requires ack; log keeps author + time
    JD.edit_instruction(db, must.id, "merchant", "m1", {"text": "Dock 5"})
    assert JD.driver_step(db, "drv", "pickup", route_id=b.id)["must_ack"] == [must.id]
    with pytest.raises(PermissionError):
        JD.edit_instruction(db, must.id, "merchant", "other", {"text": "x"})
    h = JD.history(db, must.id)
    assert [e["action"] for e in h] == ["create", "edit"] and h[1]["before"]["text"] == "Dock 4, ring bell"
    assert h[1]["author_id"] == "m1" and h[1]["at"]
    assert len(JD.for_viewer(db, "admin", route_id=b.id)) == 4


def test_must_read_delivery_instruction_blocks_delivery(db):
    b, r = _batch(db)
    _confirm(db, r)
    p = db.query(BatchParcel).filter(BatchParcel.route_id == r.id).first()
    i = JD.add_instruction(db, "customer", "c1", {"text": "Leave with concierge", "priority": "must_read",
                                                  "parcel_id": p.id}, route_id=b.id)
    with pytest.raises(ValueError, match="instruction_not_acknowledged"):
        svc.deliver(db, r.id, "drv", [p.barcode])
    JD.acknowledge(db, i.id, "drv")
    assert svc.deliver(db, r.id, "drv", [p.barcode])["delivered"] == [p.barcode]


def test_customer_limited_to_own_delivery(db):
    for body, err in (({"text": "x", "steps": ["pickup"]}, "customer_delivery_only"),
                      ({"text": "x", "business": True}, "customer_visibility_limited"),
                      ({"text": "x", "visibility": ["merchant"]}, "customer_visibility_limited"),
                      ({"text": "x", "parcel_id": "someone-else"}, "not_your_parcel")):
        with pytest.raises(PermissionError, match=err):
            JD.add_instruction(db, "customer", "c1", body, order_id="o1", own_parcels={"mine"})
    with pytest.raises(PermissionError):
        JD.add_instruction(db, "driver", "d", {"text": "x"}, order_id="o1")
    assert JD.add_instruction(db, "customer", "c1", {"text": "Gate 1234", "parcel_id": "mine"}, order_id="o1",
                              own_parcels={"mine"}).id


def _admin(app, role="dispatcher"):
    from porterchain_api.admin_engine.rbac import AdminContext, AdminUser, parse_admin_role
    from porterchain_api.auth.admin import get_admin_context
    app.dependency_overrides[get_admin_context] = lambda: AdminContext(
        user=AdminUser(auth_subject="adm-1", email="a@x.test", role=role), role=parse_admin_role(role))
    return get_admin_context


def test_admin_endpoints_partner_on_behalf_and_rbac(db):
    from porterchain_api.db import get_db
    from porterchain_api.main import app
    b, r = _batch(db)
    app.dependency_overrides[get_db] = lambda: db
    key = _admin(app)
    try:
        c = TestClient(app)
        res = c.post(f"/v1/admin/jobs/batches/{b.id}/instructions",
                     json={"text": "Partner: use rear door", "as_partner_id": "pt-9", "steps": ["pickup"]})
        assert res.status_code == 200, res.text
        iid = res.json()["id"]
        items = c.get(f"/v1/admin/jobs/batches/{b.id}/instructions").json()["items"]
        assert items[0]["author_role"] == "partner" and items[0]["author_id"] == "pt-9"
        assert c.patch(f"/v1/admin/jobs/instructions/{iid}", json={"priority": "must_read"}).json()["version"] == 2
        assert len(c.get(f"/v1/admin/jobs/instructions/{iid}/history").json()["items"]) == 2
        assert c.get(f"/v1/admin/jobs/batches/{b.id}/pickup-docs").json() == {"documents": []}
        _admin(app, "marketing")
        assert c.get(f"/v1/admin/jobs/batches/{b.id}/instructions").status_code == 403
    finally:
        app.dependency_overrides.pop(key, None)
        app.dependency_overrides.pop(get_db, None)


def test_driver_endpoints_checklist_capture_ack(db, monkeypatch):
    from types import SimpleNamespace

    from porterchain_api.db import get_db
    from porterchain_api.driver_engine.rbac import DriverContext
    from porterchain_api.main import app
    from porterchain_api.routers.driver._deps import get_driver_context
    monkeypatch.setattr(svc, "_batch_docs", lambda *_a, **_k: ["bol", "signed_handover"])
    b, r = _batch(db)
    i = JD.add_instruction(db, "merchant", "m", {"text": "Ask for Joe", "priority": "must_read", "steps": ["pickup"]},
                           route_id=b.id)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_driver_context] = lambda: DriverContext(driver=SimpleNamespace(id="drv"))
    try:
        c = TestClient(app)
        app.dependency_overrides[get_driver_context] = lambda: DriverContext(driver=SimpleNamespace(id="other"))
        assert c.get(f"/driver-api/v1/doc-checklist/routes/{r.id}").status_code in (403, 404)
        app.dependency_overrides[get_driver_context] = lambda: DriverContext(driver=SimpleNamespace(id="drv"))
        base = f"/driver-api/v1/doc-checklist/routes/{r.id}"
        assert c.get(base).json()["blockers"] == ["bol", "signed_handover"]
        from porterchain_api.media_store.service import _key
        doc, sig = _key("photo", "drv", "jpg"), _key("signature", "drv", "png")
        assert c.post(f"{base}/bol", json=SIG).status_code == 409  # not keys uploaded via /media/*
        stolen = {**SIG, "media_key": _key("photo", "other", "jpg"), "shipper_signature_key": sig}
        assert c.post(f"{base}/bol", json=stolen).status_code == 403  # another driver's upload
        res = c.post(f"{base}/bol", json={**SIG, "media_key": doc, "shipper_signature_key": sig})
        assert res.json().get("blockers") == ["signed_handover"], res.text
        assert c.post(f"{base}/signed_handover/missing", json={"reason": "no signer"}).json()["blocking"] is True
        got = c.get(f"/driver-api/v1/instructions/routes/{r.id}", params={"step": "pickup"}).json()
        assert got["must_ack"] == [i.id]
        assert c.post(f"/driver-api/v1/instructions/{i.id}/ack").json() == {"ok": True}
        assert c.get(f"/driver-api/v1/instructions/routes/{r.id}", params={"step": "pickup"}).json()["must_ack"] == []
        # (last: a rejected capture rolls back the test transaction)
        assert c.post(f"{base}/bol", json={"media_key": doc}).json()["detail"] == "shipper_name_required"
    finally:
        app.dependency_overrides.pop(get_driver_context, None)
        app.dependency_overrides.pop(get_db, None)

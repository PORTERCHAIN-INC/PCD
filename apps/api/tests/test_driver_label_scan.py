"""Signed PC1 labels + scan-anytime lookup security (Oct 2026)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from porterchain_api.reporting.qr_codec import (
    InvalidLabelQr,
    decode_signed_label,
    encode_signed_label,
    is_signed_label,
)
from porterchain_api.driver_engine import scan_service
from porterchain_api.routers.driver import scan as scan_router

KEY = b"k" * 32


def test_pc1_round_trip_and_opaque():
    pid = str(uuid.uuid4())
    code = encode_signed_label(pid, key=KEY)
    assert is_signed_label(code) and code.startswith("PC1.")
    assert decode_signed_label(code, key=KEY) == pid
    assert decode_signed_label(code.lower(), key=KEY) == pid  # camera case-insensitive
    assert "|" not in code  # no order id / COD / route payload


def test_pc1_forged_or_tampered_rejected():
    pid = str(uuid.uuid4())
    code = encode_signed_label(pid, key=KEY)
    other = str(uuid.uuid4()).replace("-", "").upper()
    with pytest.raises(InvalidLabelQr):
        decode_signed_label(f"PC1.{other}.{code.split('.')[2]}", key=KEY)
    with pytest.raises(InvalidLabelQr):
        decode_signed_label(code, key=b"x" * 32)
    with pytest.raises(InvalidLabelQr):
        decode_signed_label("PC1.garbage", key=KEY)


def _ctx(driver_id="d1"):
    return SimpleNamespace(driver=SimpleNamespace(id=driver_id, status="approved", verification_status="approved"))


@pytest.fixture
def patched(monkeypatch):
    logged: list[dict] = []
    monkeypatch.setattr(scan_router, "require_approved_driver", lambda ctx: None)
    monkeypatch.setattr(scan_router.scan_audit, "enforce_scan_rate", lambda d: None)
    monkeypatch.setattr(scan_service.scan_audit, "log_scan", lambda db, **kw: logged.append(kw))
    return logged


def _db(pkg, order):
    db = MagicMock()
    db.get = MagicMock(side_effect=lambda model, _id: pkg if model.__name__ == "Package" else order)
    return db


def test_lookup_not_yours_reveals_nothing(patched, monkeypatch):
    pid = str(uuid.uuid4())
    pkg = SimpleNamespace(id=pid, order_id="o1", status="manifested")
    order = SimpleNamespace(id="o1", assigned_driver_id="someone-else", state="ASSIGNED")
    monkeypatch.setattr(scan_service, "_resolve", lambda db, code: pkg)
    with pytest.raises(HTTPException) as e:
        scan_router.scan_lookup(_ctx(), {"code": "x", "lat": 43.5, "lng": -79.8}, _db(pkg, order))
    assert e.value.status_code == 404 and e.value.detail == {"code": "not_yours"}
    assert patched[-1]["result"] == "not_yours" and patched[-1].get("order_id") is None


def test_lookup_unknown_code_same_404(patched, monkeypatch):
    monkeypatch.setattr(scan_service, "_resolve", lambda db, code: None)
    with pytest.raises(HTTPException) as e:
        scan_router.scan_lookup(_ctx(), {"code": "nope"}, MagicMock())
    assert e.value.detail == {"code": "not_yours"}


def test_lookup_finished_order_is_not_yours(patched, monkeypatch):
    pkg = SimpleNamespace(id="p", order_id="o1", status="delivered")
    order = SimpleNamespace(id="o1", assigned_driver_id="d1", state="DELIVERED")
    monkeypatch.setattr(scan_service, "_resolve", lambda db, code: pkg)
    with pytest.raises(HTTPException):
        scan_router.scan_lookup(_ctx(), {"code": "x"}, _db(pkg, order))


def test_lookup_own_parcel_and_wrong_stop(patched, monkeypatch):
    pkg = SimpleNamespace(id="p", order_id="o1", status="picked_up", tracking_suffix="T-1",
                          item_label="Sofa", box_index=1, box_count=3, parcel_index=1,
                          total_parcels=3, stop_sequence=2)
    order = SimpleNamespace(id="o1", order_number="PC-1", assigned_driver_id="d1", state="PICKED_UP")
    monkeypatch.setattr(scan_service, "_resolve", lambda db, code: pkg)
    out = scan_router.scan_lookup(_ctx(), {"code": "x", "expected_order_id": "o2"}, _db(pkg, order))
    assert out["warning"] == "wrong_stop"
    assert out["next_phase"] == "delivery" and "scan_delivery" in out["allowed_actions"]
    assert "phone" not in str(out) and "address" not in str(out)
    assert patched[-1]["result"] == "wrong_stop"

"""Merchant pickup/delivered emails: driver's name only, addresses, portal link; scan repeats flagged."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from porterchain_api.merchant_engine.scan_gate_service import ScanGateService
from porterchain_api.notification_engine.templates import render_email

BASE = {
    "audience": "business",
    "recipient_role": "merchant",
    "merchant_id": "m1",
    "order_number": "ORD-1",
    "tracking_number": "PC-1",
    "driver_name": "Zed Testdriver",
    "pickup_address": "25 Peel Centre Dr, Brampton, ON",
    "dropoff_address": "2 Wellington St W, Brampton, ON",
    "merchant_order_url": "https://merchant.porterchain.com/orders/o1",
    "public_track_url": "https://porterchain.com/track/PC-1",
    # Never rendered even if present in the context.
    "driver_phone": "+14165550199",
    "driver_email": "driver@example.com",
}


def test_pickup_email_names_driver_and_links_portal():
    subject, text, html = render_email("parcel_picked_up", dict(BASE))
    assert subject == "Picked up · PC-1"
    assert "Zed Testdriver picked up order ORD-1" in text
    assert "https://merchant.porterchain.com/orders/o1" in html
    assert "2 Wellington St W" in html
    for leak in ("4165550199", "driver@example.com"):
        assert leak not in text and leak not in html


def test_delivered_email_points_to_proof_in_portal():
    subject, text, html = render_email("delivered", dict(BASE))
    assert subject == "Delivered · PC-1"
    assert "View proof of delivery" in html
    assert "Zed Testdriver delivered order ORD-1" in text
    assert "4165550199" not in html


def test_delivered_without_driver_still_reads_well():
    ctx = {k: v for k, v in BASE.items() if k != "driver_name"}
    _subject, text, _html = render_email("delivered", ctx)
    assert "Order ORD-1 was delivered." in text


def test_driver_copy_is_not_the_merchant_layout():
    ctx = dict(BASE, recipient_role="driver")
    subject, _text, _html = render_email("delivered", ctx)
    assert subject == "Delivered"


def test_admin_copy_override_still_wins():
    ctx = dict(BASE, copy_subject="Custom {tracking_number}")
    subject, _text, _html = render_email("parcel_picked_up", ctx)
    assert subject == "Custom PC-1"


def _scan(status: str, phase: str) -> dict:
    gate = ScanGateService()
    pkg = SimpleNamespace(id="p1", tracking_suffix="PC-1-01", status=status, order_id="o1")
    gate._package_for_scan = lambda _db, _o, _qr: pkg  # type: ignore[method-assign]
    gate.scan_progress = lambda _db, _o, phase: {"scanned": 1, "required": 1}  # type: ignore[method-assign]
    return gate.scan_qr(MagicMock(), SimpleNamespace(id="o1"), "PC-1-01", phase=phase)  # type: ignore[arg-type]


def test_first_pickup_scan_is_not_duplicate():
    assert _scan("manifested", "pickup")["duplicate"] is False


def test_repeat_pickup_scan_is_flagged():
    out = _scan("picked_up", "pickup")
    assert out["duplicate"] is True and out["status"] == "picked_up"


def test_repeat_delivery_scan_is_flagged():
    assert _scan("delivered", "delivery")["duplicate"] is True
    assert _scan("picked_up", "delivery")["duplicate"] is False

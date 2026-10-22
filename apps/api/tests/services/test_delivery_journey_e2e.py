"""End to end: pickup → Start delivery → "on the way" email/SMS with tracking link →
live driver dot on the tracking page (only with GPS consent + on duty) → arriving soon → delivered.

Driven through the real driver StopsService and the real customer-experience event hook.
No message leaves the box: senders are tripwires; assertions are on queued NotificationRecords.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

import porterchain_api.main  # noqa: F401
from porterchain_api.booking_engine.public_tracking_snapshot import build_public_live_tracking
from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.booking_models import Order
from porterchain_api.customer_experience.events import process_order_event
from porterchain_api.driver_models import DriverShift
from porterchain_api.platform.gps_policy import CONSENT_VERSION
from porterchain_driver.stops import StopsService
from tests.services.test_customer_experience_phase_b import _all_on, _order, _records, _set_cx, no_real_sends  # noqa: F401


def _live(lat: float = 43.6471234, lng: float = -79.3801234) -> dict:
    return {"location": {"lat": lat, "lng": lng}, "coordinates": {"lat": lat, "lng": lng},
            "recorded_at": datetime.now(UTC).isoformat(), "source": "last_known"}


def _tracking(db, order) -> dict:
    maps = MagicMock()
    maps.eta_between.return_value = None
    maps.optimized_route.return_value = None
    return build_public_live_tracking(
        order, _live(), maps=maps, gps_allowed=lambda: TrackingService._driver_gps_allowed(db, order)
    )


@pytest.fixture
def relaxed_gates(monkeypatch):
    # Scan gate / paperwork / POD photo are covered by their own suites.
    from porterchain_driver import stops as stops_mod

    monkeypatch.setattr(stops_mod, "_assert_dropoff_pod_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_complete", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "porterchain_api.booking_attachments.service.assert_pickup_documents_shown", lambda *_a, **_k: None
    )


def test_pickup_to_delivered_with_live_tracking(db, merchant_ctx, settings, driver, relaxed_gates) -> None:
    _set_cx(db, merchant_ctx.merchant, _all_on())
    driver.documents = {**(driver.documents or {}),
                        "gps_consent": {"version": CONSENT_VERSION, "accepted": True}}
    shift = DriverShift(driver_id=driver.id, status="active")
    db.add(shift)
    db.commit()
    order = _order(db, merchant_ctx, state="DRIVER_ASSIGNED", driver_id=driver.id, email="rcv@example.test")
    stops = StopsService()

    # 1) Pickup done → the driver app's next action is "Start delivery".
    stops.arrive_stop(db, driver, f"{order.id}-pickup", skip_presence=True)
    view = stops.deliver_stop(db, driver, f"{order.id}-pickup", enforce_sequence=False)
    db.commit()
    assert db.get(Order, order.id).state == "PICKED_UP" and view.stop_type == "pickup"
    assert _tracking(db, db.get(Order, order.id))["driver_location"] is not None  # active state

    # 2) Start delivery → IN_TRANSIT → "out for delivery" email + SMS with the tracking link.
    stops.start_delivery(db, driver, f"{order.id}-dropoff")
    db.commit()
    order = db.get(Order, order.id)
    assert order.state == "IN_TRANSIT"
    process_order_event(db, settings, "order.in_transit", {"order_id": order.id})
    out = [r for r in _records(db, order) if r.template_key == "cx_out_for_delivery"]
    assert {r.channel for r in out} == {"email", "sms"}
    assert all(f"/track/{order.tracking_number}" in (r.deep_link or "") for r in out)
    assert f"/track/{order.tracking_number}" in next(r for r in out if r.channel == "email").body

    # 3) Tracking page: live (coarse) dot only with consent and while on duty.
    loc = _tracking(db, order)["driver_location"]
    assert loc == {"lat": 43.647, "lng": -79.38, "recorded_at": loc["recorded_at"]}
    shift.status = "on_break"
    db.commit()
    assert _tracking(db, order)["driver_location"] is None
    shift.status = "active"
    driver.documents = {"gps_consent_history": [{"accepted": False}]}  # consent withdrawn
    db.commit()
    assert _tracking(db, order)["driver_location"] is None
    driver.documents = {"gps_consent": {"version": CONSENT_VERSION, "accepted": True}}
    db.commit()
    assert _tracking(db, order)["driver_location"] is not None

    # 4) Arriving soon (ETA under the merchant threshold).
    process_order_event(db, settings, "order.tracking_updated", {"order_id": order.id, "eta_seconds": 300})
    soon = [r for r in _records(db, order) if r.template_key == "cx_eta_20"]
    assert soon and "5" in soon[0].body

    # 5) Delivered: notification, and the dot disappears.
    stops.arrive_stop(db, driver, f"{order.id}-dropoff", skip_presence=True)
    stops.deliver_stop(db, driver, f"{order.id}-dropoff", enforce_sequence=False)
    db.commit()
    order = db.get(Order, order.id)
    assert order.state in {"DELIVERED", "POD_COMPLETED"}
    process_order_event(db, settings, "order.delivered", {"order_id": order.id})
    assert [r for r in _records(db, order) if r.template_key == "cx_delivered"]
    assert _tracking(db, order)["driver_location"] is None

"""Live map — real Postgres + live Valhalla/OSRM (P0-6).

Snapshot tests commit into the shared local DB (same as other API integration
tests). Orders use an early scheduled_at so they land inside snapshot's
ACTIVE_LIMIT window even when the DB already has many in-flight rows. Rows are
always deleted in finally.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.live_map_service import (
    LiveMapService,
    order_stop_points,
)
from porterchain_api.admin_models import Driver
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.dispatch_engine import ops_mirror
from porterchain_api.booking_models import Order
from porterchain_services.maps.service import MapsService

# Guarantees the fixture sits inside snapshot()'s order_by(scheduled_at).limit(200).
_EARLY = datetime(2000, 1, 1, tzinfo=UTC)


def _order(state: OrderState = OrderState.IN_TRANSIT, **overrides) -> Order:
    addr = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
    dest = {"formatted": "10 Yonge St, Toronto", "lat": 43.6426, "lng": -79.3744}
    defaults = dict(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        amount_cents=3200,
        currency="cad",
        pickup=addr,
        dropoff=dest,
        scheduled_at=_EARLY,
        created_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return Order(**defaults)


def _cleanup(db: Session, *rows) -> None:
    for row in rows:
        if row is None:
            continue
        obj = db.get(type(row), row.id)
        if obj is not None:
            db.delete(obj)
    db.commit()


def _valhalla_reachable(maps: MapsService) -> str | None:
    """Return skip reason, or None if Valhalla answers /route."""
    url = (maps.settings.valhalla_url or "").rstrip("/")
    if not url:
        return "VALHALLA_BASE_URL / valhalla_url not configured"
    try:
        with httpx.Client(timeout=8.0) as client:
            status = client.get(f"{url}/status")
            if status.status_code >= 400:
                return f"Valhalla /status HTTP {status.status_code}"
            probe = maps.route_multi([(43.6488, -79.3817), (43.6426, -79.3744)])
    except Exception as exc:  # noqa: BLE001 — network probe
        return f"Valhalla unreachable: {exc}"
    if not probe:
        return "Valhalla /route returned no trip"
    return None


def _osrm_reachable(maps: MapsService) -> str | None:
    url = (maps.settings.osrm_url or "").rstrip("/")
    if not url:
        return "OSRM_HOST / osrm_url not configured"
    # Always probe the OSRM host directly — MapsService may prefer Valhalla first.
    try:
        with httpx.Client(timeout=8.0) as client:
            r = client.get(
                f"{url}/route/v1/driving/-79.3817,43.6488;-79.3744,43.6426",
                params={"overview": "false"},
            )
        if r.status_code >= 400:
            return f"OSRM HTTP {r.status_code}"
        if r.json().get("code") != "Ok":
            return f"OSRM code={r.json().get('code')}"
    except Exception as exc:  # noqa: BLE001
        return f"OSRM unreachable: {exc}"
    return None


class TestStopExtraction:
    def test_legacy_pickup_dropoff(self):
        stops = order_stop_points(_order())
        assert [s["kind"] for s in stops] == ["pickup", "dropoff"]
        assert stops[0]["label"] == "1 King St W, Toronto"

    def test_rich_stops_sorted_by_sequence(self):
        meta = {
            "stops": [
                {"type": "dropoff", "sequence": 2, "lat": 43.7, "lng": -79.4, "address": "B St"},
                {"type": "pickup", "sequence": 1, "lat": 43.6, "lng": -79.3, "address": "A St"},
            ]
        }
        stops = order_stop_points(_order(compliance_metadata=meta))
        assert [s["kind"] for s in stops] == ["pickup", "dropoff"]
        assert stops[0]["label"] == "A St"

    def test_legacy_additional_stops_in_middle(self):
        meta = {"additional_stops": [{"address": "Mid", "lat": 43.66, "lng": -79.38}]}
        stops = order_stop_points(_order(compliance_metadata=meta))
        assert [s["kind"] for s in stops] == ["pickup", "stop", "dropoff"]

    def test_stops_without_coords_are_skipped(self):
        meta = {"stops": [{"type": "pickup", "sequence": 1, "address": "No coords"}]}
        stops = order_stop_points(_order(compliance_metadata=meta))
        assert [s["kind"] for s in stops] == ["pickup", "dropoff"]


class TestSnapshot:
    def test_on_duty_driver_without_fleetbase_id(self, db: Session):
        from porterchain_api.driver_engine.last_known import LastKnown
        from porterchain_api.driver_models import DriverShift

        driver = Driver(
            id=str(uuid4()),
            status="APPROVED",
            email=f"{uuid4()}@test.dev",
            full_name="Ada Driver",
            fleetbase_driver_id=None,
            is_online=True,
        )
        shift = DriverShift(
            id=str(uuid4()),
            driver_id=driver.id,
            status="active",
            started_at=datetime.now(UTC),
        )
        order = _order(assigned_driver_id=driver.id)
        db.add_all([driver, shift, order])
        db.commit()
        known = LastKnown(
            driver_id=driver.id,
            lat=43.65,
            lng=-79.38,
            recorded_at=datetime.now(UTC),
        )
        pin = {
            "id": driver.id,
            "fleetbase_driver_id": "",
            "name": driver.full_name,
            "lat": 43.65,
            "lng": -79.38,
            "online": True,
            "on_break": False,
            "gps_source": "last_known",
            "recorded_at": known.recorded_at.isoformat(),
            "accuracy_m": None,
            "heading": None,
            "h3": None,
        }
        try:
            with (
                patch(
                    "porterchain_api.admin_engine.live_map_service.ops_mirror.read_zones",
                    return_value=([], ops_mirror.SOURCE_MISS),
                ),
                patch(
                    "porterchain_api.admin_engine.live_map_service.gps_board.board_pins",
                    return_value=([pin], "last_known"),
                ),
            ):
                snap = LiveMapService().snapshot(db)

            assert snap["drivers_source"] == "last_known"
            match = [d for d in snap["drivers"] if d["id"] == driver.id]
            assert match and match[0]["name"] == "Ada Driver"
            assert match[0]["online"] is True
            assert match[0]["fleetbase_driver_id"] == ""

            tracked = [o for o in snap["orders"] if o["id"] == order.id]
            assert tracked, "fixture order missing from snapshot (ACTIVE_LIMIT / scheduled_at)"
            assert tracked[0]["driver"] == "Ada Driver"
            assert len(tracked[0]["stops"]) == 2
        finally:
            _cleanup(db, order, shift, driver)

    def test_no_shift_returns_orders_only(self, db: Session):
        order = _order()
        db.add(order)
        db.commit()
        try:
            with patch(
                "porterchain_api.admin_engine.live_map_service.ops_mirror.read_zones",
                return_value=([], ops_mirror.SOURCE_UNAVAILABLE),
            ):
                snap = LiveMapService().snapshot(db)
            assert snap["drivers"] == []
            assert snap["drivers_source"] == "miss"
            assert any(o["id"] == order.id for o in snap["orders"])
        finally:
            _cleanup(db, order)

    def test_last_known_pin_for_on_duty_driver(self, db: Session):
        from porterchain_api.driver_engine.last_known import LastKnown
        from porterchain_api.driver_models import DriverShift

        driver = Driver(
            id=str(uuid4()),
            status="APPROVED",
            email=f"{uuid4()}@test.dev",
            full_name="Last Known",
            fleetbase_driver_id=None,
            is_online=True,
        )
        shift = DriverShift(
            id=str(uuid4()),
            driver_id=driver.id,
            status="active",
            started_at=datetime.now(UTC),
        )
        db.add_all([driver, shift])
        db.commit()
        known = LastKnown(
            driver_id=driver.id,
            lat=43.65,
            lng=-79.38,
            recorded_at=datetime.now(UTC),
        )
        pin = {
            "id": driver.id,
            "fleetbase_driver_id": "",
            "name": driver.full_name,
            "lat": 43.65,
            "lng": -79.38,
            "online": True,
            "on_break": False,
            "gps_source": "last_known",
            "recorded_at": known.recorded_at.isoformat(),
            "accuracy_m": None,
            "heading": None,
            "h3": None,
        }
        try:
            with (
                patch(
                    "porterchain_api.admin_engine.live_map_service.ops_mirror.read_zones",
                    return_value=([], ops_mirror.SOURCE_MISS),
                ),
                patch(
                    "porterchain_api.admin_engine.live_map_service.gps_board.board_pins",
                    return_value=([pin], "last_known"),
                ),
            ):
                snap = LiveMapService().snapshot(db)
            assert snap["drivers_source"] == "last_known"
            match = [d for d in snap["drivers"] if d["id"] == driver.id]
            assert match and match[0]["lat"] == 43.65
            assert match[0]["gps_source"] == "last_known"
            assert match[0]["recorded_at"]
        finally:
            _cleanup(db, shift, driver)


class TestRouteGeometry:
    def test_live_valhalla_route_geometry(self, db: Session):
        maps = MapsService()
        reason = _valhalla_reachable(maps)
        if reason:
            pytest.skip(reason)

        order = _order()
        db.add(order)
        db.commit()
        try:
            geo = LiveMapService(adapter=None, maps=maps).route_geometry(db, order.id)
            assert geo["source"] == "valhalla"
            assert geo["distance_meters"] is not None and geo["distance_meters"] > 0
            assert geo["duration_seconds"] is not None and geo["duration_seconds"] > 0
            assert len(geo["path"]) >= 2
            # Path should stay near downtown Toronto (±~0.05°)
            assert abs(geo["path"][0][0] - 43.6488) < 0.05
            assert abs(geo["path"][0][1] - (-79.3817)) < 0.05
        finally:
            _cleanup(db, order)

    def test_live_osrm_route_reachable(self):
        """OSRM is the MapsService distance/ETA fallback — prove the configured host works."""
        maps = MapsService()
        reason = _osrm_reachable(maps)
        if reason:
            pytest.skip(reason)
        with httpx.Client(timeout=10.0) as client:
            url = maps.settings.osrm_url.rstrip("/")
            r = client.get(
                f"{url}/route/v1/driving/-79.3817,43.6488;-79.3744,43.6426",
                params={"overview": "false"},
            )
        body = r.json()
        assert r.status_code == 200
        assert body.get("code") == "Ok"
        assert body["routes"][0]["distance"] > 0

    def test_direct_fallback_when_routing_unavailable(self, db: Session):
        order = _order()
        db.add(order)
        db.commit()

        class _DownMaps:
            def route_multi(self, points):
                return None

        try:
            geo = LiveMapService(adapter=None, maps=_DownMaps()).route_geometry(db, order.id)
            assert geo["source"] == "direct"
            assert geo["path"] == [[43.6488, -79.3817], [43.6426, -79.3744]]
        finally:
            _cleanup(db, order)

    def test_unknown_order_raises(self, db: Session):
        class _DownMaps:
            def route_multi(self, points):
                return None

        with pytest.raises(LookupError):
            LiveMapService(adapter=None, maps=_DownMaps()).route_geometry(db, str(uuid4()))

"""Live map service — stop extraction, adapter-fed drivers, route geometry (P0-6)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.live_map_service import (
    LiveMapService,
    order_stop_points,
)
from porterchain_api.admin_models import Driver
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order
from porterchain_services.maps.polyline import encode_polyline


def _order(state: OrderState = OrderState.IN_TRANSIT, **overrides) -> Order:
    addr = {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}
    dest = {"formatted": "10 Yonge St, Toronto", "lat": 43.6426, "lng": -79.3744}
    return Order(
        id=str(uuid4()),
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state.value,
        amount_cents=3200,
        currency="cad",
        pickup=addr,
        dropoff=dest,
        scheduled_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        **overrides,
    )


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
        # Falls back to legacy pickup/dropoff which have coords
        assert [s["kind"] for s in stops] == ["pickup", "dropoff"]


class _FakeAdapter:
    is_enabled = True

    def __init__(self, drivers):
        self._drivers = drivers

    def list_drivers(self, *, limit: int = 200):
        return self._drivers


class TestSnapshot:
    def test_driver_positions_matched_to_pc_drivers(self, db: Session):
        driver = Driver(
            id=str(uuid4()),
            status="APPROVED",
            email=f"{uuid4()}@test.dev",
            full_name="Ada Driver",
            fleetbase_driver_id="fb-1",
            is_online=True,
        )
        order = _order(assigned_driver_id=driver.id)
        db.add_all([driver, order])
        db.commit()

        adapter = _FakeAdapter(
            [{"id": "fb-1", "online": True, "location": {"lat": 43.65, "lng": -79.38}}]
        )
        svc = LiveMapService(adapter=adapter)
        snap = svc.snapshot(db)

        assert snap["drivers_source"] == "fleetbase"
        match = [d for d in snap["drivers"] if d["fleetbase_driver_id"] == "fb-1"]
        assert match and match[0]["name"] == "Ada Driver"
        assert match[0]["online"] is True

        tracked = [o for o in snap["orders"] if o["id"] == order.id]
        assert tracked and tracked[0]["driver"] == "Ada Driver"
        assert len(tracked[0]["stops"]) == 2

    def test_adapter_down_returns_orders_only(self, db: Session):
        order = _order()
        db.add(order)
        db.commit()

        class _Down:
            is_enabled = True

            def list_drivers(self, *, limit: int = 200):
                raise RuntimeError("fleetbase unreachable")

        svc = LiveMapService(adapter=_Down())
        snap = svc.snapshot(db)

        assert snap["drivers"] == []
        assert snap["drivers_source"] == "unavailable"
        assert any(o["id"] == order.id for o in snap["orders"])


class _FakeMaps:
    def __init__(self, response):
        self._response = response

    def route_multi(self, points):
        return self._response


class TestRouteGeometry:
    def test_valhalla_shape_decoded_to_path(self, db: Session):
        order = _order()
        db.add(order)
        db.commit()

        coords = [(43.6488, -79.3817), (43.6460, -79.3780), (43.6426, -79.3744)]
        shape = encode_polyline(coords, precision=6)
        response = {
            "trip": {
                "legs": [{"shape": shape}],
                "summary": {"length": 2.4, "time": 420},
            }
        }
        svc = LiveMapService(adapter=None, maps=_FakeMaps(response))
        geo = svc.route_geometry(db, order.id)

        assert geo["source"] == "valhalla"
        assert geo["distance_meters"] == 2400
        assert geo["duration_seconds"] == 420
        assert len(geo["path"]) == 3
        assert abs(geo["path"][0][0] - 43.6488) < 1e-5

    def test_direct_fallback_when_routing_unavailable(self, db: Session):
        order = _order()
        db.add(order)
        db.commit()

        svc = LiveMapService(adapter=None, maps=_FakeMaps(None))
        geo = svc.route_geometry(db, order.id)

        assert geo["source"] == "direct"
        assert geo["path"] == [[43.6488, -79.3817], [43.6426, -79.3744]]

    def test_unknown_order_raises(self, db: Session):
        svc = LiveMapService(adapter=None, maps=_FakeMaps(None))
        try:
            svc.route_geometry(db, str(uuid4()))
            assert False, "expected LookupError"
        except LookupError:
            pass

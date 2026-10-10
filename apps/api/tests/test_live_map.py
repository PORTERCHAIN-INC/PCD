"""Live map — real Postgres + live Valhalla/OSRM (P0-6).

Snapshot tests commit into the shared local DB (same as other API integration
tests). Orders use an early scheduled_at so they land inside snapshot's
ACTIVE_LIMIT window even when the DB already has many in-flight rows. Rows are
always deleted in finally.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from porterchain_services.maps.service import MapsService
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.live_map_service import (
    LiveMapService,
    order_stop_points,
)
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.domain.states import OrderState

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
    db.rollback()
    ids = [getattr(row, "id", None) for row in rows if row is not None]
    from porterchain_api.driver_models import DriverShift

    if ids:
        db.query(DriverShift).filter(DriverShift.driver_id.in_([i for i in ids if i])).delete(
            synchronize_session=False
        )
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

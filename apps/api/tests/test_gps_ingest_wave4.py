"""Wave 4 — H3 density, AABB-equivalent zones, Valhalla next-stop / import."""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.live_map_service import _density_cells
from porterchain_api.merchant_engine.import_route_optimize import optimize_drop_order_with_source
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.route_optimizer import DriverRouteOptimizer
from porterchain_pricing.gta_rate import calculate_gta_delivery_rate, is_downtown_point, is_upper_zone_point
from porterchain_pricing.types import GeoPoint
from porterchain_pricing.zone import DEFAULT_ZONES, ZoneService
from porterchain_services.maps.service import MapsService


class TestH3Density:
    def test_same_hex_aggregates_weight_and_uses_cell_center(self):
        pytest.importorskip("h3")
        orders = [
            {
                "stops": [
                    {"lat": 43.65, "lng": -79.38},
                    {"lat": 43.65, "lng": -79.38},
                ]
            },
            {"stops": [{"lat": 43.889, "lng": -79.263}]},
        ]
        cells, source = _density_cells(orders)
        assert source in {"h3", "grid"}
        assert cells
        assert all({"lat", "lng", "weight"} <= set(c) for c in cells)
        assert any(c["weight"] == 2 for c in cells)
        downtown = next(c for c in cells if c["weight"] == 2)
        assert abs(downtown["lat"] - 43.65) < 0.05
        assert abs(downtown["lng"] - (-79.38)) < 0.05


class TestZoneAabbParity:
    def test_polygons_match_historic_aabb(self):
        historic = [
            ("gta_core", {"min_lat": 43.58, "max_lat": 43.78, "min_lng": -79.55, "max_lng": -79.25}),
            ("gta_outer", {"min_lat": 43.45, "max_lat": 43.90, "min_lng": -79.75, "max_lng": -79.05}),
            ("ontario_extended", {"min_lat": 42.0, "max_lat": 45.5, "min_lng": -81.0, "max_lng": -78.0}),
        ]

        def old_code(lat: float, lng: float) -> str:
            for code, b in historic:
                if b["min_lat"] <= lat <= b["max_lat"] and b["min_lng"] <= lng <= b["max_lng"]:
                    return code
            return "ontario_extended"

        svc = ZoneService()
        assert all(z.polygon for z in DEFAULT_ZONES)
        samples = [
            (43.65, -79.38),
            (43.58, -79.55),
            (43.78, -79.25),
            (43.45, -79.75),
            (43.90, -79.05),
            (42.0, -81.0),
            (44.0, -79.4),
            (43.0, -80.0),
        ]
        for lat, lng in samples:
            got = svc.resolve_zone(GeoPoint(lat=lat, lng=lng))
            assert got is not None
            assert got.code == old_code(lat, lng)

    def test_gta_cad_boxes_unchanged(self):
        assert is_downtown_point(GeoPoint(lat=43.65, lng=-79.38)) is True
        assert is_downtown_point(GeoPoint(lat=43.68, lng=-79.38)) is False
        assert is_upper_zone_point(GeoPoint(lat=43.85, lng=-79.30)) is True
        result = calculate_gta_delivery_rate(
            vehicle_type="suv", total_km=10, is_downtown=True, is_upper_zone=True
        )
        assert result.total_cad == 95.0
        assert "isochrone" not in inspect.getsource(is_downtown_point)
        assert "isochrone" not in inspect.getsource(is_upper_zone_point)


class TestNextStopMatrix:
    def test_matrix_picks_road_nearest_and_uses_real_eta(self):
        near = SimpleNamespace(
            stop_id="s-near",
            stop_type="dropoff",
            order_id="o-near",
            order_number="N1",
            tracking_number="T1",
            sequence=2,
            address={"lat": 43.70, "lng": -79.40},
            status="pending",
        )
        far = SimpleNamespace(
            stop_id="s-far",
            stop_type="dropoff",
            order_id="o-far",
            order_number="N2",
            tracking_number="T2",
            sequence=1,
            address={"lat": 43.66, "lng": -79.39},
            status="pending",
        )
        maps = MagicMock()
        # Road says `near` (second target, seq 2) is faster than closer-by-crow `far`.
        maps.matrix_durations.return_value = ([[(900, 9000), (120, 800)]], "valhalla")
        resolver = NextStopResolver(maps=maps)
        route = SimpleNamespace(stops=[far, near])
        driver = SimpleNamespace(id="drv-1")
        db = MagicMock()
        with (
            patch("porterchain_driver.stops.StopsService.assigned_route", return_value=route),
            patch(
                "porterchain_api.driver_engine.last_known.read_last_known",
                return_value=SimpleNamespace(lat=43.65, lng=-79.38),
            ),
        ):
            out = resolver.resolve(db, driver)
        assert out is not None
        assert out["stop_id"] == "s-near"
        assert out["source"] == "valhalla"
        assert out["eta_minutes"] == 2
        assert out["distance_m"] == 800

    def test_haversine_fallback_has_no_invented_eta(self):
        stop = SimpleNamespace(
            stop_id="s1",
            stop_type="pickup",
            order_id="o1",
            order_number="N",
            tracking_number="T",
            sequence=1,
            address={"lat": 43.66, "lng": -79.39},
            status="pending",
        )
        maps = MagicMock()
        maps.matrix_durations.return_value = ([], None)
        resolver = NextStopResolver(maps=maps)
        route = SimpleNamespace(stops=[stop])
        with (
            patch("porterchain_driver.stops.StopsService.assigned_route", return_value=route),
            patch(
                "porterchain_api.driver_engine.last_known.read_last_known",
                return_value=SimpleNamespace(lat=43.65, lng=-79.38),
            ),
        ):
            out = resolver.resolve(MagicMock(), SimpleNamespace(id="drv-1"))
        assert out is not None
        assert out["source"] == "haversine"
        assert out["eta_minutes"] is None
        assert out["distance_m"] is not None


class TestImportMatrix:
    def test_matrix_can_reorder_by_road_cost(self):
        stops = [
            {"sequence": 1, "stop_type": "pickup", "lat": 43.65, "lng": -79.38, "address": "P"},
            {"sequence": 2, "stop_type": "drop", "lat": 43.75, "lng": -79.50, "address": "Far"},
            {"sequence": 3, "stop_type": "drop", "lat": 43.651, "lng": -79.381, "address": "Near"},
        ]
        # points = [P, Far, Near]. Make Far cheaper from pickup than Near.
        maps = MagicMock()
        maps.matrix_durations.return_value = (
            [
                [(0, 0), (100, 100), (900, 900)],
                [(100, 100), (0, 0), (100, 100)],
                [(900, 900), (100, 100), (0, 0)],
            ],
            "osrm",
        )
        out, source = optimize_drop_order_with_source(stops, maps=maps)
        assert source == "osrm"
        assert out[1]["address"] == "Far"


class TestOptimizerMatrix:
    def test_optimizer_does_not_build_local_tsp(self):
        src = inspect.getsource(DriverRouteOptimizer)
        assert "_build_cost_matrix" not in src
        assert "_two_opt" not in src
        assert "_StopNode" not in src
        opt = DriverRouteOptimizer()
        assert opt.reoptimize_remaining(None, None, "x") is None
        pickup = SimpleNamespace(
            state="DRIVER_ASSIGNED",
            pickup={"lat": 43.65, "lng": -79.38},
            dropoff={"lat": 43.66, "lng": -79.39},
            amount_cents=1000,
            scheduled_at=None,
        )
        assert opt.can_optimize([pickup]) is True


class TestIsochroneHelper:
    def test_isochrone_exists_and_cad_does_not_call_it(self):
        assert callable(MapsService.isochrone)
        src = inspect.getsource(calculate_gta_delivery_rate)
        assert "isochrone" not in src

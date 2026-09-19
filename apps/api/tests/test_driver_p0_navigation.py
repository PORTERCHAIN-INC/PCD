"""P0 — navigation / maps / POD (API-D-05 / API-D-06 / MAP-*)."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.main import app
from porterchain_driver.navigation import NavigationService
from porterchain_driver.pod import ProofOfDeliveryService
from porterchain_services.maps.service import MapsService


@pytest.mark.driver_p0
def test_map_04_no_google_distance_matrix_in_driver_engine() -> None:
    """MAP-04 — Google Distance Matrix / Directions banned in driver_engine + admin ops."""
    roots = [
        Path(__file__).resolve().parents[1] / "src" / "porterchain_api" / "driver_engine",
        Path(__file__).resolve().parents[1] / "src" / "porterchain_api" / "admin_engine" / "control_tower",
    ]
    banned = ("distancematrix", "distance_matrix", "google.maps.DistanceMatrix", "directions/json")
    offenders: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for needle in banned:
                if needle.lower() in text:
                    offenders.append(f"{path}:{needle}")
    assert not offenders, f"Google routing banned in driver/CT paths: {offenders}"


@pytest.mark.driver_p0
def test_api_d_05_navigation_idle_session() -> None:
    """API-D-05 — idle navigation session pins Valhalla/OSRM/Fleetbase engine labels."""
    session = NavigationService().idle_session(SimpleNamespace(id="d1", availability="offline"))
    assert session["idle"] is True
    assert session["state"] == "idle"
    assert session["message"] == "no_active_job"
    engines = session["routing_engines"]
    assert engines["eta"] == "osrm"
    assert engines["optimized_route"] == "valhalla"
    assert engines["gps"] == "fleetbase"
    assert engines["map_display"] == "google_maps"
    assert "google" not in engines["eta"].lower()
    assert "google" not in engines["optimized_route"].lower()


@pytest.mark.driver_p0
def test_api_d_06_pod_otp_and_openapi() -> None:
    """API-D-06 — OTP verify contract + POD OpenAPI surface."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    assert ProofOfDeliveryService().verify_otp(db, "ord-missing", "123456") is False

    otp = "654321"
    meta = SimpleNamespace(meta={"delivery_otp_hash": hashlib.sha256(otp.encode()).hexdigest()})
    db.query.return_value.filter.return_value.first.return_value = meta
    assert ProofOfDeliveryService().verify_otp(db, "ord-1", otp) is True
    assert ProofOfDeliveryService().verify_otp(db, "ord-1", "000000") is False

    paths = set(app.openapi().get("paths", {}))
    required = {
        "/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-photo",
        "/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-signature",
        "/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-barcode",
        "/driver-api/v1/routes/{route_id}/stops/{stop_id}/pod-complete",
        "/driver-api/v1/orders/{order_id}/otp",
    }
    missing = sorted(p for p in required if p not in paths)
    assert not missing, f"missing POD OpenAPI paths: {missing}"


@pytest.mark.driver_p0
def test_map_01_valhalla_primary_osrm_fallback() -> None:
    """MAP-01 — MapsService.route_with_source Valhalla first, OSRM on miss."""
    svc = MapsService()
    svc.ctx = SimpleNamespace(
        settings=SimpleNamespace(
            routing_engine="valhalla",
            valhalla_url="http://valhalla.test",
            osrm_url="http://osrm.test",
            osrm_allow_public_demo=False,
        )
    )
    with (
        patch.object(svc, "_valhalla_route", return_value={"distance": 1000, "time": 120}),
        patch.object(svc, "_osrm_route", return_value=None) as osrm,
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert leg is not None
    assert source == "valhalla"
    osrm.assert_not_called()

    with (
        patch.object(svc, "_valhalla_route", return_value=None),
        patch.object(svc, "_osrm_route", return_value={"distance": 900, "time": 100}),
    ):
        leg, source = svc.route_with_source((43.65, -79.38), (43.66, -79.39))
    assert leg is not None
    assert source == "osrm"


@pytest.mark.driver_p0
def test_no_vroom_import_in_maps_service() -> None:
    """FB-04 companion — maps service must not import a VROOM client."""
    maps = (
        Path(__file__).resolve().parents[3]
        / "services"
        / "python"
        / "porterchain_services"
        / "maps"
        / "service.py"
    )
    assert maps.exists(), f"expected maps service at {maps}"
    tree = ast.parse(maps.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "vroom" not in alias.name.lower()
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "vroom" not in node.module.lower()

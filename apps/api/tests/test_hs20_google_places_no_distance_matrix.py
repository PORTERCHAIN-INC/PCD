"""HS-20 — Google Places for address autocomplete; no Distance Matrix for pricing."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MAPS_PKG = REPO_ROOT / "packages" / "maps" / "src"
ROUTING = REPO_ROOT / "apps" / "api" / "src" / "porterchain_api" / "services" / "routing.py"
BOOK_CLIENTS = (
    REPO_ROOT / "apps" / "customer" / "src" / "components" / "booking" / "CustomerBookDelivery.tsx",
    REPO_ROOT / "apps" / "merchant-portal" / "src" / "components" / "booking" / "BookDeliveryClient.tsx",
)


def test_hs20_places_autocomplete_in_maps_package() -> None:
    """Book UI address entry uses PlaceAutocompleteElement (Places), not Distance Matrix."""
    autocomplete = (MAPS_PKG / "AddressAutocompleteInput.tsx").read_text(encoding="utf-8")
    assert "PlaceAutocompleteElement" in autocomplete
    assert "useMapsLibrary(\"places\")" in autocomplete or "useMapsLibrary('places')" in autocomplete
    for needle in (
        "DistanceMatrix",
        "distancematrix",
        "DirectionsService",
        "maps/api/distancematrix",
    ):
        assert needle not in autocomplete


def test_hs20_book_ui_wires_address_autocomplete() -> None:
    for path in BOOK_CLIENTS:
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        assert "AddressAutocompleteInput" in text, path.name


def test_hs20_pricing_distance_delegates_to_maps_service() -> None:
    """Authoritative pricing distance is MapsService (Valhalla/OSRM), never Google DM."""
    text = ROUTING.read_text(encoding="utf-8")
    assert "MapsService" in text
    assert "route_distance_meters" in text
    for needle in ("distancematrix", "DistanceMatrix", "maps.googleapis.com"):
        assert needle not in text


def test_hs20_verify_no_ops_spatial_math_includes_google_dm_ban() -> None:
    script = REPO_ROOT / "scripts" / "verify_no_ops_spatial_math.py"
    src = script.read_text(encoding="utf-8")
    assert "distancematrix" in src.lower()
    assert "HS-20" in src or "Google Places" in src
    proc = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK:" in proc.stdout

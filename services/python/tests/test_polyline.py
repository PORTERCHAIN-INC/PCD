"""Tests for encoded polyline helpers."""

from __future__ import annotations

from porterchain_services.maps.polyline import (
    decode_polyline,
    encode_polyline,
    valhalla_shape_to_google_polyline,
)


def test_google_polyline_roundtrip() -> None:
    coords = [(43.6532, -79.3832), (43.6487, -79.3817)]
    encoded = encode_polyline(coords, precision=5)
    decoded = decode_polyline(encoded, precision=5)
    assert len(decoded) == 2
    assert abs(decoded[0][0] - coords[0][0]) < 1e-4
    assert abs(decoded[0][1] - coords[0][1]) < 1e-4


def test_valhalla_shape_converts_to_google_encoding() -> None:
    coords = [(43.6532, -79.3832), (43.6487, -79.3817)]
    valhalla_shape = encode_polyline(coords, precision=6)
    google_shape = valhalla_shape_to_google_polyline(valhalla_shape)
    assert google_shape is not None
    decoded = decode_polyline(google_shape, precision=5)
    assert len(decoded) == 2
    assert abs(decoded[0][0] - coords[0][0]) < 1e-4
    assert abs(decoded[1][1] - coords[1][1]) < 1e-4

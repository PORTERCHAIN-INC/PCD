"""Encoded polyline helpers — Google/OSRM (1e-5) and Valhalla (1e-6)."""

from __future__ import annotations


def decode_polyline(encoded: str, *, precision: int = 5) -> list[tuple[float, float]]:
    factor = 10**precision
    points: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lat = ~(result >> 1) if result & 1 else result >> 1
        lat += delta_lat

        result = 0
        shift = 0
        while True:
            byte = ord(encoded[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lng = ~(result >> 1) if result & 1 else result >> 1
        lng += delta_lng

        points.append((lat / factor, lng / factor))

    return points


def encode_polyline(coords: list[tuple[float, float]], *, precision: int = 5) -> str:
    factor = 10**precision
    output: list[str] = []
    prev_lat = 0
    prev_lng = 0

    for lat, lng in coords:
        lat_i = round(lat * factor)
        lng_i = round(lng * factor)
        output.append(_encode_value(lat_i - prev_lat))
        output.append(_encode_value(lng_i - prev_lng))
        prev_lat = lat_i
        prev_lng = lng_i

    return "".join(output)


def _encode_value(value: int) -> str:
    value = ~(value << 1) if value < 0 else value << 1
    chunks: list[str] = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    chunks.append(chr(value + 63))
    return "".join(chunks)


def valhalla_shape_to_google_polyline(shape: str | None) -> str | None:
    """Re-encode Valhalla leg shape (precision 6) for Google Maps clients (precision 5)."""
    if not shape:
        return None
    coords = decode_polyline(shape, precision=6)
    if not coords:
        return shape
    return encode_polyline(coords, precision=5)

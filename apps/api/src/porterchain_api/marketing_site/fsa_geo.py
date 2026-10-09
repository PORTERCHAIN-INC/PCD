"""FSA -> registry centroid (no geocoding, no paid APIs)."""

from __future__ import annotations

from porterchain_pricing.components.fsa import normalize_fsa
from porterchain_pricing.gta150_fsa import gta150_fsa_record

_HUB = (43.6532, -79.3832)


def fsa_centroid(value: str | None) -> tuple[str, float, float] | None:
    """(FSA, lat, lng) for a covered FSA; None when outside the GTA ±150 km tile."""
    code = normalize_fsa(value or "")
    if not code:
        return None
    rec = gta150_fsa_record(code)
    if not rec or rec.get("active") is False:
        return None
    lat, lng = rec.get("lat"), rec.get("lng")
    if lat is None or lng is None:
        centroid = rec.get("centroid") if isinstance(rec.get("centroid"), dict) else {}
        lat, lng = centroid.get("lat", _HUB[0]), centroid.get("lng", _HUB[1])
    return code, float(lat), float(lng)

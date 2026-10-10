"""Self-hosted coordinates for addresses that arrive without lat/lng.

Uses the GTA FSA registry centroids (no paid geocoder, no network). Coordinates are marked
``coords_source = "fsa"`` so consumers know they are area-level, not rooftop.
"""

from __future__ import annotations

import re
from typing import Any

_POSTAL = re.compile(r"\b([A-Za-z]\d[A-Za-z])\s?(\d[A-Za-z]\d)?\b")


def postal_of(addr: dict[str, Any] | None) -> str | None:
    if not isinstance(addr, dict):
        return None
    for key in ("postal", "postal_code", "formatted"):
        value = addr.get(key)
        if isinstance(value, str):
            m = _POSTAL.search(value.upper())
            if m:
                return (m.group(1) + (" " + m.group(2) if m.group(2) else "")).upper()
    return None


def with_coords(addr: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a copy with lat/lng filled from the FSA centroid when missing."""
    if not isinstance(addr, dict):
        return addr
    if isinstance(addr.get("lat"), (int, float)) and isinstance(addr.get("lng"), (int, float)):
        return addr
    from porterchain_api.marketing_site.fsa_geo import fsa_centroid

    postal = postal_of(addr)
    hit = fsa_centroid(postal) if postal else None
    if not hit:
        return addr
    _, lat, lng = hit
    out = dict(addr)
    out.update({"lat": lat, "lng": lng, "coords_source": "fsa"})
    out.setdefault("postal", postal)
    return out


def fill_quote_coords(quote: Any) -> bool:
    """Fill pickup / dropoff / extra stops on a quote in place. True when anything changed."""
    changed = False
    for field in ("pickup", "dropoff"):
        cur = getattr(quote, field, None)
        new = with_coords(cur)
        if new is not cur:
            setattr(quote, field, new)
            changed = True
    stops = getattr(quote, "additional_stops", None)
    if isinstance(stops, list) and stops:
        filled = [with_coords(s) for s in stops]
        if any(a is not b for a, b in zip(filled, stops, strict=True)):
            quote.additional_stops = filled
            changed = True
    return changed

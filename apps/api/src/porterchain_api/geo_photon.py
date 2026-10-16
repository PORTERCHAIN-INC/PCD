"""Photon (self-hosted) address search for /v1/geo. Split out of routers/geo.py (LOC cap)."""

from __future__ import annotations

from typing import Any

import httpx

from porterchain_api.geo_text import (
    STREET_VALUES,
    normalize_postal,
    strip_unit,
    typed_house_number,
)
from porterchain_api.geo_text import (
    relaxed_queries as _relaxed_queries,
)


def _g():
    # Late import: router owns config + formatting helpers (avoids a circular import).
    from porterchain_api.routers import geo

    return geo


def photon_search(q: str, limit: int) -> list[dict[str, Any]]:
    postal = normalize_postal(q)
    if postal:
        q = postal
    else:
        q = strip_unit(q)
    typed_number = None if postal else typed_house_number(q)
    params = {
        "q": q,
        "limit": str(min(limit * 3, 30)),
        "lat": str(_g().HUB_LAT),
        "lon": str(_g().HUB_LNG),
        "bbox": _g().BBOX,
        "lang": "en",
    }
    with httpx.Client(timeout=_g().TIMEOUT_S) as client:
        features: list[dict[str, Any]] = []
        for attempt in _relaxed_queries(q, postal is not None):
            params["q"] = attempt
            res = client.get(f"{_g().photon_url()}/api", params=params)
            res.raise_for_status()
            features = res.json().get("features") or []
            if features:
                break
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for f in features:
        props = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2 or (props.get("countrycode") or "").upper() not in {
            "",
            "CA",
        }:
            continue
        lng, lat = float(coords[0]), float(coords[1])
        if _g()._km(lat, lng) > _g().MAX_KM:
            continue
        props = dict(props)
        if (
            typed_number
            and not props.get("housenumber")
            and (
                props.get("osm_value") in STREET_VALUES or props.get("type") == "street"
            )
        ):
            # Street-level hit for "8500 Mount Pleasant Way": keep the typed house number.
            props.setdefault("street", props.get("name"))
            props["housenumber"] = typed_number
            props["name"] = None
        main, secondary = _g()._format(props)
        if not main:
            continue
        formatted = ", ".join(x for x in (main, secondary) if x)
        if formatted in seen:
            continue
        seen.add(formatted)
        place = {
            "formatted": formatted,
            "lat": lat,
            "lng": lng,
            "postal": props.get("postcode"),
            "city": props.get("city") or props.get("town") or props.get("village"),
            "province": "ON" if props.get("state") == "Ontario" else props.get("state"),
        }
        out.append(
            {
                "id": _g()._encode(place),
                "main": main,
                "secondary": secondary,
                "formatted": formatted,
            }
        )
        if len(out) >= limit:
            break
    return out


def _postal_fallback(q: str) -> dict[str, Any] | None:
    """Full postal code with no Photon hit: suggest its FSA centroid (approximate)."""
    from porterchain_api.marketing_site.fsa_geo import fsa_centroid

    postal = normalize_postal(q)
    hit = fsa_centroid(postal or q)
    if not postal or not hit:
        return None
    _fsa, lat, lng = hit
    if _g()._km(lat, lng) > _g().MAX_KM:
        return None
    place = {
        "formatted": f"{postal}, ON",
        "lat": lat,
        "lng": lng,
        "postal": postal,
        "province": "ON",
        "approximate": True,
    }
    return {
        "id": _g()._encode(place),
        "main": postal,
        "secondary": "ON (area)",
        "formatted": place["formatted"],
    }

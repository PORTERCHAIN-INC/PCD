"""Photon (self-hosted) address search for /v1/geo. Split out of routers/geo.py (LOC cap).

Confidence rules (house numbers must be right, never invented on the wrong segment):
- an OSM address point whose number AND street match what was typed -> confident;
- a named place (POI) or a postal code hit -> confident;
- only street segments: keep the typed number only when every matching segment lies
  within SEGMENT_SPREAD_KM of the first (one stretch of road) -> not confident;
  otherwise show the street without a number.
The router asks Google (when enabled) only when no result is confident.
"""

from __future__ import annotations

import math
from typing import Any

import httpx

from porterchain_api.geo_text import (
    STREET_VALUES,
    TORONTO_DISTRICTS,
    city_matches,
    expand_short_forms,
    lead_city_last,
    normalize_postal,
    split_city,
    street_core,
    strip_unit,
    typed_house_number,
)
from porterchain_api.geo_text import relaxed_queries as _relaxed_queries

SEGMENT_SPREAD_KM = 1.5


def _g():
    # Late import: router owns config + formatting helpers (avoids a circular import).
    from porterchain_api.routers import geo

    return geo


def _dist_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    )
    return 12742 * math.asin(math.sqrt(h))


def _fetch(q: str, is_postal: bool) -> list[dict[str, Any]]:
    params = {
        "limit": "30",
        "lat": str(_g().HUB_LAT),
        "lon": str(_g().HUB_LNG),
        "bbox": _g().BBOX,
        "lang": "en",
    }
    with httpx.Client(timeout=_g().TIMEOUT_S) as client:
        for attempt in _relaxed_queries(q, is_postal):
            params["q"] = attempt
            res = client.get(f"{_g().photon_url()}/api", params=params)
            res.raise_for_status()
            features = res.json().get("features") or []
            if features:
                return features
    return []


def _display(props: dict[str, Any]) -> dict[str, Any]:
    p = dict(props)
    district = (p.get("district") or "").strip()
    if (p.get("city") or "") == "Toronto" and district.lower() in TORONTO_DISTRICTS:
        p["city"] = f"{district}, Toronto"
    return p


def photon_search_scored(q: str, limit: int) -> tuple[list[dict[str, Any]], bool]:
    """(suggestions, confident)."""
    postal = normalize_postal(q)
    typed_city: str | None = None
    if postal:
        search = postal
    else:
        search = expand_short_forms(strip_unit(q))
        search = lead_city_last(search)
        typed_city = split_city(search)[1]
    number = None if postal else typed_house_number(search)
    typed_street = None
    if number:
        typed_street = street_core(split_city(search)[0][len(number) :])
    features = _fetch(search, postal is not None)
    if not features and typed_city:
        features = _fetch(
            split_city(search)[0], False
        )  # city spelled differently in OSM
    if postal:
        return _postal_area(postal, features)

    exact: list[tuple[dict[str, Any], tuple[float, float]]] = []
    segments: list[tuple[dict[str, Any], tuple[float, float]]] = []
    others: list[tuple[dict[str, Any], tuple[float, float]]] = []
    loose: list[tuple[dict[str, Any], tuple[float, float]]] = []
    for f in features:
        props = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2 or (props.get("countrycode") or "").upper() not in {
            "",
            "CA",
        }:
            continue
        pt = (float(coords[1]), float(coords[0]))
        if _g()._km(*pt) > _g().MAX_KM or not city_matches(typed_city, props):
            continue
        is_street = (
            props.get("osm_value") in STREET_VALUES or props.get("type") == "street"
        )
        street_name = street_core(
            props.get("street") or (props.get("name") if is_street else "")
        )
        if number and typed_street:
            if props.get("housenumber") == number and street_name == typed_street:
                exact.append((props, pt))
            elif props.get("housenumber") == number and street_loose_match(typed_street, street_name):
                loose.append((props, pt))
            elif is_street and street_name == typed_street:
                segments.append((props, pt))
            elif props.get("osm_value") == "bus_stop" or (
                props.get("housenumber") and not props.get("name")
            ):
                continue  # bus stops / other numbers on other streets: noise for an address
            else:
                others.append((props, pt))
        else:
            others.append((props, pt))

    picked: list[tuple[dict[str, Any], tuple[float, float]]] = []
    confident = False
    if not exact and loose:
        exact = loose  # same number, street typed with a town/postal after it or spaced differently
    if exact:
        picked, confident = exact, True
    elif segments:
        first = segments[0][1]
        one_stretch = all(_dist_km(first, s[1]) <= SEGMENT_SPREAD_KM for s in segments)
        if one_stretch:
            props = dict(segments[0][0])
            props["street"] = props.get("street") or props.get("name")
            props["housenumber"], props["name"] = number, None
            picked = [(props, first)]
        else:
            picked = [
                (
                    {
                        **s[0],
                        "street": s[0].get("street") or s[0].get("name"),
                        "name": None,
                        "housenumber": None,
                    },
                    s[1],
                )
                for s in segments
            ]
    if not number:
        picked = others
        # A number typed somewhere (e.g. "Milton 8500 ...") that we could not place: not sure.
        confident = bool(others) and not any(w[:1].isdigit() for w in search.split())
    elif not picked:
        picked = others
    if postal and picked:
        confident = True

    picked = postal_consistent(picked)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for props, (lat, lng) in picked:
        props = _display(props)
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
    return out, confident and bool(out)


_DIRECTIONS = {"east", "west", "north", "south", "e", "w", "n", "s"}


def street_loose_match(typed: str, cand: str) -> bool:
    """'willoughby place, bowmanville' ~ 'willoughby place'; 'woody vine way' ~ 'woody vineway'.
    A trailing direction is never dropped ('king street east' is not 'king street')."""
    if not typed or not cand:
        return False
    head = typed.split(",")[0].strip()
    if head.replace(" ", "") == cand.replace(" ", ""):
        return True
    if not head.startswith(cand + " ") and head != cand:
        return False
    nxt = head[len(cand) :].split()
    return not nxt or nxt[0] not in _DIRECTIONS


def postal_fits(props: dict[str, Any]) -> bool:
    """Toronto postal codes start with M; GTA cities outside Toronto use L/N/K, never M."""
    pc = (props.get("postcode") or "").strip().upper()
    if not pc:
        return True
    in_toronto = (props.get("city") or "").strip().lower() == "toronto"
    return pc.startswith("M") == in_toronto


def postal_consistent(
    picked: list[tuple[dict[str, Any], tuple[float, float]]],
) -> list[tuple[dict[str, Any], tuple[float, float]]]:
    """Demote hits whose postal code doesn't fit the city; drop them when the same address
    is also present with a consistent postal code (OSM sometimes has both)."""

    def key(p: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            (p.get("name") or "").lower(),
            str(p.get("housenumber") or ""),
            street_core(p.get("street")),
            (p.get("city") or "").lower(),
        )

    good = [x for x in picked if postal_fits(x[0])]
    good_keys = {key(x[0]) for x in good}
    bad = [x for x in picked if not postal_fits(x[0]) and key(x[0]) not in good_keys]
    return good + bad


def _postal_area(postal: str, features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    """A typed postal code: one suggestion for that exact code (centre of its addresses).
    Photon's near-misses (other codes sharing digits) are never offered as the answer."""
    pts: list[tuple[float, float]] = []
    cities: dict[str, int] = {}
    for f in features:
        props = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) != 2 or normalize_postal(props.get("postcode") or "") != postal:
            continue
        pt = (float(coords[1]), float(coords[0]))
        if _g()._km(*pt) > _g().MAX_KM:
            continue
        pts.append(pt)
        city = _display(props).get("city") or props.get("town") or props.get("village")
        if city:
            cities[city] = cities.get(city, 0) + 1
    if not pts:
        return [], False
    lat = sum(p[0] for p in pts) / len(pts)
    lng = sum(p[1] for p in pts) / len(pts)
    city = max(cities, key=cities.get) if cities else None
    secondary = f"{city}, ON" if city else "ON"
    place = {
        "formatted": f"{postal}, {secondary}",
        "lat": lat,
        "lng": lng,
        "postal": postal,
        "city": city,
        "province": "ON",
    }
    return [{"id": _g()._encode(place), "main": postal, "secondary": secondary, "formatted": place["formatted"]}], True


def photon_search(q: str, limit: int) -> list[dict[str, Any]]:
    return photon_search_scored(q, limit)[0]


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

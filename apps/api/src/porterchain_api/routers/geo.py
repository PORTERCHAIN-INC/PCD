"""Free address search: Nominatim autocomplete (Photon later), Nominatim / FSA fallback.

No Google APIs. Results are biased to Toronto and limited to the GTA ±150 km
service area. Public, per-IP rate limited.
"""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import re
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from porterchain_api.platform.rate_limit import (
    bucket_key,
    check_fixed_window,
    rate_limit_headers,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/geo", tags=["geo"])

HUB_LAT, HUB_LNG = 43.6532, -79.3832
MAX_KM = 150.0
# lon_min, lat_min, lon_max, lat_max: GTA hub ±150 km.
BBOX = "-81.25,42.30,-77.52,45.00"
RATE_LIMIT_PER_MIN = 90
TIMEOUT_S = 3.0


def photon_url() -> str:
    return os.environ.get("PHOTON_URL", "").rstrip("/")


NOMINATIM_SEARCH_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
NOMINATIM_UA = "PorterchainAddressSearch/1.0 (https://porterchain.com)"
SUGGEST_CACHE_TTL_S = 60 * 60 * 24 * 7
NOMINATIM_GAP_MS = 1100  # public Nominatim: max 1 request/second for the whole site


def _redis():
    from porterchain_shared.redis_client import get_redis_client

    return get_redis_client()


def _nominatim_slot() -> bool:
    """One upstream call per ~1.1 s across all API replicas; skip (not queue) when busy."""
    try:
        return bool(
            _redis().set("pc:geo:nominatim:slot", "1", nx=True, px=NOMINATIM_GAP_MS)
        )
    except Exception:  # noqa: BLE001
        return True


def nominatim_suggest(q: str, limit: int) -> list[dict[str, Any]]:
    key = "pc:geo:suggest:v1:" + q.strip().lower()[:200]
    try:
        cached = _redis().get(key)
        if cached:
            return json.loads(cached)[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.debug("geo suggest cache unavailable: %s", exc)
    if not _nominatim_slot():
        return []
    params = {
        "q": q,
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": "8",
        "countrycodes": "ca",
        "viewbox": "-81.25,45.00,-77.52,42.30",
        "bounded": "1",
    }
    with httpx.Client(timeout=TIMEOUT_S) as client:
        res = client.get(
            NOMINATIM_SEARCH_URL, params=params, headers={"User-Agent": NOMINATIM_UA}
        )
        res.raise_for_status()
        rows = res.json() or []
    m = re.match(r"\s*(\d+[a-zA-Z]?)\b", q)
    typed_number = m.group(1) if m else None
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for r in rows:
        try:
            lat, lng = float(r["lat"]), float(r["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if _km(lat, lng) > MAX_KM:
            continue
        a = r.get("address") or {}
        props = {
            "housenumber": a.get("house_number"),
            "street": a.get("road"),
            "name": r.get("name") if r.get("name") != a.get("road") else None,
            "city": a.get("city")
            or a.get("town")
            or a.get("village")
            or a.get("municipality"),
            "state": a.get("state"),
            "postcode": a.get("postcode"),
        }
        if not props["housenumber"] and typed_number and props["street"]:
            # OSM often lacks the house number; keep the one the customer typed.
            props["housenumber"] = typed_number
        main, secondary = _format(props)
        if not main:
            main = (r.get("display_name") or "").split(",")[0]
        formatted = ", ".join(x for x in (main, secondary) if x)
        if not formatted or formatted in seen:
            continue
        seen.add(formatted)
        place = {
            "formatted": formatted,
            "lat": lat,
            "lng": lng,
            "postal": props["postcode"],
            "city": props["city"],
            "province": "ON" if props["state"] == "Ontario" else props["state"],
        }
        out.append(
            {
                "id": _encode(place),
                "main": main,
                "secondary": secondary,
                "formatted": formatted,
            }
        )
    try:
        _redis().setex(key, SUGGEST_CACHE_TTL_S, json.dumps(out))
    except Exception as exc:  # noqa: BLE001
        logger.debug("geo suggest cache unavailable: %s", exc)
    return out[:limit]


def _km(lat: float, lng: float) -> float:
    p1, p2 = math.radians(HUB_LAT), math.radians(lat)
    dp, dl = p2 - p1, math.radians(lng - HUB_LNG)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _limit(request: Request, response: Response) -> None:
    allowed, current, err = check_fixed_window(
        bucket_key("geo", _client_ip(request)), RATE_LIMIT_PER_MIN
    )
    if err:  # Redis down: degrade open so address entry keeps working.
        logger.warning("geo rate limit unavailable: %s", err)
        return
    response.headers.update(rate_limit_headers(RATE_LIMIT_PER_MIN, current))
    if not allowed:
        raise HTTPException(status_code=429, detail="rate_limited")


def _encode(item: dict[str, Any]) -> str:
    raw = json.dumps(item, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(token: str) -> dict[str, Any]:
    try:
        pad = "=" * (-len(token) % 4)
        data = json.loads(base64.urlsafe_b64decode(token + pad))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_place_id") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="invalid_place_id")
    return data


def _format(p: dict[str, Any]) -> tuple[str, str]:
    street = " ".join(x for x in (p.get("housenumber"), p.get("street")) if x)
    name = p.get("name") or ""
    main = street or name
    if name and street and name != street:
        main = f"{name}, {street}"
    city = p.get("city") or p.get("town") or p.get("village") or p.get("county") or ""
    secondary = ", ".join(
        x
        for x in (
            city,
            "ON" if p.get("state") == "Ontario" else p.get("state"),
            p.get("postcode"),
        )
        if x
    )
    return main, secondary


from porterchain_api.geo_photon import _postal_fallback, photon_search
from porterchain_api.geo_text import (
    normalize_postal,
)


def _postal_complete(postal: str | None) -> bool:
    return bool(postal) and len((postal or "").replace(" ", "")) == 6


@router.get("/autocomplete")
def autocomplete(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=3, max_length=200),
    limit: int = Query(6, ge=1, le=10),
) -> dict[str, Any]:
    _limit(request, response)
    q = q.strip()
    if photon_url():
        try:
            results = photon_search(q, limit)
            if results or not normalize_postal(q):
                return {"results": results, "source": "photon"}
            fsa = _postal_fallback(q)
            if fsa:
                return {"results": [fsa], "source": "fsa"}
            return {"results": [], "source": "photon"}
        except httpx.HTTPError as exc:
            logger.warning("photon unavailable, falling back to nominatim: %s", exc)
    try:
        return {"results": nominatim_suggest(q, limit), "source": "nominatim"}
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("nominatim suggest unavailable: %s", exc)
        return {"results": [], "source": "unavailable"}


@router.get("/place")
def place(
    request: Request,
    response: Response,
    id: str | None = Query(None, max_length=2000),
    q: str | None = Query(None, max_length=300),
) -> dict[str, Any]:
    """Resolve an autocomplete pick (or free text) to a booking address with coordinates."""
    _limit(request, response)
    if id:
        data = _decode(id)
        lat, lng = data.get("lat"), data.get("lng")
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            raise HTTPException(status_code=400, detail="invalid_place_id")
        result = {**data, "placeId": id, "source": "photon"}
        if not _postal_complete(result.get("postal")):
            # Photon often lacks the full postcode on a street hit; keep what we have.
            result["postal"] = result.get("postal") or None
        return result
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="id_or_q_required")
    from porterchain_api.merchant_engine.import_geocode import geocode_stop

    geo = geocode_stop(address=q.strip(), province="ON")
    if geo.lat is None or geo.lng is None:
        from porterchain_api.marketing_site.fsa_geo import fsa_centroid

        hit = fsa_centroid(q)
        if not hit:
            raise HTTPException(status_code=404, detail="not_found")
        fsa, lat, lng = hit
        return {
            "formatted": q.strip(),
            "lat": lat,
            "lng": lng,
            "postal": fsa,
            "source": "fsa",
            "approximate": True,
        }
    if _km(geo.lat, geo.lng) > MAX_KM:
        raise HTTPException(status_code=422, detail="out_of_service_area")
    return {
        "formatted": geo.formatted or q.strip(),
        "lat": geo.lat,
        "lng": geo.lng,
        "postal": geo.postal,
        "city": geo.city,
        "source": geo.source or "nominatim",
        "approximate": geo.status == "approximate",
    }

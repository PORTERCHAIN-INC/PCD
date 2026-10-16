"""Google Places (New) backup for /v1/geo — only when our own search has no confident hit.

Our free search (Photon, later NAR) always goes first. Google is called server-side only,
with the IP-restricted server key, behind GEO_GOOGLE_FALLBACK and a daily call cap
(GEO_GOOGLE_DAILY_CAP, default 300) so usage stays inside Google's free monthly allowance.
Every billable call (autocomplete or place details) increments a per-day Redis counter,
shown on the admin integrations panel.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
DETAILS_URL = "https://places.googleapis.com/v1/places/{id}"
COUNTER_PREFIX = "pc:geo:google:calls:"
TIMEOUT_S = 3.0


def _key() -> str:
    return (os.environ.get("GOOGLE_MAPS_SERVER_API_KEY") or "").strip()


def enabled() -> bool:
    flag = (os.environ.get("GEO_GOOGLE_FALLBACK") or "").strip().lower()
    return flag in {"1", "true", "yes", "on"} and bool(_key())


def daily_cap() -> int:
    try:
        return max(0, int(os.environ.get("GEO_GOOGLE_DAILY_CAP", "300")))
    except ValueError:
        return 300


def _counter_key(day: str | None = None) -> str:
    return COUNTER_PREFIX + (day or datetime.now(UTC).strftime("%Y%m%d"))


def _redis():
    from porterchain_shared.redis_client import get_redis_client

    return get_redis_client()


def usage_today() -> dict[str, Any]:
    try:
        used = int(_redis().get(_counter_key()) or 0)
    except Exception:  # noqa: BLE001
        used = None
    return {"enabled": enabled(), "calls_today": used, "daily_cap": daily_cap()}


def _take_slot() -> bool:
    """Reserve one billable call; False when today's cap is reached or Redis is down."""
    try:
        r = _redis()
        key = _counter_key()
        n = int(r.incr(key))
        if n == 1:
            r.expire(key, 3 * 86400)
        return n <= daily_cap()
    except Exception as exc:  # noqa: BLE001
        logger.warning("google geo counter unavailable, skipping fallback: %s", exc)
        return False  # fail closed: never spend without a counter


def suggest(q: str, limit: int, bbox: str) -> list[dict[str, Any]]:
    """Places Autocomplete (New), restricted to Canada + the GTA bbox, addresses first."""
    if not enabled() or not _take_slot():
        return []
    lon_min, lat_min, lon_max, lat_max = (float(x) for x in bbox.split(","))
    body = {
        "input": q,
        "includedRegionCodes": ["ca"],
        "languageCode": "en",
        "locationRestriction": {
            "rectangle": {
                "low": {"latitude": lat_min, "longitude": lon_min},
                "high": {"latitude": lat_max, "longitude": lon_max},
            }
        },
    }
    with httpx.Client(timeout=TIMEOUT_S) as client:
        res = client.post(
            AUTOCOMPLETE_URL, json=body, headers={"X-Goog-Api-Key": _key()}
        )
        res.raise_for_status()
        rows = res.json().get("suggestions") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        p = row.get("placePrediction") or {}
        pid = p.get("placeId")
        text = (p.get("text") or {}).get("text") or ""
        sf = p.get("structuredFormat") or {}
        if not pid or not text:
            continue
        main = (sf.get("mainText") or {}).get("text") or text.split(",")[0]
        secondary = ((sf.get("secondaryText") or {}).get("text") or "").replace(
            ", Canada", ""
        )
        out.append(
            {
                "g": pid,
                "main": main,
                "secondary": secondary,
                "formatted": text.replace(", Canada", ""),
            }
        )
        if len(out) >= limit:
            break
    return out


def details(place_id: str) -> dict[str, Any] | None:
    if not enabled() or not _take_slot():
        return None
    with httpx.Client(timeout=TIMEOUT_S) as client:
        res = client.get(
            DETAILS_URL.format(id=place_id),
            headers={
                "X-Goog-Api-Key": _key(),
                "X-Goog-FieldMask": "formattedAddress,location,addressComponents",
            },
        )
        res.raise_for_status()
        body = res.json()
    loc = body.get("location") or {}
    if loc.get("latitude") is None or loc.get("longitude") is None:
        return None
    comps = {
        t: c.get("longText")
        for c in body.get("addressComponents") or []
        for t in c.get("types") or []
    }
    return {
        "formatted": (body.get("formattedAddress") or "").replace(", Canada", ""),
        "lat": float(loc["latitude"]),
        "lng": float(loc["longitude"]),
        "postal": comps.get("postal_code"),
        "city": comps.get("locality")
        or comps.get("sublocality")
        or comps.get("administrative_area_level_3"),
        "province": "ON"
        if comps.get("administrative_area_level_1") == "Ontario"
        else comps.get("administrative_area_level_1"),
        "source": "google",
    }

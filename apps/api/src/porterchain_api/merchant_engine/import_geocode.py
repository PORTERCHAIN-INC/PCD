"""Nominatim geocoding for route import (no Google / paid geocode APIs).

The point is for Valhalla/OSRM. CSV-supplied lat/lng skip the lookup.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from porterchain_api.merchant_engine.address_normalize import normalize_address

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "PorterchainRouteImport/1.0 (https://porterchain.com)"
MIN_INTERVAL_S = 1.05  # Nominatim usage policy ~1 req/s
TIMEOUT_S = 8.0
CACHE_TTL_S = 60 * 60 * 24 * 30  # 30 days
CACHE_PREFIX = "pc:geocode:nominatim:v1:"

_last_call_at = 0.0


@dataclass
class GeocodeResult:
    lat: float | None
    lng: float | None
    formatted: str | None
    status: str  # ok | approximate | failed | supplied | cached
    confidence: float
    unit: str | None
    raw: str
    geocode_query: str
    issues: list[str]
    place_id: str | None = None
    source: str | None = None  # csv | nominatim | places
    city: str | None = None
    postal: str | None = None


def _throttle() -> None:
    global _last_call_at
    elapsed = time.monotonic() - _last_call_at
    if elapsed < MIN_INTERVAL_S:
        time.sleep(MIN_INTERVAL_S - elapsed)
    _last_call_at = time.monotonic()


def _cache_key(query: str) -> str:
    digest = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
    return f"{CACHE_PREFIX}{digest}"


def _cache_get(query: str) -> dict[str, Any] | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(_cache_key(query))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _cache_set(query: str, hit: dict[str, Any]) -> None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        get_redis_client().setex(_cache_key(query), CACHE_TTL_S, json.dumps(hit))
    except Exception:  # noqa: BLE001
        return


def _nominatim_search(query: str) -> dict[str, Any] | None:
    if not query.strip():
        return None
    cached = _cache_get(query)
    if cached is not None:
        return {**cached, "_cached": True}

    _throttle()
    url = f"{NOMINATIM_URL}?q={quote(query)}&format=json&limit=1&countrycodes=ca"
    try:
        with httpx.Client(timeout=TIMEOUT_S) as client:
            res = client.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            )
            if res.status_code >= 400:
                logger.warning("Nominatim HTTP %s for %s", res.status_code, query[:80])
                return None
            data = res.json()
    except httpx.HTTPError as exc:
        logger.warning("Nominatim unreachable: %s", exc)
        return None
    if not isinstance(data, list) or not data:
        return None
    hit = data[0]
    _cache_set(
        query,
        {
            "lat": hit.get("lat"),
            "lon": hit.get("lon"),
            "display_name": hit.get("display_name"),
        },
    )
    return hit


def geocode_stop(
    *,
    address: str,
    unit: str | None = None,
    city: str | None = None,
    province: str | None = None,
    postal: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    place_id: str | None = None,
    source: str | None = None,
) -> GeocodeResult:
    """``place_id``/``source`` only matter with ``lat``/``lng``: a stop re-resolved with
    coordinates it already had keeps where they came from."""
    norm = normalize_address(address, unit=unit, city=city, province=province, postal=postal)
    issues = list(norm.issues)

    if lat is not None and lng is not None:
        return GeocodeResult(
            lat=float(lat),
            lng=float(lng),
            # Prefer the merchant/Places string; normalize only fills gaps.
            formatted=(address or "").strip() or norm.street or address,
            status="supplied",
            confidence=1.0,
            unit=norm.unit,
            raw=norm.raw,
            geocode_query=norm.geocode_query,
            issues=issues,
            place_id=place_id,
            source=source or "csv",
            city=norm.city,
            postal=norm.postal,
        )

    attempts = [
        ("ok", 0.9, norm.geocode_query),
        (
            "ok",
            0.85,
            ", ".join(
                p
                for p in [
                    norm.street,
                    norm.city,
                    norm.province or "ON",
                    norm.postal,
                    "Canada",
                ]
                if p
            ),
        ),
    ]
    if norm.postal and norm.city:
        attempts.append(
            (
                "approximate",
                0.55,
                f"{norm.postal}, {norm.city}, {norm.province or 'ON'}, Canada",
            )
        )

    seen: set[str] = set()
    for status, confidence, query in attempts:
        q = query.strip()
        if not q or q in seen:
            continue
        seen.add(q)
        hit = _nominatim_search(q)
        if not hit:
            continue
        try:
            was_cached = bool(hit.pop("_cached", False)) if isinstance(hit, dict) else False
            return GeocodeResult(
                lat=float(hit["lat"]),
                lng=float(hit["lon"]),
                formatted=str(hit.get("display_name") or norm.street or address),
                status="cached" if was_cached else status,
                confidence=confidence,
                unit=norm.unit,
                raw=norm.raw,
                geocode_query=q,
                issues=issues + (["address.approximate"] if status == "approximate" else []),
                source="nominatim",
                city=norm.city,
                postal=norm.postal,
            )
        except (KeyError, TypeError, ValueError):
            continue

    issues.append("stop.geocode_failed")
    return GeocodeResult(
        lat=None,
        lng=None,
        formatted=None,
        status="failed",
        confidence=0.0,
        unit=norm.unit,
        raw=norm.raw,
        geocode_query=norm.geocode_query,
        issues=issues,
        city=norm.city,
        postal=norm.postal,
    )

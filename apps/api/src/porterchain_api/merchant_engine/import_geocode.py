"""Nominatim geocoding for route import (no Google / paid geocode APIs).

The point is for Valhalla/OSRM. CSV-supplied lat/lng skip the lookup.
"""

from __future__ import annotations

import re

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from porterchain_api.merchant_engine.address_normalize import normalize_address

logger = logging.getLogger(__name__)

NOMINATIM_URL = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
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


_ORD_RE = re.compile(r"^(\d+[A-Za-z]?\s+)(\d+)(\s+(?:Line|Concession|Conc|Sideroad|Side Road)\b)", re.I)
_POSTAL_RE = re.compile(r"\b([A-Z]\d[A-Z])\s?\d[A-Z]\d\b", re.I)


def _ordinal_street(street: str) -> str:
    """'3075 8 Line' -> '3075 8th Line' (OSM names numbered concession roads this way)."""
    def suffix(n: int) -> str:
        return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")

    m = _ORD_RE.match(street or "")
    if not m:
        return street
    n = int(m.group(2))
    return f"{m.group(1)}{n}{suffix(n)}{m.group(3)}{street[m.end():]}"


def _postal_mismatch(postal: str | None, display: Any) -> bool:
    """L197c: the hit's forward sortation area differs from the one the merchant gave."""
    if not postal or not isinstance(display, str):
        return False
    want = _POSTAL_RE.search(postal)
    got = _POSTAL_RE.search(display)
    return bool(want and got and want.group(1).upper() != got.group(1).upper())


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
    # L197b: Nominatim often has no Canadian postcode for a building -> retry without it,
    # and spell concession roads the OSM way ("8 Line" -> "8th Line").
    # The street may carry the town itself ("3075 8 Line, Bradford") when no city column is set.
    if norm.street:
        base = [p for p in [norm.street, norm.city, norm.province or "ON", "Canada"] if p]
        attempts.append(("ok", 0.75, ", ".join(base)))
        ordinal = _ordinal_street(norm.street)
        if ordinal != norm.street:
            attempts.append(("ok", 0.75, ", ".join([ordinal, *base[1:]])))
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
                issues=issues
                + (["address.approximate"] if status == "approximate" else [])
                + (["address.postal_mismatch"] if _postal_mismatch(norm.postal, hit.get("display_name")) else []),
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

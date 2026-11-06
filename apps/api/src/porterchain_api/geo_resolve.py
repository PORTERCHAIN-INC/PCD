"""Shared address brain: one resolver for bulk import, booking, Shopify and portals.

Order (free first, never a silent guess):
  normalize (unit, postal O->0, street abbrev, fuzzy GTA city)
  -> Photon (self-hosted, confidence rules in geo_photon, top 5)
  -> Nominatim (limit=5, Canada)
  -> Google Places (capped; only when the #182 module exists and GEO_GOOGLE_FALLBACK is on)

Candidates outside GTA hub ±150 km are dropped before ranking. Callers still run
``assert_ontario_*`` as the final service-area gate.

Status:
  confident   one area, strong score -> book it
  ambiguous   2+ plausible areas, or postal disagrees with city/street -> ask the user
  approximate one area, weak score (postal centroid, street without number) -> flag
  failed      nothing in the service area
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import math
import os
import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any
from urllib.parse import urlencode

import httpx

from porterchain_api.merchant_engine.address_normalize import normalize_address

logger = logging.getLogger(__name__)

MAX_CANDIDATES = 5
HUB = (43.6532, -79.3832)
MAX_KM = 150.0
SAME_SPOT_KM = 0.25  # duplicates across providers
SAME_AREA_KM = 2.0  # farther apart than this = different area
SIMILAR_SCORE = 0.15  # candidates within this of the best are "just as likely"
CONFIDENT_SCORE = 0.8

STATUS_CONFIDENT = "confident"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_APPROXIMATE = "approximate"
STATUS_FAILED = "failed"

NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
_NOMINATIM_UA = "PorterchainGeoResolve/1.0 (https://porterchain.com)"
_NOM_CACHE_PREFIX = "pc:geo:resolve:nominatim:v1:"
_NOM_CACHE_TTL_S = 60 * 60 * 24 * 30

# GTA ±150 km municipalities + Toronto districts (fuzzy target list, lowercase).
GTA_CITIES = (
    "toronto", "north york", "scarborough", "etobicoke", "east york", "york",
    "mississauga", "brampton", "caledon", "oakville", "milton", "halton hills",
    "burlington", "hamilton", "stoney creek", "ancaster", "grimsby", "st catharines",
    "niagara falls", "welland", "vaughan", "woodbridge", "maple", "concord",
    "richmond hill", "markham", "unionville", "stouffville", "whitchurch-stouffville",
    "aurora", "newmarket", "king city", "east gwillimbury", "georgina", "bradford",
    "pickering", "ajax", "whitby", "oshawa", "clarington", "bowmanville", "courtice",
    "uxbridge", "scugog", "port perry", "barrie", "innisfil", "orangeville",
    "guelph", "kitchener", "waterloo", "cambridge", "brantford", "peterborough",
    "cobourg", "port hope", "orillia", "collingwood", "alliston", "georgetown", "acton",
)  # fmt: skip

_POSTAL_LOOSE = re.compile(r"\b([A-Z][0-9O][A-Z])\s?([0-9O][A-Z][0-9O])\b", re.I)
_FSA_RE = re.compile(r"\b([A-Z]\d[A-Z])\s?\d[A-Z]\d\b", re.I)
_EXTRA_ABBREV = (
    (re.compile(r"\bCres\.?(?=\W|$)", re.I), "Crescent"),
    (re.compile(r"\b(?:Crt|Ct)\.?(?=\W|$)", re.I), "Court"),
    (re.compile(r"\bPkwy\.?(?=\W|$)", re.I), "Parkway"),
    (re.compile(r"\bHwy\.?(?=\W|$)", re.I), "Highway"),
    (re.compile(r"\bLn\.?(?=\W|$)", re.I), "Lane"),
    (re.compile(r"\bCir\.?(?=\W|$)", re.I), "Circle"),
    (re.compile(r"\bTerr?\.?(?=\W|$)", re.I), "Terrace"),
    (re.compile(r"\bSq\.?(?=\W|$)", re.I), "Square"),
)


@dataclass
class Candidate:
    formatted: str
    lat: float
    lng: float
    city: str | None = None
    postal: str | None = None
    province: str | None = "ON"
    score: float = 0.5
    source: str = "photon"
    place_id: str | None = None

    @property
    def fsa(self) -> str:
        m = _FSA_RE.search(self.postal or "") or _FSA_RE.search(self.formatted or "")
        return m.group(1).upper() if m else ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["fsa"] = self.fsa
        return d


@dataclass
class ResolveResult:
    status: str
    candidates: list[Candidate]
    confidence: float
    source: str | None
    query: str
    reasons: list[str] = field(default_factory=list)
    normalized: dict[str, Any] = field(default_factory=dict)

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidates": [c.to_dict() for c in self.candidates],
            "confidence": self.confidence,
            "source": self.source,
            "query": self.query,
            "reasons": list(self.reasons),
            "normalized": dict(self.normalized),
        }


# --------------------------------------------------------------------------- cleaning


def repair_postal(text: str) -> str:
    """'L4C OA1' -> 'L4C 0A1': letter O typed for zero in the digit slots."""

    def fix(m: re.Match[str]) -> str:
        a, b = m.group(1).upper(), m.group(2).upper()
        a = a[0] + a[1].replace("O", "0") + a[2]
        b = b[0].replace("O", "0") + b[1] + b[2].replace("O", "0")
        return f"{a} {b}"

    return _POSTAL_LOOSE.sub(fix, text or "")


def expand_abbrev(text: str) -> str:
    out = text or ""
    for pat, full in _EXTRA_ABBREV:
        out = pat.sub(full, out)
    return out


def fuzzy_city(city: str | None) -> str | None:
    """'Richmnd Hil' -> 'Richmond Hill'. Only snaps to the GTA list; unknown stays as typed."""
    if not city:
        return city
    key = city.strip().lower().replace(".", "")
    if key in GTA_CITIES:
        return city.strip()
    hit = difflib.get_close_matches(key, GTA_CITIES, n=1, cutoff=0.85)
    return " ".join(w.capitalize() for w in hit[0].split()) if hit else city.strip()


def _fuzzy_city_in_text(text: str) -> str:
    """Fix a misspelt city in the trailing comma parts of a one-cell address."""
    parts = [p.strip() for p in (text or "").split(",")]
    for i in range(1, len(parts)):
        p = parts[i]
        if p and not any(ch.isdigit() for ch in p) and len(p) > 3:
            parts[i] = fuzzy_city(p) or p
    return ", ".join(x for x in parts if x)


def _city_key(city: str | None) -> str:
    c = (city or "").lower().replace(".", "").strip()
    # Toronto districts ("North York, Toronto") count as Toronto for area comparison.
    return c.split(",")[-1].strip() if c else ""


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    h = (
        math.sin((p2 - p1) / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[1] - a[1]) / 2) ** 2
    )
    return 12742 * math.asin(math.sqrt(h))


# --------------------------------------------------------------------------- providers


def _photon(query: str) -> tuple[list[Candidate], bool]:
    try:
        from porterchain_api import geo_photon
        from porterchain_api.routers import geo as geo_router

        rows, confident = geo_photon.photon_search_scored(query, MAX_CANDIDATES)
    except Exception as exc:  # noqa: BLE001
        logger.info("photon unavailable for resolve: %s", exc)
        return [], False
    out: list[Candidate] = []
    for i, row in enumerate(rows):
        try:
            place = geo_router._decode(row["id"])
            lat, lng = float(place["lat"]), float(place["lng"])
        except Exception:  # noqa: BLE001
            continue
        base = 0.92 if confident else (0.5 if place.get("approximate") else 0.65)
        out.append(
            Candidate(
                formatted=str(place.get("formatted") or row.get("formatted") or ""),
                lat=lat,
                lng=lng,
                city=place.get("city"),
                postal=place.get("postal"),
                province=place.get("province") or "ON",
                score=round(base - 0.01 * i, 3),
                source="photon",
            )
        )
    return out, confident


def _nominatim(query: str) -> list[Candidate]:
    from porterchain_api.merchant_engine import import_geocode as ig

    key = _NOM_CACHE_PREFIX + hashlib.sha256(query.strip().lower().encode()).hexdigest()
    data: Any = None
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(key)
        data = json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        data = None
    if data is None:
        ig._throttle()
        params = {
            "q": query,
            "format": "json",
            "limit": str(MAX_CANDIDATES),
            "countrycodes": "ca",
            "addressdetails": "1",
        }
        try:
            with httpx.Client(timeout=ig.TIMEOUT_S) as client:
                res = client.get(
                    f"{NOMINATIM_URL}?{urlencode(params)}",
                    headers={"User-Agent": _NOMINATIM_UA, "Accept": "application/json"},
                )
                if res.status_code >= 400:
                    return []
                data = res.json()
        except httpx.HTTPError as exc:
            logger.info("nominatim unavailable for resolve: %s", exc)
            return []
        try:
            from porterchain_shared.redis_client import get_redis_client

            get_redis_client().setex(key, _NOM_CACHE_TTL_S, json.dumps(data))
        except Exception:  # noqa: BLE001
            pass
    out: list[Candidate] = []
    for hit in data if isinstance(data, list) else []:
        try:
            addr = hit.get("address") or {}
            importance = float(hit.get("importance") or 0.4)
            base = 0.7 if addr.get("house_number") else 0.55
            out.append(
                Candidate(
                    formatted=str(hit.get("display_name") or ""),
                    lat=float(hit["lat"]),
                    lng=float(hit["lon"]),
                    city=addr.get("city")
                    or addr.get("town")
                    or addr.get("village")
                    or addr.get("municipality"),
                    postal=addr.get("postcode"),
                    province="ON"
                    if addr.get("state") == "Ontario"
                    else addr.get("state"),
                    score=round(min(0.9, base + 0.2 * importance), 3),
                    source="nominatim",
                    place_id=str(hit.get("place_id") or "") or None,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _google_module() -> Any | None:
    try:
        from porterchain_api import geo_google  # type: ignore[attr-defined]
    except ImportError:
        return None  # #182 not merged yet: stub stays dark
    return geo_google


def google_available() -> bool:
    """True when the capped Places backup (#182) is installed and GEO_GOOGLE_FALLBACK is on."""
    mod = _google_module()
    try:
        return bool(mod and mod.enabled())
    except Exception:  # noqa: BLE001
        return False


def _google(query: str) -> list[Candidate]:
    """Capped Places (New) backup. Each suggest/details call spends one daily-cap slot."""
    mod = _google_module()
    if mod is None or not google_available():
        return []
    from porterchain_api.routers import geo as geo_router

    try:
        rows = mod.suggest(query, 3, geo_router.BBOX)
    except Exception as exc:  # noqa: BLE001
        logger.info("google suggest failed: %s", exc)
        return []
    out: list[Candidate] = []
    for i, row in enumerate(rows[:3]):
        try:
            d = mod.details(row["g"])
        except Exception:  # noqa: BLE001
            d = None
        if not d:
            continue
        out.append(
            Candidate(
                formatted=d.get("formatted") or row.get("formatted") or "",
                lat=float(d["lat"]),
                lng=float(d["lng"]),
                city=d.get("city"),
                postal=d.get("postal"),
                province=d.get("province") or "ON",
                score=round(0.85 - 0.05 * i, 3),
                source="google",
                place_id=row.get("g"),
            )
        )
    return out


# --------------------------------------------------------------------------- ranking


def _in_area(c: Candidate) -> bool:
    if c.province and c.province not in {"ON", "Ontario"}:
        return False
    return km(HUB, (c.lat, c.lng)) <= MAX_KM


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    out: list[Candidate] = []
    for c in sorted(cands, key=lambda x: -x.score):
        twin = next(
            (o for o in out if km((o.lat, o.lng), (c.lat, c.lng)) <= SAME_SPOT_KM), None
        )
        if twin is None:
            out.append(c)
        else:
            # Two providers agree on the spot: a little more sure, keep the richer record.
            twin.score = round(min(0.98, max(twin.score, c.score) + 0.04), 3)
            twin.postal = twin.postal or c.postal
            twin.city = twin.city or c.city
    return out


def different_area(a: Candidate, b: Candidate) -> bool:
    if km((a.lat, a.lng), (b.lat, b.lng)) > SAME_AREA_KM:
        return True
    ca, cb = _city_key(a.city), _city_key(b.city)
    if ca and cb and ca != cb:
        return True
    return bool(a.fsa and b.fsa and a.fsa != b.fsa)


def _city_fits(typed_city: str, c: Candidate) -> bool:
    return _city_key(typed_city) in f"{c.city or ''} {c.formatted}".lower()


def classify(
    cands: list[Candidate],
    *,
    typed_city: str | None = None,
    typed_postal: str | None = None,
) -> tuple[str, list[Candidate], list[str]]:
    """Rank in-area candidates and decide confident / ambiguous / approximate / failed."""
    reasons: list[str] = []
    pool = [
        replace(c) for c in cands if _in_area(c)
    ]  # copies: scoring never mutates input
    if len(pool) < len(cands):
        reasons.append("dropped_out_of_service_area")
    pool = _dedupe(pool)
    if not pool:
        return STATUS_FAILED, [], [*reasons, "no_candidates"]

    # A typed city narrows the field (Main St, Markham vs Main St, Richmond Hill).
    if typed_city:
        fitting = [c for c in pool if _city_fits(typed_city, c)]
        if fitting:
            for c in pool:
                if c not in fitting:
                    c.score = round(c.score - 0.2, 3)
        else:
            reasons.append("city_not_matched")
    m = _FSA_RE.search(typed_postal or "")
    typed_fsa = m.group(1).upper() if m else None
    if typed_fsa:
        for c in pool:
            if c.fsa == typed_fsa:
                c.score = round(min(0.98, c.score + 0.05), 3)
    pool.sort(key=lambda c: -c.score)
    pool = pool[:MAX_CANDIDATES]
    best = pool[0]

    rivals = [
        c
        for c in pool[1:]
        if best.score - c.score <= SIMILAR_SCORE and different_area(best, c)
    ]
    if rivals:
        return STATUS_AMBIGUOUS, pool, [*reasons, "multiple_areas"]
    if typed_fsa and best.fsa and best.fsa != typed_fsa:
        return STATUS_AMBIGUOUS, pool, [*reasons, "postal_disagrees"]
    if "city_not_matched" in reasons:
        return STATUS_AMBIGUOUS, pool, reasons
    if best.score >= CONFIDENT_SCORE:
        return STATUS_CONFIDENT, pool, reasons
    return STATUS_APPROXIMATE, pool, [*reasons, "low_score"]


# --------------------------------------------------------------------------- entry point


def resolve_address(
    address: str,
    *,
    unit: str | None = None,
    city: str | None = None,
    province: str | None = None,
    postal: str | None = None,
    allow_google: bool = True,
) -> ResolveResult:
    """Resolve free text (plus optional columns) to ranked GTA candidates.

    Pure read: no DB, no booking. Safe for autocomplete, import, Shopify and portals.
    """
    text = _fuzzy_city_in_text(expand_abbrev(repair_postal(address or "")))
    norm = normalize_address(
        text,
        unit=unit,
        city=fuzzy_city(city),
        province=province,
        postal=repair_postal(postal or "") or None,
    )
    query = norm.geocode_query or text
    normalized = {
        "street": norm.street,
        "unit": norm.unit,
        "city": norm.city,
        "postal": norm.postal,
        "query": query,
        "issues": list(norm.issues),
    }
    if not query.strip():
        return ResolveResult(STATUS_FAILED, [], 0.0, None, query, ["empty"], normalized)

    def rank(pool: list[Candidate]) -> tuple[str, list[Candidate], list[str]]:
        return classify(list(pool), typed_city=norm.city, typed_postal=norm.postal)

    cands, photon_confident = _photon(query)
    status, ranked, reasons = rank(cands)
    if not (photon_confident and status == STATUS_CONFIDENT):
        cands = cands + _nominatim(query)
        status, ranked, reasons = rank(cands)
    if allow_google and status in {STATUS_FAILED, STATUS_APPROXIMATE}:
        extra = _google(query)
        if extra:
            status, ranked, reasons = rank(cands + extra)

    best = ranked[0] if ranked else None
    return ResolveResult(
        status=status,
        candidates=ranked,
        confidence=best.score if best else 0.0,
        source=best.source if best else None,
        query=query,
        reasons=reasons,
        normalized=normalized,
    )

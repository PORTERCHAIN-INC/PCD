"""Deterministic address cleaning for route import (unit/suite hygiene for Nominatim)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_UNIT_PATTERNS = [
    re.compile(
        r"^(?P<unit>(?:unit|suite|apt|apartment|floor|fl|#)\s*[\w\-]+)\s*[-,]?\s*(?P<rest>.+)$",
        re.I,
    ),
    re.compile(
        r"^(?P<rest>.+?)[,\s]+(?P<unit>(?:unit|suite|apt|apartment|floor|fl|#)\s*[\w\-]+)\s*$",
        re.I,
    ),
    # street + unit + city/province tail: "100 King St W Unit 1200, Toronto, ON"
    re.compile(
        r"^(?P<rest>.+?)\s+(?P<unit>(?:unit|suite|apt|apartment|floor|fl|#)\s*[\w\-]+)\s*,\s*(?P<tail>.+)$",
        re.I,
    ),
    re.compile(r"^(?P<unit>\d+)\s*[-–]\s*(?P<rest>\d+\s+.+)$"),
]

_POSTAL_CA = re.compile(
    r"\b([ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z])\s?(\d[ABCEGHJ-NPRSTV-Z]\d)\b",
    re.I,
)

_ABBREV = (
    (re.compile(r"\bSt\.?\b", re.I), "Street"),
    (re.compile(r"\bAve\.?\b", re.I), "Avenue"),
    (re.compile(r"\bRd\.?\b", re.I), "Road"),
    (re.compile(r"\bBlvd\.?\b", re.I), "Boulevard"),
    (re.compile(r"\bDr\.?\b", re.I), "Drive"),
)

# Longest-first so "richmond hill" wins over "richmond".
_ON_CITIES = tuple(
    sorted(
        (
            "richmond hill",
            "niagara falls",
            "st catharines",
            "st. catharines",
            "north york",
            "east york",
            "scarborough",
            "etobicoke",
            "mississauga",
            "brampton",
            "vaughan",
            "markham",
            "oakville",
            "burlington",
            "hamilton",
            "toronto",
            "ottawa",
            "london",
            "kitchener",
            "waterloo",
            "cambridge",
            "guelph",
            "windsor",
            "oshawa",
            "ajax",
            "pickering",
            "milton",
            "newmarket",
            "aurora",
            "barrie",
            "kingston",
            "sudbury",
            "thunder bay",
            "whitby",
            "orillia",
            "peterborough",
        ),
        key=len,
        reverse=True,
    )
)


@dataclass(frozen=True)
class NormalizedAddress:
    raw: str
    street: str
    unit: str | None
    city: str | None
    province: str | None
    postal: str | None
    geocode_query: str
    issues: tuple[str, ...] = ()


def _space_postal(text: str) -> str:
    def _fix(m: re.Match[str]) -> str:
        return f"{m.group(1).upper()} {m.group(2).upper()}"

    return _POSTAL_CA.sub(_fix, text)


def _extract_unit(text: str) -> tuple[str, str | None]:
    cleaned = " ".join(text.split()).strip(" ,")
    for pat in _UNIT_PATTERNS:
        m = pat.match(cleaned)
        if not m:
            continue
        unit = m.group("unit").strip(" ,#")
        rest = m.group("rest").strip(" ,")
        if "tail" in m.groupdict() and m.group("tail"):
            rest = f"{rest}, {m.group('tail').strip(' ,')}"
        if unit.lower().startswith("#"):
            unit = unit[1:].strip()
        return rest, unit
    return cleaned, None


def _extract_city(street: str) -> tuple[str, str | None]:
    """Pull a known Ontario city out of a freeform one-cell address."""
    for city in _ON_CITIES:
        # Word boundary so "ton" does not match inside "eton".
        pat = re.compile(rf"(^|[\s,]){re.escape(city)}([\s,]|$)", re.I)
        m = pat.search(street)
        if not m:
            continue
        before = street[: m.start()].strip(" ,")
        after = street[m.end() :].strip(" ,")
        rest = ", ".join(p for p in (before, after) if p)
        display = " ".join(w.capitalize() for w in city.replace(".", "").split())
        return rest or street, display
    return street, None


def normalize_address(
    raw: str,
    *,
    unit: str | None = None,
    city: str | None = None,
    province: str | None = None,
    postal: str | None = None,
) -> NormalizedAddress:
    raw_s = (raw or "").strip()
    issues: list[str] = []
    if not raw_s:
        return NormalizedAddress(
            raw=raw_s,
            street="",
            unit=unit,
            city=city,
            province=province,
            postal=postal,
            geocode_query="",
            issues=("address.incomplete",),
        )

    street, extracted_unit = _extract_unit(raw_s)
    unit_final = (unit or "").strip() or extracted_unit
    street = _space_postal(street)
    for pat, repl in _ABBREV:
        street = pat.sub(repl, street)
    street = " ".join(street.split()).strip(" ,")

    postal_final = (postal or "").strip() or None
    if postal_final:
        postal_final = _space_postal(postal_final)
    else:
        m = _POSTAL_CA.search(street)
        if m:
            postal_final = f"{m.group(1).upper()} {m.group(2).upper()}"
            # Keep the civic line clean for Nominatim.
            street = (street[: m.start()] + street[m.end() :]).strip(" ,")

    city_final = (city or "").strip() or None
    if not city_final:
        street, city_final = _extract_city(street)
    province_final = (province or "").strip() or "ON"

    parts = [street]
    if city_final:
        parts.append(city_final)
    if province_final:
        parts.append(province_final)
    if postal_final:
        parts.append(postal_final)
    if "ontario" not in " ".join(parts).lower() and "canada" not in " ".join(parts).lower():
        parts.append("Canada")

    geocode_query = ", ".join(p for p in parts if p)
    if not street:
        issues.append("address.incomplete")
    if postal_final and not _POSTAL_CA.search(postal_final.replace(" ", "")):
        # already spaced; validate loosely
        if not re.match(
            r"^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\s?\d[ABCEGHJ-NPRSTV-Z]\d$",
            postal_final,
            re.I,
        ):
            issues.append("address.postal_invalid")

    return NormalizedAddress(
        raw=raw_s,
        street=street,
        unit=unit_final,
        city=city_final,
        province=province_final,
        postal=postal_final,
        geocode_query=geocode_query,
        issues=tuple(issues),
    )


def compose_raw_from_parts(row: dict[str, Any]) -> str:
    """Build a single address string from mapped row fields."""
    if row.get("address"):
        return str(row["address"]).strip()
    bits = [
        row.get("street"),
        row.get("city"),
        row.get("province") or row.get("state"),
        row.get("postal") or row.get("postal_code") or row.get("zip"),
    ]
    return ", ".join(str(b).strip() for b in bits if b and str(b).strip())

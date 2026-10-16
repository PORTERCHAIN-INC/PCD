"""Address-text helpers for /v1/geo search (units, house numbers, postal codes)."""

from __future__ import annotations

import re

STREET_VALUES = {
    "residential",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "service",
    "living_street",
    "trunk",
    "primary_link",
    "secondary_link",
    "tertiary_link",
    "road",
}
POSTAL_RE = re.compile(r"^\s*([A-Za-z]\d[A-Za-z])\s*-?\s*(\d[A-Za-z]\d)\s*$")
HOUSE_RE = re.compile(r"^\s*(\d+[A-Za-z]?)\s+\S")
UNIT_PREFIX_RE = re.compile(
    r"^\s*(?:(?:unit|suite|ste|apt|apartment|#)\s*[\w-]+\s*[,-]?\s*|\w{1,5}\s*-\s*(?=\d))",
    re.IGNORECASE,
)
UNIT_SUFFIX_RE = re.compile(
    r"\s*,?\s*(?:unit|suite|ste|apt|#)\s*[\w-]+\s*(?=,|$)", re.IGNORECASE
)


def strip_unit(q: str) -> str:
    """'12-345 Main St' / 'Unit 5, 345 Main St' / '345 Main St Unit 5' -> '345 Main St'.

    Canadian style is UNIT-HOUSE; Photon has no unit data, so search on the building.
    """
    out = UNIT_SUFFIX_RE.sub("", UNIT_PREFIX_RE.sub("", q, count=1))
    return out.strip() or q


def normalize_postal(q: str) -> str | None:
    """'l9t8w7' / 'L9T-8W7' -> 'L9T 8W7'; None when q is not a full Canadian postal code."""
    m = POSTAL_RE.match(q)
    return f"{m.group(1)} {m.group(2)}".upper() if m else None


def typed_house_number(q: str) -> str | None:
    m = HOUSE_RE.match(q)
    return m.group(1) if m else None


def relaxed_queries(q: str, is_postal: bool) -> list[str]:
    """Photon needs every word to match. When the full text finds nothing (a city name
    OSM files differently, e.g. North York vs Toronto), retry without trailing words,
    keeping at least the house number and two street words. At most 3 calls."""
    words = q.replace(",", " ").split()
    tries = [q]
    if not is_postal:
        for cut in (1, 2):
            if len(words) - cut >= 3:
                tries.append(" ".join(words[:-cut]))
    return tries

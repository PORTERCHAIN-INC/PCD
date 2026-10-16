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


# --- street short forms, typed city, Toronto districts -------------------------------

_SHORT = {
    "ave": "avenue",
    "av": "avenue",
    "st": "street",
    "rd": "road",
    "dr": "drive",
    "blvd": "boulevard",
    "cres": "crescent",
    "cr": "crescent",
    "ct": "court",
    "crt": "court",
    "pkwy": "parkway",
    "hwy": "highway",
    "ln": "lane",
    "pl": "place",
    "sq": "square",
    "terr": "terrace",
    "ter": "terrace",
    "cir": "circle",
    "trl": "trail",
    "gt": "gate",
    "gdns": "gardens",
    "hts": "heights",
    "pt": "point",
    "wy": "way",
    "cv": "cove",
}
_DIRS = {"w": "west", "e": "east", "n": "north", "s": "south"}
STREET_TYPES = set(_SHORT.values()) | {
    "way",
    "street",
    "road",
    "line",
    "sideroad",
    "concession",
}

# Former Toronto municipalities (Photon: city=Toronto, district=<name>) and
# common community names that live inside a city.
TORONTO_DISTRICTS = {"north york", "scarborough", "etobicoke", "york", "east york"}
COMMUNITY_TO_CITY = {
    "concord": "vaughan",
    "maple": "vaughan",
    "woodbridge": "vaughan",
    "kleinburg": "vaughan",
    "thornhill": "vaughan|markham",
    "unionville": "markham",
    "streetsville": "mississauga",
    "port credit": "mississauga",
    "bolton": "caledon",
    "georgetown": "halton hills",
    "acton": "halton hills",
    "stouffville": "whitchurch-stouffville",
    **{d: "toronto" for d in TORONTO_DISTRICTS},
}
KNOWN_CITIES = {
    "toronto",
    "vaughan",
    "markham",
    "richmond hill",
    "mississauga",
    "brampton",
    "milton",
    "oakville",
    "burlington",
    "hamilton",
    "pickering",
    "ajax",
    "whitby",
    "oshawa",
    "newmarket",
    "aurora",
    "caledon",
    "halton hills",
    "king",
    "barrie",
    "guelph",
    "kitchener",
    "waterloo",
    "cambridge",
    "st. catharines",
    "niagara falls",
    "clarington",
    "whitchurch-stouffville",
    "east gwillimbury",
    "georgina",
    "uxbridge",
    "scugog",
} | set(COMMUNITY_TO_CITY)


def expand_short_forms(q: str) -> str:
    """'1880 Steeles Ave W' -> '1880 Steeles Avenue West' (Photon matches whole words)."""
    words = q.replace(",", " , ").split()
    out: list[str] = []
    for i, w in enumerate(words):
        lw = w.lower().rstrip(".")
        prev = out[-1].lower() if out else ""
        nxt = words[i + 1].lower().rstrip(".") if i + 1 < len(words) else ""
        if lw in ("st", "st") and nxt and nxt not in _DIRS and nxt != ",":
            out.append(w)  # "St Clair", "St. George": Saint, not Street
        elif lw in _SHORT and i > 0:
            out.append(_SHORT[lw].title())
        elif lw in _DIRS and (prev in STREET_TYPES or prev in {"avenue", "street"}):
            out.append(_DIRS[lw].title())
        else:
            out.append(w)
    return " ".join(out).replace(" , ", ", ").strip(" ,")


def split_city(q: str) -> tuple[str, str | None]:
    """'1880 Steeles Avenue West North York' -> ('1880 Steeles Avenue West', 'north york')."""
    # A trailing postal code ("..., Toronto M6N 4Y5") is not part of the street or city.
    q = re.sub(r"(?:,|\s)\s*[A-Z]\d[A-Z](?:\s*\d[A-Z]\d)?\s*$", "", q.strip(), flags=re.IGNORECASE)
    q = re.sub(r"(?:,|\s)\s*canada\.?\s*$", "", q.strip(), flags=re.IGNORECASE)
    q = re.sub(r"(?:,|\s)\s*[A-Z]\d[A-Z](?:\s*\d[A-Z]\d)?\s*$", "", q.strip(), flags=re.IGNORECASE)
    base = re.sub(
        r"(?:,|\s)\s*(?:on|ontario)\.?\s*$", "", q.strip(), flags=re.IGNORECASE
    )
    low = base.lower().rstrip(" ,")
    for city in sorted(KNOWN_CITIES, key=len, reverse=True):
        if low.endswith((" " + city, "," + city)):
            head = base[: len(low) - len(city)].rstrip(" ,")
            if head and re.search(r"[a-z]", head, re.IGNORECASE):
                return head, city
    return base.rstrip(" ,"), None


def city_matches(typed: str | None, props: dict) -> bool:
    if not typed:
        return True
    city = (
        props.get("city") or props.get("town") or props.get("village") or ""
    ).lower()
    district = (props.get("district") or "").lower()
    county = (props.get("county") or "").lower()
    if typed in TORONTO_DISTRICTS:
        return city == "toronto" and (not district or district == typed)
    targets = COMMUNITY_TO_CITY.get(typed, typed).split("|")
    return any(t in (city, district, county) or (t and t in city) for t in targets) or (
        typed == district
    )


def street_core(s: str | None) -> str:
    """Normalized street name for comparisons: 'Steeles Ave. W' == 'steeles avenue west'."""
    return expand_short_forms(s or "").lower().replace(".", "").strip()


def lead_city_last(q: str) -> str:
    """'Milton 8500 Mount Pleasant Way' -> '8500 Mount Pleasant Way Milton'."""
    low = q.lower()
    for city in sorted(KNOWN_CITIES, key=len, reverse=True):
        rest = q[len(city) :].lstrip(" ,")
        if low.startswith(city) and rest[:1].isdigit():
            return f"{rest} {q[: len(city)]}"
    return q

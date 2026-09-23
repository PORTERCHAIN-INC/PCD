"""Synonym-based column mapping with confidence scores."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

CANONICAL_FIELDS = (
    "pickup_address",
    "dropoff_address",
    "address",
    "unit",
    "city",
    "province",
    "postal",
    "stop_type",
    "sequence",
    "contact_name",
    "contact_phone",
    "external_ref",
    "lat",
    "lng",
    "notes",
    "sku",
    "length",
    "width",
    "height",
    "dimensions_unit",
    "weight",
    "weight_unit",
    "quantity",
)

_SYNONYMS: dict[str, tuple[str, ...]] = {
    "pickup_address": (
        "pickup_address",
        "pickup",
        "pick_up_address",
        "pickup_location",
        "ship_from",
        "origin",
        "origin_address",
        "from_address",
    ),
    "dropoff_address": (
        "dropoff_address",
        "dropoff",
        "drop_off_address",
        "drop_address",
        "dropoff_location",
        "delivery_address",
        "destination_address",
        "to_address",
    ),
    "address": (
        "address",
        "street",
        "location",
        "ship_to",
        "dest",
        "destination",
        "full_address",
        "addr",
    ),
    "unit": ("unit", "suite", "apt", "apartment", "floor", "unit_number"),
    "city": ("city", "town", "municipality"),
    "province": ("province", "state", "region"),
    "postal": ("postal", "postal_code", "zip", "zipcode", "postcode"),
    "stop_type": ("stop_type", "type", "kind", "pickup_drop", "stop"),
    "sequence": ("sequence", "seq", "order", "stop_no", "stop_number", "route_order", "#"),
    "contact_name": ("contact_name", "name", "contact", "recipient", "consignee", "customer"),
    "contact_phone": ("contact_phone", "phone", "mobile", "tel", "telephone"),
    "external_ref": ("external_ref", "ref", "po", "order_id", "invoice", "barcode", "reference"),
    "lat": ("lat", "latitude"),
    "lng": ("lng", "lon", "longitude", "long"),
    "notes": ("notes", "instructions", "comments", "special_instructions"),
    "sku": ("sku", "item", "item_sku", "product", "product_sku"),
    "length": ("length", "l", "dim_length"),
    "width": ("width", "w", "dim_width"),
    "height": ("height", "h", "dim_height"),
    "dimensions_unit": ("dimensions_unit", "dimension_unit", "size_unit", "dim_unit"),
    "weight": ("weight", "parcel_weight", "item_weight"),
    "weight_unit": ("weight_unit", "weight_uom", "mass_unit"),
    "quantity": ("quantity", "qty", "parcel_qty", "count"),
}


@dataclass
class FieldMapping:
    canonical: str
    source: str | None
    confidence: float
    evidence: str


def _score(header: str, synonym: str) -> float:
    h = _norm_header(header)
    s = synonym.lower()
    if h == s:
        return 1.0
    if h.replace("_", "") == s.replace("_", ""):
        return 0.98
    if s in h or h in s:
        return 0.9
    return SequenceMatcher(None, h, s).ratio()


PAIR_FIELDS = ("pickup_address", "dropoff_address")

# Pickup/dropoff need an exact header: a fuzzy hit ("pickup_date", "address")
# would steal the column a one-address sheet needs.
_PAIR_MIN_SCORE = 0.98


def _exact_claims(headers: list[str]) -> dict[str, str]:
    """Header → the field it names exactly, so a fuzzy earlier field cannot take it
    ("order_id" is the merchant reference, not the stop sequence)."""
    claims: dict[str, str] = {}
    for h in headers:
        for canonical in CANONICAL_FIELDS:
            if any(_score(h, syn) >= _PAIR_MIN_SCORE for syn in _SYNONYMS[canonical]):
                claims[h] = canonical
                break
    return claims


def suggest_mapping(headers: list[str]) -> list[FieldMapping]:
    used: set[str] = set()
    results: list[FieldMapping] = []
    claims = _exact_claims(headers)
    for canonical in CANONICAL_FIELDS:
        best_h: str | None = None
        best_score = 0.0
        best_syn = ""
        for h in headers:
            if h in used or claims.get(h, canonical) != canonical:
                continue
            for syn in _SYNONYMS[canonical]:
                sc = _score(h, syn)
                if sc > best_score:
                    best_score = sc
                    best_h = h
                    best_syn = syn
        threshold = _PAIR_MIN_SCORE if canonical in PAIR_FIELDS else 0.72
        if best_h and best_score >= threshold:
            used.add(best_h)
            results.append(
                FieldMapping(
                    canonical=canonical,
                    source=best_h,
                    confidence=round(best_score, 3),
                    evidence=f"matched synonym '{best_syn}'",
                )
            )
        else:
            results.append(
                FieldMapping(
                    canonical=canonical,
                    source=None,
                    confidence=0.0,
                    evidence="unmapped",
                )
            )
    return _fold_lone_pair_column(results)


def _fold_lone_pair_column(results: list[FieldMapping]) -> list[FieldMapping]:
    """One of pickup/dropoff alone is a one-address sheet: that column is ``address``."""
    by_c = {m.canonical: m for m in results}
    mapped = [by_c[c] for c in PAIR_FIELDS if by_c[c].source]
    if len(mapped) != 1:
        return results
    lone = mapped[0]
    address = by_c["address"]
    if not address.source:
        address.source = lone.source
        address.confidence = lone.confidence
        address.evidence = f"{lone.evidence} (single address column)"
    lone.source = None
    lone.confidence = 0.0
    lone.evidence = "unmapped"
    return results


def apply_mapping(
    rows: list[dict[str, Any]],
    mapping: list[FieldMapping] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pairs: list[tuple[str, str]] = []
    for m in mapping:
        if isinstance(m, FieldMapping):
            if m.source:
                pairs.append((m.canonical, m.source))
        elif m.get("source") and m.get("canonical"):
            pairs.append((str(m["canonical"]), str(m["source"])))

    out: list[dict[str, Any]] = []
    for row in rows:
        mapped: dict[str, Any] = {}
        for canonical, source in pairs:
            value = _row_get(row, source)
            if value not in (None, ""):
                mapped[canonical] = value
        out.append(mapped)
    return out


def _norm_header(value: str) -> str:
    return str(value).lower().strip().replace(" ", "_").replace("-", "_")


def _row_get(row: dict[str, Any], source: str) -> Any:
    if source in row:
        return row[source]
    want = _norm_header(source)
    for key, value in row.items():
        if _norm_header(str(key)) == want:
            return value
    return None


def adapt_mapping_to_headers(
    mapping: list[FieldMapping] | list[dict[str, Any]],
    headers: list[str],
) -> list[dict[str, Any]]:
    """Replay a saved mapping onto this file's headers (case-insensitive)."""
    lookup = {_norm_header(str(h)): h for h in headers if h}
    adapted: list[dict[str, Any]] = []
    for item in mapping:
        if isinstance(item, FieldMapping):
            canonical = item.canonical
            source = item.source
        else:
            canonical = str(item.get("canonical") or "")
            source = item.get("source")
        if not canonical:
            continue
        matched = lookup.get(_norm_header(str(source))) if source else None
        adapted.append(
            {
                "canonical": canonical,
                "source": matched,
                "confidence": 1.0 if matched else 0.0,
                "evidence": "saved mapping" if matched else "saved mapping — column missing",
            }
        )
    return adapted


def mapping_to_dicts(mapping: list[FieldMapping]) -> list[dict[str, Any]]:
    return [
        {
            "canonical": m.canonical,
            "source": m.source,
            "confidence": m.confidence,
            "evidence": m.evidence,
        }
        for m in mapping
    ]


def mapping_confidence_ok(mapping: list[FieldMapping] | list[dict[str, Any]], *, threshold: float = 0.8) -> bool:
    """Either one ``address`` column, or both a pickup and a dropoff address column."""
    confident: set[str] = set()
    for m in mapping:
        if isinstance(m, FieldMapping):
            canonical, source, confidence = m.canonical, m.source, m.confidence
        else:
            canonical = str(m.get("canonical") or "")
            source = m.get("source")
            confidence = float(m.get("confidence") or 0)
        if source and confidence >= threshold:
            confident.add(canonical)
    return "address" in confident or all(c in confident for c in PAIR_FIELDS)

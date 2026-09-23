"""
Flat rates keyed on forward sortation area.

An FSA is the first three characters of a Canadian postal code — "M5V 2T6" is
in M5V. Merchants that ship from one warehouse think in these terms ("$18 to
anywhere in L4W"), and Shopify hands us the buyer's postal code on every order,
so this is the natural rate model for that channel.
"""

from __future__ import annotations

import re

from porterchain_pricing.components.quote import ComponentQuote, _item
from porterchain_pricing.gta_rate import vehicle_classes_match
from porterchain_pricing.types import FsaRateRecord, GeoPoint


def _vehicle_match(stored: str | None, requested: str | None) -> bool:
    return vehicle_classes_match(stored, requested)

COMPONENT = "fsa_rate"

#: Canadian FSA: letter, digit, letter. Deliberately not anchored to the end so
#: it also matches inside a formatted address line.
_FSA_RE = re.compile(r"\b([A-Za-z]\d[A-Za-z])\s*\d?[A-Za-z]?\d?\b")

#: Postal districts covering Ontario.
ONTARIO_FSA_PREFIXES = frozenset({"K", "L", "M", "N", "P"})


def normalize_fsa(value: str | None) -> str:
    """Uppercase three-character FSA, or empty when the input has none."""
    if not value:
        return ""
    candidate = value.strip().upper().replace(" ", "")
    if len(candidate) >= 3 and re.fullmatch(r"[A-Z]\d[A-Z]", candidate[:3]):
        return candidate[:3]
    return ""


def fsa_from_point(point: GeoPoint | None) -> str:
    """
    FSA for a stop: the explicit postal code when we have one, otherwise
    whatever can be recovered from the formatted address.
    """
    if point is None:
        return ""
    explicit = normalize_fsa(getattr(point, "postal", "") or "")
    if explicit:
        return explicit
    match = _FSA_RE.search(point.formatted or "")
    return normalize_fsa(match.group(1)) if match else ""


def is_ontario_fsa(fsa: str) -> bool:
    return bool(fsa) and fsa[0] in ONTARIO_FSA_PREFIXES


class FsaRateService:
    """Selects the most specific FSA rate for a delivery."""

    def select(
        self,
        rates: list[FsaRateRecord],
        *,
        dest_fsa: str,
        origin_fsa: str = "",
        merchant_id: str | None = None,
        vehicle_class: str | None = None,
    ) -> FsaRateRecord | None:
        dest = normalize_fsa(dest_fsa)
        if not dest:
            return None
        origin = normalize_fsa(origin_fsa)

        matches = [
            r
            for r in rates
            if r.is_active
            and normalize_fsa(r.dest_fsa) == dest
            # A blank filter on the row means "any", so it always matches.
            and (not r.merchant_id or r.merchant_id == merchant_id)
            and (not r.origin_fsa or normalize_fsa(r.origin_fsa) == origin)
            and (not r.vehicle_class or _vehicle_match(r.vehicle_class, vehicle_class))
        ]
        if not matches:
            return None
        # Most specific wins; cheapest breaks a tie so a merchant is never
        # penalised by two equally-specific rows.
        return sorted(matches, key=lambda r: (-r.specificity(), r.flat_cents))[0]

    def quote(
        self,
        rates: list[FsaRateRecord],
        *,
        pickup: GeoPoint | None = None,
        dropoff: GeoPoint | None = None,
        dest_fsa: str = "",
        origin_fsa: str = "",
        merchant_id: str | None = None,
        vehicle_class: str | None = None,
    ) -> ComponentQuote:
        origin = normalize_fsa(origin_fsa) or fsa_from_point(pickup)
        dest = normalize_fsa(dest_fsa) or fsa_from_point(dropoff)

        metadata = {"origin_fsa": origin, "dest_fsa": dest, "matched": False}
        if not dest:
            metadata["reason"] = "no_destination_fsa"
            return ComponentQuote(component=COMPONENT, metadata=metadata)

        rate = self.select(
            rates,
            dest_fsa=dest,
            origin_fsa=origin,
            merchant_id=merchant_id,
            vehicle_class=vehicle_class,
        )
        if rate is None:
            metadata["reason"] = "no_matching_rate"
            return ComponentQuote(component=COMPONENT, metadata=metadata)

        label = rate.label or (f"{origin} to {dest} flat rate" if origin else f"Flat rate to {dest}")
        metadata.update(
            {
                "matched": True,
                "rate_id": rate.id,
                "specificity": rate.specificity(),
                "includes_location_fees": rate.includes_location_fees,
                "merchant_scoped": bool(rate.merchant_id),
            }
        )
        return ComponentQuote(
            component=COMPONENT,
            items=_item("fsa_rate", label, rate.flat_cents),
            metadata=metadata,
        )

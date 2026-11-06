"""Shopify shipping-address review: never book a Shopify order on a silent guess.

Before booking, the shipping address runs through the shared ``geo_resolve`` brain.
``ambiguous`` (2+ GTA areas) or ``failed`` -> the order is held with reason
``address_needs_review``; the merchant picks a candidate (same AddressDisambiguationModal
as bulk import) and books it from the Shopify orders list.

Shopify-supplied coordinates are trusted (Shopify geocoded the checkout address).
Kill switch: ``GEO_RESOLVE_SHOPIFY=0`` restores the old geocode-and-book behaviour.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from porterchain_api.integrations.shopify_orders import format_shopify_address

logger = logging.getLogger(__name__)

HOLD_REASON = "address_needs_review"
HOLD_STATUSES = frozenset({"ambiguous", "failed"})


def review_enabled() -> bool:
    flag = (os.environ.get("GEO_RESOLVE_SHOPIFY", "1") or "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _has_coords(address: dict[str, Any]) -> bool:
    try:
        return (
            address.get("latitude") is not None
            and address.get("longitude") is not None
            and (
                float(address["latitude"]) != 0.0 or float(address["longitude"]) != 0.0
            )
        )
    except (TypeError, ValueError):
        return False


def resolve_shipping(address: dict[str, Any]) -> dict[str, Any]:
    """Run geo_resolve on a Shopify shipping address. Returns ResolveResult.to_dict()."""
    from porterchain_api.geo_resolve import resolve_address

    street = str(address.get("address1") or "").strip()
    res = resolve_address(
        street or format_shopify_address(address),
        unit=(str(address.get("address2") or "").strip() or None),
        city=(str(address.get("city") or "").strip() or None),
        province=(
            str(
                address.get("province_code")
                or address.get("provinceCode")
                or address.get("province")
                or ""
            ).strip()
            or None
        ),
        postal=(str(address.get("zip") or "").strip() or None),
    )
    return res.to_dict()


def needs_review(address: dict[str, Any]) -> dict[str, Any] | None:
    """The resolver result when this address must be held, else None (book as before)."""
    if not review_enabled() or not address or _has_coords(address):
        return None
    try:
        res = resolve_shipping(address)
    except Exception:
        logger.exception("shopify_address_review_failed")
        return None
    return res if res.get("status") in HOLD_STATUSES else None


def apply_choice(payload: dict[str, Any], *, lat: float, lng: float) -> dict[str, Any]:
    """Pin the merchant-picked point on the shipping address so booking skips review."""
    out = dict(payload)
    addr = dict(out.get("shipping_address") or {})
    addr["latitude"], addr["longitude"] = float(lat), float(lng)
    out["shipping_address"] = addr
    return out

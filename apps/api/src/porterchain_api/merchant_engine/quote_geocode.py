"""Server-side coordinates for typed merchant addresses (Kaylulu 2026-10-15).

When Places autocomplete fails in the browser (or the merchant never picks a suggestion) the
quote arrives with ``formatted`` but no lat/lng. Geocode it here: Nominatim first, then the
FSA centroid from the postal code. Never raises; unresolved addresses keep lat/lng None so
``validate_addresses`` still reports ``coordinates_required``.
"""

from __future__ import annotations

import logging

from porterchain_api.schemas_merchant import AddressInput

log = logging.getLogger(__name__)


def resolve_coordinates(addr: AddressInput | None) -> None:
    if addr is None or (addr.lat is not None and addr.lng is not None):
        return
    text = (addr.formatted or "").strip()
    if not text:
        return
    try:
        from porterchain_api.merchant_engine.import_geocode import geocode_stop

        geo = geocode_stop(address=text, postal=addr.postal, province="ON")
        if geo.lat is not None and geo.lng is not None:
            addr.lat, addr.lng = float(geo.lat), float(geo.lng)
            if not addr.postal and getattr(geo, "postal", None):
                addr.postal = geo.postal
            log.info("merchant_quote_server_geocode source=nominatim status=%s", geo.status)
            return
    except Exception as exc:  # noqa: BLE001 - geocoder must never break the quote path
        log.warning("merchant_quote_server_geocode nominatim_error=%s", exc)
    try:
        from porterchain_api.customer_fast.geo import with_coords

        hit = with_coords({"formatted": text, "postal": addr.postal})
        if hit and hit.get("lat") is not None and hit.get("lng") is not None:
            addr.lat, addr.lng = float(hit["lat"]), float(hit["lng"])
            log.info("merchant_quote_server_geocode source=fsa")
    except Exception as exc:  # noqa: BLE001
        log.warning("merchant_quote_server_geocode fsa_error=%s", exc)


def resolve_missing_coordinates(*addrs: AddressInput | None) -> None:
    for addr in addrs:
        resolve_coordinates(addr)

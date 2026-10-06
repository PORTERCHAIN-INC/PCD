"""GTA ±150 km service-area gate for programmatic bookings.

Portal route import and Shopify / `/v1/merchant-api/bookings` must refuse stops
outside the Valhalla tile. Ontario district prefixes alone are too wide
(Ottawa K*, Sudbury P*).
"""

from __future__ import annotations

from porterchain_api.merchant_engine.booking_validation import BookingValidationError
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest
from porterchain_pricing.components.fsa import fsa_from_point, is_ontario_fsa, normalize_fsa
from porterchain_pricing.gta150_fsa import is_gta150_fsa
from porterchain_pricing.types import GeoPoint


def fsa_from_address(addr: AddressInput | None) -> str:
    if addr is None:
        return ""
    explicit = normalize_fsa(getattr(addr, "postal", None) or "")
    if explicit:
        return explicit
    return fsa_from_point(
        GeoPoint(
            lat=getattr(addr, "lat", None),
            lng=getattr(addr, "lng", None),
            formatted=addr.formatted or "",
            postal=getattr(addr, "postal", None) or "",
        )
    )


def service_area_error(label: str, addr: AddressInput | None) -> str | None:
    fsa = fsa_from_address(addr)
    if not fsa:
        return f"{label} needs an Ontario postal code (FSA starting with K, L, M, N, or P)."
    if not is_ontario_fsa(fsa):
        return f"{label} is outside Ontario service area ({fsa})."
    if not is_gta150_fsa(fsa):
        return (
            f"{label} is outside the PorterChain GTA ±150 km service tile ({fsa}). "
            "Request a quote for extended Ontario lanes."
        )
    return None


def assert_ontario_booking(body: MerchantBookDeliveryRequest) -> None:
    points: list[tuple[str, AddressInput]] = [("pickup", body.pickup), ("dropoff", body.dropoff)]
    for index, stop in enumerate(body.additional_stops or []):
        points.append((f"stop {index + 1}", stop))
    for label, addr in points:
        message = service_area_error(label, addr)
        if message:
            raise BookingValidationError("out_of_service_area", message)


def assert_ontario_stop(*, label: str, formatted: str | None, postal: str | None) -> str | None:
    """Return an error code for route-import rows, or None when the stop is in-area."""
    dummy = AddressInput(formatted=formatted or "", postal=postal)
    message = service_area_error(label, dummy)
    return "stop.out_of_service_area" if message else None

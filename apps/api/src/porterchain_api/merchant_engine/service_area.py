"""GTA ±150 km service-area gate for programmatic bookings.

Portal route import and Shopify / `/v1/merchant-api/bookings` must refuse stops
outside the Valhalla tile. Ontario district prefixes alone are too wide
(Ottawa K*, Sudbury P*).

An FSA-model merchant's own rate table defines where it can deliver, so its
destinations may also be any FSA that table prices (`merchant_coverage_fsas`).
Pickups always stay on the tile.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

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


def merchant_coverage_fsas(db: Session, merchant: Any) -> frozenset[str]:
    """
    Destination FSAs an FSA-model merchant may use beyond the GTA tile.

    A checked-in contract schedule is the whole answer when the merchant has
    one; otherwise every FSA with an active merchant-scoped rate row counts.
    Distance merchants get nothing extra.
    """
    from porterchain_pricing.contract_schedule import load_contract_schedule
    from porterchain_pricing.policy import MODEL_FSA, policy_from_config

    if merchant is None or getattr(merchant, "pricing_model", None) != MODEL_FSA:
        return frozenset()
    policy = policy_from_config(getattr(merchant, "pricing_config", None) or {})
    terms = load_contract_schedule(policy.schedule.contract_schedule)
    if terms is not None:
        return terms.coverage_fsas()
    from porterchain_api.admin_models import PricingFsaRate

    rows = (
        db.query(PricingFsaRate.dest_fsa)
        .filter(PricingFsaRate.merchant_id == merchant.id, PricingFsaRate.is_active.is_(True))
        .all()
    )
    return frozenset(code for code in (normalize_fsa(r[0]) for r in rows) if code)


def service_area_error(
    label: str, addr: AddressInput | None, extra_fsas: frozenset[str] = frozenset()
) -> str | None:
    fsa = fsa_from_address(addr)
    if not fsa:
        return f"{label} needs an Ontario postal code (FSA starting with K, L, M, N, or P)."
    if not is_ontario_fsa(fsa):
        return f"{label} is outside Ontario service area ({fsa})."
    if not is_gta150_fsa(fsa) and fsa not in extra_fsas:
        return (
            f"{label} is outside the PorterChain GTA ±150 km service tile ({fsa}). "
            "Request a quote for extended Ontario lanes."
        )
    return None


def assert_ontario_booking(
    body: MerchantBookDeliveryRequest, *, extra_fsas: frozenset[str] = frozenset()
) -> None:
    """Pickup on the tile; dropoff and stops on the tile or in `extra_fsas`."""
    points: list[tuple[str, AddressInput, frozenset[str]]] = [
        ("pickup", body.pickup, frozenset()),
        ("dropoff", body.dropoff, extra_fsas),
    ]
    for index, stop in enumerate(body.additional_stops or []):
        points.append((f"stop {index + 1}", stop, extra_fsas))
    for label, addr, extra in points:
        message = service_area_error(label, addr, extra)
        if message:
            raise BookingValidationError("out_of_service_area", message)


def assert_ontario_stop(*, label: str, formatted: str | None, postal: str | None) -> str | None:
    """Return an error code for route-import rows, or None when the stop is in-area."""
    dummy = AddressInput(formatted=formatted or "", postal=postal)
    message = service_area_error(label, dummy)
    return "stop.out_of_service_area" if message else None

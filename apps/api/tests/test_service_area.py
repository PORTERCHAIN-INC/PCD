"""Ontario service-area gate for programmatic bookings."""

from datetime import UTC, datetime

from porterchain_api.merchant_engine.booking_validation import BookingValidationError
from porterchain_api.merchant_engine.service_area import (
    assert_ontario_booking,
    fsa_from_address,
)
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def _addr(**kwargs) -> AddressInput:
    base = dict(formatted="1 King St W, Toronto, ON", lat=43.65, lng=-79.38)
    base.update(kwargs)
    return AddressInput(**base)


def _body(*, pickup=None, dropoff=None) -> MerchantBookDeliveryRequest:
    return MerchantBookDeliveryRequest(
        pickup=pickup or _addr(postal="M5V 2T6"),
        dropoff=dropoff or _addr(formatted="100 Queen St W, Toronto", postal="M5H 2N2"),
        scheduled_at=datetime.now(UTC),
    )


def test_fsa_from_explicit_postal() -> None:
    assert fsa_from_address(_addr(postal="m5v 2t6")) == "M5V"


def test_fsa_from_formatted_when_postal_missing() -> None:
    assert fsa_from_address(AddressInput(formatted="1 King St W, Toronto, ON M5V 2T6")) == "M5V"


def test_ontario_booking_is_allowed() -> None:
    assert_ontario_booking(_body())


def test_vancouver_dropoff_is_rejected() -> None:
    try:
        assert_ontario_booking(_body(dropoff=_addr(formatted="Vancouver", postal="V6B 1A1")))
    except BookingValidationError as exc:
        assert exc.code == "out_of_service_area"
        return
    raise AssertionError("expected out_of_service_area")


def test_missing_postal_is_rejected() -> None:
    try:
        assert_ontario_booking(_body(dropoff=AddressInput(formatted="Somewhere without a code")))
    except BookingValidationError as exc:
        assert exc.code == "out_of_service_area"
        return
    raise AssertionError("expected out_of_service_area")

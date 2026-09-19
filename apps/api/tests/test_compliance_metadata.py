"""Compliance metadata helpers (§8.1.2 · §8.1.9)."""

from datetime import UTC, datetime

from porterchain_api.booking_engine.compliance_metadata import (
    append_temperature_reading,
    build_compliance_metadata,
    is_temperature_excursion,
    otp_required_at_delivery,
    requires_medical_certified,
)
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def _addr() -> AddressInput:
    return AddressInput(formatted="123 Main St Toronto ON")


def test_medical_chain_of_custody_metadata():
    body = MerchantBookDeliveryRequest(
        pickup=_addr(),
        dropoff=_addr(),
        package_type="medical",
        scheduled_at=datetime.now(UTC),
        custodian_name="Dr. Lee",
        specimen_id="SP-9912",
        seal_number="SEAL-44",
    )
    meta = build_compliance_metadata(body)
    assert meta is not None
    assert requires_medical_certified(meta)
    assert meta["chain_of_custody"]["specimen_id"] == "SP-9912"


def test_food_cold_chain_and_window():
    start = datetime(2026, 7, 9, 10, 0, tzinfo=UTC)
    end = datetime(2026, 7, 9, 14, 0, tzinfo=UTC)
    body = MerchantBookDeliveryRequest(
        pickup=_addr(),
        dropoff=_addr(),
        package_type="foodBeverage",
        scheduled_at=datetime.now(UTC),
        requires_cold_chain=True,
        temperature_min_c=2,
        temperature_max_c=8,
        delivery_window_start=start,
        delivery_window_end=end,
    )
    meta = build_compliance_metadata(body)
    assert meta["cold_chain"]["required"] is True
    assert meta["delivery_window"]["end"] == end.isoformat()


def test_otp_required_defaults_off_until_merchant_opts_in():
    assert otp_required_at_delivery(None) is False
    assert otp_required_at_delivery({}) is False
    body = MerchantBookDeliveryRequest(
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    assert otp_required_at_delivery(build_compliance_metadata(body)) is False

    opted = MerchantBookDeliveryRequest(
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
        otp_required=True,
    )
    meta = build_compliance_metadata(opted)
    assert meta is not None
    assert meta["proof"]["otp_required"] is True
    assert otp_required_at_delivery(meta) is True


def test_temperature_excursion_detection():
    meta = {"cold_chain": {"required": True, "min_c": 2, "max_c": 8, "readings": []}}
    assert is_temperature_excursion(meta, 9.5) is True
    assert is_temperature_excursion(meta, 5.0) is False
    updated = append_temperature_reading(meta, celsius=5.0, recorded_at=datetime.now(UTC))
    assert len(updated["cold_chain"]["readings"]) == 1

"""Fleetbase requires phone — synthetic E.164 when seed drivers omit it."""

from porterchain_fleetbase_adapter.mappers import build_driver_payload


def test_build_driver_payload_synthesizes_phone() -> None:
    body = build_driver_payload(
        {"id": "26b1897c-ed59-4674-a7bb-35b5d49a974b", "full_name": "Driver", "email": "a@b.c"}
    )
    assert body["phone"].startswith("+1555")
    assert body["meta"]["porterchain_phone_synthetic"] is True


def test_build_driver_payload_keeps_real_phone() -> None:
    body = build_driver_payload(
        {"id": "x", "full_name": "D", "phone": "+14165550100", "email": "a@b.c"}
    )
    assert body["phone"] == "+14165550100"
    assert "porterchain_phone_synthetic" not in body["meta"]

"""COI 2026-11-04 limits drive claim caps (Lloyd's B5000191409)."""
from datetime import date

from porterchain_pricing import declared_value as DV
from porterchain_pricing import insurance_policy as P


def test_limits_match_certificate():
    assert P.CGL["each_occurrence_cents"] == 200_000_000
    assert P.CGL["general_aggregate_cents"] == 200_000_000
    assert P.CGL["personal_and_advertising_injury_cents"] == 100_000_000
    assert P.CGL["tenants_legal_liability_cents"] == 25_000_000
    assert P.CGL["medical_payments_cents"] == 1_500_000
    assert P.CARGO == {"motor_truck_cargo_cents": 5_000_000, "target_commodities_cents": 2_500_000,
                       "towing_storage_debris_removal_cents": 1_000_000}
    assert P.DEDUCTIBLE_CENTS == 250_000
    assert P.summary()["non_owned_auto"] is False


def test_in_force_window():
    assert not P.in_force(date(2026, 11, 4))
    assert P.in_force(date(2026, 11, 5))
    assert not P.in_force(date(2027, 11, 5))


def test_shipment_cap_never_above_cargo_limit():
    out = DV.shipment_claim_cap_cents([250_000] * 30)
    assert out["cap_cents"] == 5_000_000 and out["capped"]
    out = DV.shipment_claim_cap_cents([250_000] * 30, ["parcel", "Electronics"])
    assert out["cap_cents"] == 2_500_000 and out["target_commodity"]
    assert DV.shipment_claim_cap_cents([1_000, 2_000])["cap_cents"] == 3_000


def test_deductible_recovery():
    assert P.insurer_recoverable_cents(200_000) == 0
    assert P.insurer_recoverable_cents(1_000_000) == 750_000

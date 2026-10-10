"""PorterChain universal conditions of carriage (global ``carriage_terms``), contract-overridable (B2–B5, C03, C07, C13, C15)."""

from __future__ import annotations

from datetime import date

from porterchain_pricing.contract_schedule import load_contract_schedule
from porterchain_pricing.contract_terms import (
    claim_deadline,
    concierge_cents,
    declaration_problem,
    failed_delivery_cents,
    missing_claim_records,
    terms_of,
    waiting_cents,
)
from porterchain_pricing.policy import policy_from_config
from porterchain_pricing.types import PricingContext
from test_contract_schedule import SCHEDULE_ID, _ctx, _price

T = terms_of(load_contract_schedule(SCHEDULE_ID))  # Kaylulu inherits the global terms


def test_b2_waiting_not_pooled_15_min_blocks():
    assert waiting_cents(T, pickup_minutes=45, stop_minutes=[15])["total_cents"] == 0
    # pickup 50 min → 5 over → one 15-min block = $7.50; stop 31 min → 16 over → two blocks = $15
    w = waiting_cents(T, pickup_minutes=50, stop_minutes=[31, 10])
    assert [x["cents"] for x in w["lines"]] == [750, 1500] and w["total_cents"] == 2250
    # unused pickup allowance never offsets a stop
    assert waiting_cents(T, pickup_minutes=0, stop_minutes=[30])["total_cents"] == 750


def test_b3_return_fee_examples():
    assert (
        failed_delivery_cents(T, vehicle="van", stop_rate_cents=3000) == 1500
    )  # $30 + $15 = $45
    assert (
        failed_delivery_cents(T, vehicle="van", stop_rate_cents=4500) == 2250
    )  # $45 + $22.50
    assert (
        failed_delivery_cents(T, vehicle="van", stop_rate_cents=6000) == 3000
    )  # $60 + $30
    assert failed_delivery_cents(T, vehicle="compact", stop_rate_cents=600) == 1500
    assert failed_delivery_cents(T, vehicle="compact", stop_rate_cents=1000) == 1500
    assert T["failed_delivery"]["route_minimum_on_return"] is False
    assert T["failed_delivery"]["handling_in_pct"] is False


def test_b4_contract_coverage_overrides_platform_default():
    b = _price(["L5M", "M5V"])
    cov = b.metadata["coverage"]
    assert (
        cov["covered_up_to_cents"] == 100000
        and cov["covered_per"] == "route"
        and cov["charge_cents"] == 0
    )
    up = _price(["L5M", "M5V"], coverage_upgrade=True)
    assert up.metadata["coverage"]["covered_up_to_cents"] == 2_500_000
    assert (
        up.subtotal_cents == 12000 + 2 * 1000
    )  # +$10 per stop on top of the route minimum


def test_b5_claims_window_and_records():
    assert claim_deadline(T, date(2026, 10, 9)) == date(
        2026, 10, 16
    )  # Fri + 5 business days
    assert missing_claim_records(T, ["order_reference", "damage_photos"]) == [
        "issue_description",
        "proof_of_value",
        "delivery_information",
        "pod_documentation",
    ]


def test_c03_concierge_past_designated_point():
    assert concierge_cents(T, "lobby") == 0
    b = _price(["L5M", "M5V", "L5N"], delivery_point="past_designated_point")
    assert any(
        i.code == "past_designated_point" and i.amount_cents == 3000 for i in b.items
    )


def test_c07_liftgate_not_blocked_globally_but_a_contract_can_turn_it_off():
    assert (
        _price(["L5M"], requires_liftgate=True).metadata.get("custom_quote") is not True
    )
    cfg = {
        "pricing_model": "fsa",
        "surcharges": {"downtown": False, "upper_zone": False},
        "schedule": {
            "fsa_miss": "refuse",
            "contract_schedule": SCHEDULE_ID,
            "contract_overrides": {"terms": {"liftgate_available": False}},
        },
    }
    ctx = PricingContext(
        merchant_policy=policy_from_config(cfg), merchant_pricing_config=cfg
    )
    b = _price(["L5M"], ctx=ctx, requires_liftgate=True)
    assert (
        b.metadata["custom_quote"] is True
        and b.metadata["custom_quote_reason"] == "liftgate_not_available"
    )


def test_global_carriage_terms_setting_is_editable():
    edited = {"concierge": {"past_designated_point_cents": 4000}}
    b = _price(
        ["L5M"], ctx=_ctx(carriage_terms=edited), delivery_point="past_designated_point"
    )
    assert any(
        i.code == "past_designated_point" and i.amount_cents == 4000 for i in b.items
    )


def test_c13_c15_declarations():
    assert (
        declaration_problem(T, dangerous_goods=True, prohibited=[])
        == "dangerous_goods_need_approval"
    )
    assert (
        declaration_problem(T, dangerous_goods=False, prohibited=["cannabis"])
        == "prohibited_article"
    )
    assert declaration_problem(T, dangerous_goods=False, prohibited=[]) is None


def test_d4_and_rural_still_custom_quote():
    assert _price(["K9H"]).metadata["custom_quote"] is True
    assert _price(["N0B"]).metadata["custom_quote"] is True


def test_per_merchant_overrides_edit_rates_and_terms():
    cfg = {
        "pricing_model": "fsa",
        "surcharges": {"downtown": False, "upper_zone": False},
        "schedule": {
            "fsa_miss": "refuse",
            "fuel_surcharge_percent": 0,
            "contract_schedule": SCHEDULE_ID,
            "contract_overrides": {
                "van": {
                    "pickup_cents": 5000,
                    "tiers": [{"code": "T1", "route_minimum_cents": 13000}],
                },
                "terms": {"waiting": {"cents_per_hour": 3600}},
            },
        },
    }
    ctx = PricingContext(
        merchant_policy=policy_from_config(cfg), merchant_pricing_config=cfg
    )
    assert _price(["L5M", "M5V"], ctx=ctx).subtotal_cents == 13000
    four = _price(["L5M", "M5V", "L5N", "L5A"], ctx=ctx)  # 50 + 4×30 = 170 > 130
    assert four.subtotal_cents == 17000
    # untouched Kaylulu default unaffected
    assert _price(["L5M", "M5V"], ctx=_ctx()).subtotal_cents == 12000

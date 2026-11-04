"""Declared-value cover (Ravi 2026-10-29): 1.5%, $3 min, $2,500 max/parcel, exclusions, proof, $4.41/kg, off (G-INS)."""
import pytest
from test_contract_schedule import _price

from porterchain_pricing import declared_value as DV
from porterchain_pricing.standard_card import STANDARD_V1_LINES, Item, quote

CONFIRMED = {"confirmed": True, "insurer": "Test Insurer", "policy_ref": "POL-TEST-1"}
ON = DV.rules({"enabled": True}, CONFIRMED)


def test_rates_and_minimum():
    assert DV.cover_cents(10_000) == 300  # $100 -> $1.50 -> $3 min
    assert DV.cover_cents(20_000) == 300  # $200 -> exactly $3
    assert DV.cover_cents(100_000) == 1500  # $1,000 -> $15
    assert DV.cover_cents(250_000) == 3750  # $2,500 -> $37.50
    assert DV.cover_cents(33_333) == 500  # $333.33 * 1.5% = $4.99995 -> $5.00 (half-up)


def test_problems():
    assert DV.problems(100_000) == ["declared_value_cover_unavailable"]  # flag off by default (G-INS)
    assert DV.problems(100_000, r=ON) == []
    assert DV.problems(250_001, r=ON) == ["declared_value_over_max"]
    assert DV.problems(0, r=ON) == ["declared_value_required"]
    for cat in ("cash", "Jewelry", "jewellery", "medicines", "pharmacy", "perishables", "food", "gift card"):
        assert "declared_value_excluded_goods" in DV.problems(10_000, cat, ON), cat
    assert DV.problems(10_000, "electronics", ON) == []


def test_claim_cap():
    assert DV.claim_cap_cents(10, covered=False) == {"cap_cents": 4410, "basis": "default_liability_per_kg"}
    assert DV.claim_cap_cents(10, covered=True, declared_value_cents=200_000)["basis"] == "proof_of_value_missing"
    got = DV.claim_cap_cents(10, covered=True, declared_value_cents=200_000, proof_of_value=True)
    assert got == {"cap_cents": 200_000, "basis": "declared_value_cover"}
    assert DV.claim_cap_cents(10, covered=True, declared_value_cents=900_000, proof_of_value=True)["cap_cents"] == 250_000
    assert DV.claim_cap_cents(2, covered=True, declared_value_cents=50_000, proof_of_value=True,
                              category="jewellery")["basis"] == "excluded_goods"


def test_standard_card_off_then_on():
    item = [Item(weight_kg=5, length_cm=40, width_cm=30, height_cm=20)]
    assert quote(item, "Z1")["declared_value"] is None
    assert STANDARD_V1_LINES["declared_value"]["enabled"] is False
    with pytest.raises(ValueError, match="declared_value_cover_unavailable"):
        quote(item, "Z1", declared_values=[100_000])
    lines = {**STANDARD_V1_LINES, "declared_value": {**STANDARD_V1_LINES["declared_value"], "enabled": True}}
    with pytest.raises(ValueError, match="declared_value_cover_unavailable"):  # G-INS: card flag alone isn't enough
        quote(item, "Z1", lines=lines, declared_values=[100_000])
    base = quote(item, "Z1", lines=lines)
    q = quote(item, "Z1", lines=lines, declared_values=[100_000, 10_000], cargo_insurance=CONFIRMED)
    assert q["subtotal_cents"] == base["subtotal_cents"] + 1500 + 300
    assert q["declared_value"]["proof_of_value_required"] is True
    with pytest.raises(ValueError, match="declared_value_over_max"):
        quote(item, "Z1", lines=lines, declared_values=[300_000], cargo_insurance=CONFIRMED)
    with pytest.raises(ValueError, match="declared_value_excluded_goods"):
        quote(item, "Z1", lines=lines, declared_values=[10_000], declared_categories=["perishables"],
              cargo_insurance=CONFIRMED)


def test_engine_path_when_enabled():
    from test_contract_schedule import _ctx
    ctx = _ctx()
    ctx.coverage = {"enabled": True}
    ctx.cargo_insurance = CONFIRMED
    b = _price(["L5M"], parcel_count=2, coverage_upgrade=True, declared_value_cents=200_000, ctx=ctx)
    cov = b.metadata["coverage"]
    assert cov["tier"] == "declared_value" and cov["charge_cents"] == 2 * 1500 and cov["proof_of_value_required"]
    over = _price(["L5M"], parcel_count=1, coverage_upgrade=True, declared_value_cents=260_000, ctx=ctx)
    assert over.metadata["coverage"]["over_max"] and over.metadata["coverage"]["charge_cents"] == 0


# --- G-INS gate (Ravi 2026-10-29): only a confirmed cargo_insurance setting can turn cover on ---------------

def test_cargo_insurance_normalizer():
    assert DV.normalize_cargo_insurance(None)["confirmed"] is False
    with pytest.raises(ValueError, match="cargo_insurance_needs_insurer_and_policy_ref"):
        DV.normalize_cargo_insurance({"confirmed": True})
    assert DV.normalize_cargo_insurance(CONFIRMED)["confirmed"] is True
    assert DV.insurance_confirmed({"confirmed": True}) is False  # incomplete -> not confirmed


def test_setting_alone_cannot_enable():
    from test_contract_schedule import _ctx
    ctx = _ctx()
    ctx.coverage = {"enabled": True}
    for ins in (None, {"confirmed": False}, {"confirmed": True}):  # missing / off / incomplete
        ctx.cargo_insurance = ins
        b = _price(["L5M"], parcel_count=1, coverage_upgrade=True, declared_value_cents=100_000, ctx=ctx)
        cov = b.metadata["coverage"]
        assert cov["enabled"] is False and cov["charge_cents"] == 0
        assert cov["unavailable"] == ["declared_value_cover_unavailable"]


def test_forged_flag_in_setting_cannot_enable():
    from porterchain_pricing.coverage import normalize_coverage
    assert normalize_coverage({"enabled": True, "insurance_confirmed": True})["enabled"] is False
    assert DV.problems(100_000, r={"enabled": True, "insurance_confirmed": True}) == ["declared_value_cover_unavailable"]


def test_contract_override_cannot_enable_without_insurance():
    from test_contract_schedule import _ctx
    over = {"schedule": {"contract_overrides": {"terms": {"coverage": {"enabled": True}}}}}
    ctx = _ctx(merchant_pricing_config=over)
    b = _price(["L5M"], parcel_count=1, coverage_upgrade=True, declared_value_cents=100_000, ctx=ctx)
    assert b.metadata["coverage"]["enabled"] is False and b.metadata["coverage"]["charge_cents"] == 0
    ctx.cargo_insurance = CONFIRMED
    b = _price(["L5M"], parcel_count=1, coverage_upgrade=True, declared_value_cents=100_000, ctx=ctx)
    assert b.metadata["coverage"]["enabled"] is True and b.metadata["coverage"]["charge_cents"] == 1500


def test_hst_applies_to_cover_fee():
    """Ravi 2026-10-29: the cover fee is part of the taxable supply (13% ON HST, with the subtotal)."""
    item = [Item(weight_kg=5, length_cm=40, width_cm=30, height_cm=20)]
    lines = {**STANDARD_V1_LINES, "declared_value": {**STANDARD_V1_LINES["declared_value"], "enabled": True}}
    base = quote(item, "Z1", lines=lines)
    q = quote(item, "Z1", lines=lines, declared_values=[100_000], cargo_insurance=CONFIRMED)
    assert q["subtotal_cents"] - base["subtotal_cents"] == 1500
    assert q["hst_cents"] - base["hst_cents"] in (195, 194, 196)  # 13% of $15, rounding of the whole subtotal

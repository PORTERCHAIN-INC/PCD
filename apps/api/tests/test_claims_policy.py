"""Claims handled per the cargo policy (COI B5000191409) and O. Reg. 643/05."""
import pytest

from porterchain_api.support_engine import claims_policy as CP
from porterchain_api.support_engine import claims_templates as T


def test_notice_window_delivered_60_days():
    w = CP.notice_window(claim_type="damaged_parcel", shipped_on="2026-11-01", delivered_on="2026-11-02",
                         notice_on="2027-01-01")
    assert w["deadline"] == "2027-01-01" and w["within_time"] is True
    late = CP.notice_window(claim_type="damaged_parcel", shipped_on="2026-11-01", delivered_on="2026-11-02",
                            notice_on="2027-01-02")
    assert late["within_time"] is False


def test_notice_window_non_delivery_9_months():
    w = CP.notice_window(claim_type="lost_parcel", shipped_on="2026-11-05", delivered_on=None,
                         notice_on="2027-08-05")
    assert w["deadline"] == "2027-08-05" and w["within_time"] is True


def test_evidence_checklist():
    s = CP.evidence_status([{"type": "photo"}, {"type": "invoice"}], {"written_notice": True})
    assert s["missing"] == ["proof_of_delivery"] and not s["complete"]


def test_shipment_cap_never_above_policy():
    big = [{"weight_kg": 1, "covered": True, "declared_value_cents": 250_000, "proof_of_value": True}] * 30
    assert CP.liability_ceiling(big)["cap_cents"] == 5_000_000


def test_insurer_step_deductible_borne_by_porterchain():
    s = CP.insurer_step(400_000, 5_000_000)
    assert s["notify_broker"] and s["deductible_borne_by"] == "PorterChain"
    assert s["recoverable_after_deductible_cents"] == 150_000
    assert not CP.insurer_step(200_000, 5_000_000)["notify_broker"]


@pytest.mark.parametrize(
    "kw,err",
    [
        ({"investigated": False}, "investigation_required_before_decision"),
        ({"investigated": True, "amount_cents": 5_000_001, "goodwill_reason": "x"},
         "compensation_exceeds_cargo_insurance_limit"),
        ({"investigated": True, "amount_cents": 10_000}, "compensation_exceeds_liability_cap_needs_goodwill_reason"),
        ({"investigated": True, "amount_cents": 100, "merchant_liability_cents": 250_000},
         "merchant_charge_needs_fault_reason_deductible_never_charged"),
    ],
)
def test_check_compensation_guards(kw, err):
    amount = kw.pop("amount_cents", 100)
    with pytest.raises(ValueError, match=err):
        CP.check_compensation(amount, 441, **kw)


def _a():
    return {"evidence": CP.evidence_status([]), "liability": CP.liability_ceiling([{"weight_kg": 2}])}


def test_letters_make_no_admission_and_cite_terms():
    ack = T.acknowledgement("CLM-1", "PC-1", _a())
    assert "not an admission of liability" in ack["body"] and "O. Reg. 643/05" in ack["body"]
    assert "Proof of delivery" in ack["body"]
    ok = T.decision_approved("CLM-1", "PC-1", 882, _a())
    assert "$4.41 per kg" in ok["body"] and "No deductible" in ok["body"]
    no = T.decision_denied("CLM-1", "PC-1", "notice_out_of_time")
    assert "Uniform Conditions" in no["body"]
    with pytest.raises(ValueError):
        T.decision_denied("CLM-1", "PC-1", "made_up")


def test_broker_notice_is_a_draft():
    n = T.broker_notice("CLM-1", "PC-1", _a(), claimed_cents=400_000, loss_date="2026-11-10", description="Fell")
    assert "B5000191409" in n["body"] and "not admitted liability" in n["body"]
    assert "to be confirmed" in n["to"]


def test_driver_certificate_file_ships_with_api():
    from porterchain_api.routers.driver import shift

    assert shift._COI_PDF.is_file() and shift._COI_PDF.read_bytes()[:5] == b"%PDF-"

from types import SimpleNamespace

import pytest
from porterchain_api.billing_engine.dunning import draft_for
from porterchain_api.billing_engine.interac.matcher import MatchProposal, score
from porterchain_pricing.margin import normalize_margin_estimates


def test_confidence_levels():
    assert (
        score(
            MatchProposal(invoice_id="i", method="reference", note="exact")
        ).confidence
        == 0.99
    )
    assert (
        score(
            MatchProposal(invoice_id="i", method="sender_amount", note="exact")
        ).confidence
        >= 0.9
    )
    assert (
        score(
            MatchProposal(invoice_id="i", method="amount_only", note="exact")
        ).confidence
        < 0.9
    )
    assert score(MatchProposal(note="unmatched")).confidence == 0.0


def test_dunning_draft_is_text_only():
    m = SimpleNamespace(id="m1", company_name="Acme", profile={}, email="x@acme.test")
    d = draft_for(m, 12345, 1, 20000)
    assert (
        d["tone"] == "friendly" and "$123.45" in d["subject"] and "Interac" in d["body"]
    )
    assert draft_for(m, 300000, 3, 300000)["tone"] == "firm"


def test_margin_estimates_validate():
    assert normalize_margin_estimates(None)["avg_speed_kmh"] == 40.0
    assert (
        normalize_margin_estimates({"vehicle_cents_per_km": 50})["vehicle_cents_per_km"]
        == 50
    )
    with pytest.raises(ValueError):
        normalize_margin_estimates({"deadhead_factor": 3})

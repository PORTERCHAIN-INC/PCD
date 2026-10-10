"""Predictive lead score blend + heuristic fallback."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_api.collaboration_engine.lead_scoring import (
    MIN_SAMPLES,
    ScorePriors,
    blend_scores,
    clear_score_priors_cache,
    predictive_score,
    score_breakdown,
)
from porterchain_api.collaboration_engine.crm_leads import CrmLeadsMixin


def _lead(**kwargs):
    base = dict(
        email="a@b.co",
        phone="+15551212",
        company_name="Acme",
        primary_contact_name="Pat",
        channel="website",
        intent_type="merchant",
        source="website_business",
        estimated_deliveries_per_month=100,
        estimated_revenue_cents=2_000_000,
        current_logistics_provider="Other",
        priority="high",
        custom_fields={},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_blend_falls_back_without_predictive():
    assert blend_scores(80, None) == 80
    assert blend_scores(120, None) == 100


def test_blend_weights():
    # 0.65*80 + 0.35*40 = 52+14 = 66
    assert blend_scores(80, 40.0) == 66


def test_predictive_uses_priors():
    priors = ScorePriors(
        by_channel={"website": 0.8},
        by_intent={"merchant": 0.7},
        by_source={"website_business": 0.6},
        global_rate=0.5,
        sample_n=MIN_SAMPLES,
    )
    lead = _lead()
    score = predictive_score(lead, priors)
    assert 50 <= score <= 100


def test_score_breakdown_heuristic_when_priors_thin():
    clear_score_priors_cache()
    lead = _lead()
    # Attach as CrmLead-like for score_lead path via breakdown only
    thin = ScorePriors(sample_n=5)
    out = score_breakdown(lead, 55, priors=thin)  # type: ignore[arg-type]
    assert out["method"] == "heuristic"
    assert out["final"] == 55
    assert out["predictive"] is None


def test_score_breakdown_blend_when_ready():
    clear_score_priors_cache()
    priors = ScorePriors(
        by_channel={"website": 0.9},
        by_intent={"merchant": 0.8},
        by_source={"website_business": 0.7},
        global_rate=0.5,
        sample_n=MIN_SAMPLES + 5,
    )
    lead = _lead(custom_fields={})
    out = score_breakdown(lead, 40, priors=priors)  # type: ignore[arg-type]
    assert out["method"] == "blend"
    assert out["predictive"] is not None
    assert out["final"] != 40 or out["predictive"] == 40


def test_crm_score_lead_writes_breakdown():
    clear_score_priors_cache()
    lead = _lead(
        estimated_deliveries_per_month=0,
        estimated_revenue_cents=0,
        current_logistics_provider=None,
        priority="low",
        phone=None,
        custom_fields={},
    )
    # Minimal CrmLead duck — score_lead mutates custom_fields
    class L:
        pass

    obj = L()
    for k, v in lead.__dict__.items():
        setattr(obj, k, v)
    score = CrmLeadsMixin.score_lead(obj)  # type: ignore[arg-type]
    assert 0 <= score <= 100
    assert isinstance(obj.custom_fields, dict)
    assert obj.custom_fields.get("_score", {}).get("method") == "fit-v1"
    assert obj.custom_fields["_score"]["reasons"]

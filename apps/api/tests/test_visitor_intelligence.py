"""Visitor intelligence scoring unit tests."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_api.collaboration_engine.crm_leads import CrmLeadsMixin
from porterchain_api.domain.visitor_intent import behavioral_score_boost, compute_intent_score


def test_compute_intent_score_quote_path() -> None:
    score = compute_intent_score(
        signals={
            "intent": "quote",
            "guide_stage": "book",
            "page_view_count": 5,
            "paths": ["/en", "/en/business", "/en/sign-up"],
            "from_page": "home-hero",
        },
        quote_generated=True,
        touch_count=4,
        has_utm=True,
    )
    assert score >= 80
    assert score <= 100


def test_compute_intent_score_cold_visit() -> None:
    score = compute_intent_score(
        signals={"page_view_count": 1, "paths": ["/en"]},
        quote_generated=False,
        touch_count=1,
        has_utm=False,
    )
    assert 0 <= score <= 20


def test_behavioral_boost_guide_lead() -> None:
    lead = SimpleNamespace(
        custom_fields={
            "form": "capacity_guide",
            "intent": "meeting",
            "transcript": [{"role": "user"}, {"role": "assistant"}, {"role": "user"}],
            "appointment": {"start": "2026-08-12T15:00:00Z"},
        }
    )
    boost = behavioral_score_boost(lead, None)
    assert boost >= 30


def test_score_lead_fuses_behavior() -> None:
    lead = SimpleNamespace(
        estimated_deliveries_per_month=60,
        estimated_revenue_cents=0,
        current_logistics_provider=None,
        phone="4165550100",
        email="ops@example.com",
        priority="high",
        custom_fields={"form": "capacity_guide", "intent": "quote", "transcript": []},
        channel=None,
        intent_type=None,
        source=None,
        company_name=None,
        primary_contact_name=None,
    )
    visitor = SimpleNamespace(intent_score=80, quote_generated=True)
    score = CrmLeadsMixin.score_lead(lead, visitor)  # type: ignore[arg-type]
    assert score >= 55
    assert score <= 100

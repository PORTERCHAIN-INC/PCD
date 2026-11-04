"""Doc 78 acceptance (rules part): SLA, spam flags, rules score, convert → organisation, flags off."""

from __future__ import annotations

import uuid

import porterchain_api.main  # noqa: F401  (registers all models)
from datetime import datetime
from zoneinfo import ZoneInfo

from porterchain_api.collaboration_engine import lead_rules as r
from porterchain_api.collaboration_engine.crm_service import CrmSalesService as CrmLeadWriteService
from porterchain_api.crm_models import CrmLead
from porterchain_api.marketing_site.config import default_marketing_site
from porterchain_api.org_engine.models import Organisation

T = ZoneInfo("America/Toronto")


def test_sla_business_hours():
    day = datetime(2026, 10, 29, 10, 0, tzinfo=T)
    night = datetime(2026, 10, 29, 22, 0, tzinfo=T)
    assert (r.sla_due_at(day) - day).total_seconds() == 3600
    assert (r.sla_due_at(night) - night).total_seconds() == 4 * 3600
    assert r.sla_state(day, day.replace(minute=30)) == "ok"
    assert r.sla_state(day, day.replace(minute=46)) == "amber"
    assert r.sla_state(day, day.replace(hour=11, minute=1)) == "red"
    assert r.sla_state(day, day, responded_at=day.replace(minute=20)) == "met"


def test_spam_flags_never_need_captcha():
    assert r.spam_flags(honeypot="x") == ["honeypot"]
    assert "too_fast" in r.spam_flags(fill_ms=1500)
    assert "disposable_email" in r.spam_flags(email="a@mailinator.com")
    assert "many_links" in r.spam_flags(message="http://a http://b www.c.com")
    assert r.spam_flags(fill_ms=9000, email="ravi@shop.ca", message="Need 40 deliveries a week") == []
    assert default_marketing_site()["calculator"]["min_fill_seconds"] == 3


def test_rules_score_bands_and_reasons():
    hot = r.rules_score(business_type="shopify_merchant", in_service_area=True, monthly_volume=300,
                        email="ops@shop.ca", phone="+14165550100", name="Ada", replied=True)
    assert hot["band"] == "hot" and hot["reasons"]
    cold = r.rules_score(business_type="retail_customer", in_service_area=False, email="a@mailinator.com", spam=["disposable_email"])
    assert cold["band"] == "cold" and cold["score"] == 0


def test_convert_creates_organisation(db):
    lead = CrmLead(company_name=f"Bakery {uuid.uuid4().hex[:6]}", email="hi@bakery.ca", business_type="small_shop",
                   source="website", status="new", tags=[], consent={}, custom_fields={})
    db.add(lead)
    db.commit()
    out = CrmLeadWriteService().convert_lead(db, None, lead.id, create_deal=False)
    assert out["org_id"]
    org = db.get(Organisation, out["org_id"])
    assert org.business_type == "small_shop" and not org.needs_review
    db.refresh(lead)
    assert lead.custom_fields["org_id"] == org.id
    again = CrmLeadWriteService().convert_lead(db, None, lead.id, create_deal=False)
    assert again["org_id"] == org.id


def test_whatsapp_cloud_and_capi_off_by_default():
    from porterchain_api.config import Settings

    s = Settings()
    for name in ("whatsapp_cloud_enabled", "lead_capi_enabled", "meta_capi_enabled"):
        if hasattr(s, name):
            assert getattr(s, name) in (False, None, ""), name

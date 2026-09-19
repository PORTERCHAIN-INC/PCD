"""P2 social adapters + territory + referral credit."""

from __future__ import annotations

import uuid

from porterchain_api.collaboration_engine.lead_channel_adapters import (
    event_from_linkedin_lead,
    event_from_x_lead,
    event_from_youtube_lead,
)
from porterchain_api.collaboration_engine.lead_ops import (
    grant_referral_credit,
    resolve_territory_assignee,
)
from porterchain_api.config import Settings
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LeadSourceChannel


def test_linkedin_x_youtube_parsers() -> None:
    li = event_from_linkedin_lead(
        {
            "email": "ops@li.test",
            "firstName": "Li",
            "lastName": "User",
            "companyName": "Li Co",
            "id": "li-1",
            "personUrn": "urn:li:person:abc",
        }
    )
    assert li.channel == LeadSourceChannel.LINKEDIN.value
    assert li.external_ids.get("linkedin_urn") == "urn:li:person:abc"

    x = event_from_x_lead({"email": "a@x.test", "username": "porter", "id": "x1", "text": "hi"})
    assert x.channel == LeadSourceChannel.TWITTER.value
    assert x.message == "hi"

    yt = event_from_youtube_lead(
        {"email": "y@t.test", "comment": "Need vans", "video_id": "v1", "id": "c1"}
    )
    assert yt.channel == LeadSourceChannel.YOUTUBE.value
    assert yt.message == "Need vans"


def test_territory_resolve() -> None:
    settings = Settings(lead_territory_map_json='{"ON":"admin-on","GTA":"admin-gta","DEFAULT":"admin-default"}')
    lead = CrmLead(company_name="T", service_area="GTA Peel", address={"province": "ON"})
    assert resolve_territory_assignee(lead, settings) in ("admin-gta", "admin-on")
    lead2 = CrmLead(company_name="U", service_area="Somewhere", address={})
    assert resolve_territory_assignee(lead2, settings) == "admin-default"


def test_referral_credit_idempotent(db) -> None:
    lead = CrmLead(
        company_name=f"Ref {uuid.uuid4().hex[:6]}",
        email=f"ref-{uuid.uuid4().hex[:6]}@t.test",
        referred_by_merchant_id="merchant-ref-1",
        source="merchant_referral",
        channel="merchant_referral",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    settings = Settings(referral_credit_cents=12345)
    a = grant_referral_credit(db, lead=lead, company_id="co-1", settings=settings)
    db.commit()
    b = grant_referral_credit(db, lead=lead, company_id="co-1", settings=settings)
    assert a is not None and b is not None
    assert a.id == b.id
    assert a.amount_cents == 12345

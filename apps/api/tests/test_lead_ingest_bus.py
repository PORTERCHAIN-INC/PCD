"""Lead ingest bus — identity normalize + merge."""

from __future__ import annotations

import uuid

from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
    normalize_email,
    normalize_phone_e164,
)
from porterchain_api.crm_models import CrmLead, CrmLeadIdentity
from porterchain_api.domain.crm_states import (
    LeadIdentityKind,
    LeadSourceChannel,
    channel_for_source,
)


def test_normalize_phone_nanp() -> None:
    assert normalize_phone_e164("(416) 555-1212") == "+14165551212"
    assert normalize_phone_e164("+1 416 555 1212") == "+14165551212"
    assert normalize_phone_e164("12") is None
    assert normalize_email("  A@B.COM ") == "a@b.com"


def test_channel_for_source_taxonomy() -> None:
    assert channel_for_source("website_quote") == LeadSourceChannel.WEBSITE.value
    assert channel_for_source("whatsapp") == LeadSourceChannel.WHATSAPP.value
    assert channel_for_source("merchant_referral") == LeadSourceChannel.MERCHANT_REFERRAL.value


def test_ingest_merges_by_email(db) -> None:
    svc = LeadIngestService()
    suffix = uuid.uuid4().hex[:8]
    email = f"ada-{suffix}@acme.test"
    phone = f"+1416{int(suffix, 16) % 10_000_000:07d}"
    company = f"Acme Logistics {suffix}"
    first = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="website",
            source="website_contact",
            provider="test",
            external_event_id=f"evt-1-{suffix}",
            company_name=company,
            primary_contact_name="Ada",
            email=email,
            phone=phone,
            message="Need capacity in GTA",
        ),
    )
    assert first.created is True
    second = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="whatsapp",
            source="whatsapp",
            provider="test",
            external_event_id=f"evt-2-{suffix}",
            company_name=company,
            email=email,
            phone=phone,
            message="Follow-up on WhatsApp",
        ),
    )
    assert second.created is False
    assert second.merged is True
    assert second.lead.id == first.lead.id
    assert db.query(CrmLead).filter(CrmLead.email == email).count() == 1
    kinds = {
        r.kind
        for r in db.query(CrmLeadIdentity).filter(CrmLeadIdentity.lead_id == first.lead.id).all()
    }
    assert LeadIdentityKind.EMAIL.value in kinds
    assert LeadIdentityKind.PHONE_E164.value in kinds


def test_ingest_idempotent_event(db) -> None:
    svc = LeadIngestService()
    suffix = uuid.uuid4().hex[:8]
    email = f"call-{suffix}@test.example"
    evt = f"same-evt-{suffix}"
    phone = f"647555{int(suffix[:4], 16) % 10000:04d}"
    a = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="manual",
            source="phone_call",
            provider="test",
            external_event_id=evt,
            company_name=f"Call Lead {suffix}",
            email=email,
            phone=phone,
        ),
    )
    b = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="manual",
            source="phone_call",
            provider="test",
            external_event_id=evt,
            company_name=f"Call Lead {suffix}",
            email=email,
            phone=phone,
        ),
    )
    assert a.lead.id == b.lead.id
    assert b.created is False

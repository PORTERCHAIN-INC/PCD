"""Lead privacy, CASL unsubscribe, list pagination, growth StaffTopic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from porterchain_api.collaboration_engine.lead_consent import (
    apply_unsubscribe,
    casl_evidence,
    make_unsubscribe_token,
    verify_unsubscribe_token,
)
from porterchain_api.collaboration_engine.lead_ops import escalate_sla_breached_leads
from porterchain_api.collaboration_engine.lead_privacy import LeadPrivacyError, LeadPrivacyService
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LeadStatus
from porterchain_api.notification_engine.staff_fanout import roles_for_topic, staff_sentinel
from porterchain_api.platform.pagination import as_page, clamp_page
from porterchain_api.routers.public_inquiries import LeadUnsubscribeRequest, unsubscribe_lead


def test_casl_evidence_and_unsubscribe_token_roundtrip() -> None:
    bag = casl_evidence({"marketing": True, "sms": False}, source="website_inquiry")
    assert bag["marketing"] is True
    assert bag["sms"] is False
    assert bag["text_version"]
    assert bag["captured_at"]
    assert bag["source"] == "website_inquiry"
    assert bag["legal_basis"] == "consent"
    secret = "test-secret"
    token = make_unsubscribe_token(lead_id="lead-abc", secret=secret)
    assert verify_unsubscribe_token(token=token, secret=secret) == "lead-abc"
    assert verify_unsubscribe_token(token=token, secret="wrong") is None
    flipped = apply_unsubscribe(bag)
    assert flipped["marketing"] is False
    assert flipped["source"] == "unsubscribe"


def test_roles_for_topic_growth_maps_to_crm() -> None:
    roles = roles_for_topic("growth")
    assert "super_admin" in roles
    assert staff_sentinel("growth").startswith("__staff:growth")


def test_list_page_envelope_helpers() -> None:
    limit, offset = clamp_page(200, 10, default=50, max_limit=500)
    assert limit == 200
    assert offset == 10
    page = as_page([{"id": "1"}], total=3, limit=limit, offset=offset)
    assert page == {"items": [{"id": "1"}], "total": 3, "limit": 200, "offset": 10}


def test_lead_privacy_export_and_erase(db) -> None:
    lead = CrmLead(
        company_name=f"Priv {uuid.uuid4().hex[:6]}",
        email=f"p-{uuid.uuid4().hex[:6]}@t.test",
        phone="4165550100",
        primary_contact_name="Pat",
        source="website",
        channel="website",
        status=LeadStatus.NEW.value,
        consent={"marketing": True},
        custom_fields={"message": "hello", "api_key": "secret"},
    )
    db.add(lead)
    db.commit()
    svc = LeadPrivacyService()
    exported = svc.export_lead(db, lead)
    assert exported["lead"]["email"] == lead.email
    assert "api_key" not in exported["lead"]["custom_fields"]
    assert exported["ropa"]["primary_residency"] == "CA-ON"
    assert exported["ropa"]["multi_region"] is False
    assert any(a["activity"] == "lead_ingest" for a in exported["ropa"]["activities"])
    out = svc.erase_lead(db, lead, actor_user_id="admin-1")
    db.commit()
    db.refresh(lead)
    assert out["status"] == "erased"
    assert lead.email.endswith("@privacy.invalid")
    assert lead.consent == {}
    assert "privacy_erased" in (lead.tags or [])


def test_lead_privacy_erase_blocks_converted_with_company(db) -> None:
    lead = CrmLead(
        company_name=f"Conv {uuid.uuid4().hex[:6]}",
        email=f"c-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status=LeadStatus.CONVERTED.value,
        company_id=str(uuid.uuid4()),
    )
    db.add(lead)
    db.commit()
    with pytest.raises(LeadPrivacyError) as exc:
        LeadPrivacyService().erase_lead(db, lead, actor_user_id="admin-1")
    assert exc.value.code == "lead_converted_linked"


def test_unsubscribe_lead_route(db) -> None:
    lead = CrmLead(
        company_name=f"Unsub {uuid.uuid4().hex[:6]}",
        email=f"u-{uuid.uuid4().hex[:6]}@t.test",
        source="website_newsletter",
        channel="website",
        status=LeadStatus.NEW.value,
        consent={"marketing": True, "source": "website_inquiry"},
    )
    db.add(lead)
    db.commit()
    secret = "unit-unsub-secret"
    token = make_unsubscribe_token(lead_id=lead.id, secret=secret)

    class _S:
        jwt_secret = secret
        public_ingest_api_key = ""

    out = unsubscribe_lead(LeadUnsubscribeRequest(token=token), db=db, settings=_S())  # type: ignore[arg-type]
    assert out.status == "unsubscribed"
    db.refresh(lead)
    assert lead.consent.get("marketing") is False
    assert lead.consent.get("source") == "unsubscribe"
    from porterchain_api.collaboration_engine.lead_suppression import is_suppressed

    assert is_suppressed(db, email=lead.email) is True

    with pytest.raises(HTTPException):
        unsubscribe_lead(LeadUnsubscribeRequest(token="bad.token.here"), db=db, settings=_S())  # type: ignore[arg-type]


def test_escalate_sla_breached_leads(db) -> None:
    lead = CrmLead(
        company_name=f"SLA {uuid.uuid4().hex[:6]}",
        email=f"s-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status=LeadStatus.NEW.value,
        priority="high",
        sla_first_response_due_at=datetime.now(UTC) - timedelta(hours=2),
    )
    db.add(lead)
    db.commit()
    with patch(
        "porterchain_api.collaboration_engine.lead_ops._enqueue_growth_staff_alert"
    ) as mock_alert:
        result = escalate_sla_breached_leads(db, limit=10)
        assert result["due"] >= 1
        assert result["notified"] >= 1
        assert mock_alert.called
        kwargs = mock_alert.call_args.kwargs
        assert kwargs.get("kind") == "sla"


def test_suppression_blocks_nurture_and_merge_resurrection(db) -> None:
    from porterchain_api.collaboration_engine.lead_nurture import enqueue_nurture_intro_email
    from porterchain_api.collaboration_engine.lead_suppression import (
        is_suppressed,
        merge_consent_safe,
        upsert_suppression,
    )
    from porterchain_api.collaboration_engine.lead_consent import casl_evidence

    email = f"dnc-{uuid.uuid4().hex[:6]}@t.test"
    lead = CrmLead(
        company_name=f"DNC {uuid.uuid4().hex[:6]}",
        email=email,
        source="website",
        channel="website",
        status=LeadStatus.NEW.value,
        consent={"marketing": True, "source": "website_inquiry", "text_version": "casl_v1_marketing"},
    )
    db.add(lead)
    db.commit()
    upsert_suppression(db, email=email, source="unsubscribe", lead_id=lead.id)
    db.commit()
    assert is_suppressed(db, email=email) is True
    with patch("porterchain_shared.queue.publisher.get_queue_publisher") as pub:
        assert enqueue_nurture_intro_email(lead, db=db) is False
        assert not pub.called

    # Merge must not resurrect marketing without fresh stamped opt-in.
    merged = merge_consent_safe(
        {"marketing": False, "source": "unsubscribe"},
        {"marketing": True},
        db=db,
        email=email,
        phone=None,
    )
    assert merged["marketing"] is False

    fresh = casl_evidence({"marketing": True}, source="website_inquiry", legal_basis="consent")
    merged2 = merge_consent_safe(
        {"marketing": False, "source": "unsubscribe"},
        fresh,
        db=db,
        email=email,
        phone=None,
    )
    assert merged2["marketing"] is True
    assert is_suppressed(db, email=email) is False


def test_soft_archive_stale_leads(db) -> None:
    from porterchain_api.collaboration_engine.lead_retention import soft_archive_stale_leads

    old = datetime.now(UTC) - timedelta(days=800)
    lead = CrmLead(
        company_name=f"Arch {uuid.uuid4().hex[:6]}",
        email=f"a-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status=LeadStatus.NEW.value,
        last_touch_at=old,
    )
    db.add(lead)
    db.commit()
    # Force updated_at/created_at style touch via last_touch_at already set.
    result = soft_archive_stale_leads(db, inactive_days=730, limit=50)
    db.refresh(lead)
    assert result["archived"] >= 1
    assert lead.status == LeadStatus.ARCHIVED.value


def test_build_lead_assist_contract(db) -> None:
    from porterchain_api.intelligence_engine.lead_assist import build_lead_assist

    lead = CrmLead(
        company_name=f"Assist {uuid.uuid4().hex[:6]}",
        email=f"as-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status=LeadStatus.NEW.value,
        consent={"marketing": True, "source": "website_inquiry", "text_version": "casl_v1_marketing"},
        lead_score=40,
    )
    db.add(lead)
    db.commit()
    out = build_lead_assist(db, lead, flags={"phase2_intelligence": False})
    assert out["contract"]["writes_require_confirm"] is True
    ids = {p["id"] for p in out["proposals"]}
    assert "draft_reply" in ids
    assert "send_nurture_intro" in ids


def test_email_engagement_bumps_score(db) -> None:
    from porterchain_api.collaboration_engine.lead_engagement import apply_email_engagement

    lead = CrmLead(
        company_name=f"Eng {uuid.uuid4().hex[:6]}",
        email=f"e-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status=LeadStatus.NEW.value,
        lead_score=10,
    )
    db.add(lead)
    db.commit()
    out = apply_email_engagement(db, lead, kind="click", campaign="d1")
    db.commit()
    db.refresh(lead)
    assert out["delta"] == 5
    assert lead.lead_score == 15
    assert (lead.custom_fields or {}).get("_engagement", {}).get("clicks") == 1


def test_whatsapp_outbound_gate() -> None:
    from porterchain_api.collaboration_engine.lead_whatsapp_gate import (
        WhatsAppSendBlocked,
        assert_whatsapp_outbound_allowed,
        whatsapp_outbound_status,
    )

    lead = CrmLead(
        company_name="WA",
        email="wa@t.test",
        source="whatsapp",
        channel="whatsapp",
        status=LeadStatus.NEW.value,
        consent={},
        last_touch_at=None,
    )
    st = whatsapp_outbound_status(lead)
    assert st["allowed"] is False
    with pytest.raises(WhatsAppSendBlocked):
        assert_whatsapp_outbound_allowed(lead)
    lead.consent = {"whatsapp": True}
    assert assert_whatsapp_outbound_allowed(lead)["allowed"] is True


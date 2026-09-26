"""Lead360 composition API — abandoned kinds stay labeled apart."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from porterchain_api.booking_models import AbandonedCheckout, VisitorSession
from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.collaboration_engine.lead360_service import Lead360Service
from porterchain_api.crm_models import CrmLead


def test_lead360_composes_and_labels_abandoned_kinds(db) -> None:
    svc = LeadIngestService()
    suffix = uuid.uuid4().hex[:8]
    vid = f"l360-{suffix}"
    quote_id = str(uuid.uuid4())
    db.add(VisitorSession(id=vid))
    db.commit()

    result = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="website",
            source="website_contact",
            provider="test",
            external_event_id=f"evt-360-{suffix}",
            company_name=f"Lead360 Co {suffix}",
            email=f"l360-{suffix}@acme.test",
            phone=f"+1416{int(suffix[:7], 16) % 10_000_000:07d}",
            custom_fields={"visitor_id": vid, "quote_id": quote_id, "form": "contact"},
            external_ids={"visitor_session": vid},
            consent={"marketing": True},
        ),
    )
    lead = result.lead
    assert lead.visitor_session_id == vid

    db.add(
        AbandonedCheckout(
            quote_id=quote_id,
            email=lead.email or f"l360-{suffix}@acme.test",
            reason="session_expired",
        )
    )
    db.commit()

    # Stamp quote_id for abandoned lookup
    lead.quote_id = quote_id
    db.add(lead)
    db.commit()

    payload = Lead360Service().get(db, lead.id)
    assert payload is not None
    assert payload["lead"].id == lead.id
    assert payload["visitor"].get("session_id") == vid or payload["lead"].visitor_session_id == vid
    assert payload["consent"].get("marketing") is True
    assert payload["score"]["lead_score"] == lead.lead_score

    abandoned = payload["abandoned_checkouts"]
    assert len(abandoned) >= 1
    assert abandoned[0]["kind"] == "stripe_abandoned_checkout"
    assert "draft_abandoned" not in abandoned[0]

    for draft in payload["drafts"]:
        assert draft["kind"] == "booking_draft"
        assert "draft_abandoned" in draft
        assert draft.get("kind") != "stripe_abandoned_checkout"


def test_lead360_missing_lead_returns_none(db) -> None:
    assert Lead360Service().get(db, "missing-lead-id") is None


def test_lead360_assignee_resolution(db) -> None:
    from porterchain_api.admin_models import AdminUser

    suffix = uuid.uuid4().hex[:8]
    admin = AdminUser(
        email=f"staff-{suffix}@porterchain.com",
        name="Ops Lead",
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.flush()

    lead = CrmLead(
        company_name=f"Assigned Co {suffix}",
        email=f"asgn-{suffix}@acme.test",
        source="website",
        assigned_to=admin.id,
        consent={},
        custom_fields={},
    )
    db.add(lead)
    db.commit()

    payload = Lead360Service().get(db, lead.id)
    assert payload is not None
    assert payload["assignee"] is not None
    assert payload["assignee"]["name"] == "Ops Lead"
    assert payload["assignee"]["email"] == admin.email

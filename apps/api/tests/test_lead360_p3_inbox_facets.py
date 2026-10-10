"""P3 Lead inbox facets — open draft / nurture / abandoned filters."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from porterchain_api.booking_draft_models import BookingDraft
from porterchain_api.booking_models import AbandonedCheckout, VisitorSession
from porterchain_api.collaboration_engine.crm_service import CrmSalesService
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.states import BookingDraftState


def test_list_leads_has_open_draft_and_nurture_filters(db) -> None:
    svc = CrmSalesService()
    suffix = uuid.uuid4().hex[:8]
    vid = f"facet-{suffix}"
    db.add(VisitorSession(id=vid))
    draft = BookingDraft(
        session_id=vid,
        state=BookingDraftState.DRAFT.value,
        current_step="details",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db.add(draft)
    db.flush()

    with_draft = CrmLead(
        company_name=f"Draft Co {suffix}",
        email=f"draft-{suffix}@acme.test",
        source="website",
        visitor_session_id=vid,
        booking_draft_id=draft.id,
        tags=[],
        consent={},
        custom_fields={},
    )
    nurturing = CrmLead(
        company_name=f"Nurture Co {suffix}",
        email=f"nurture-{suffix}@acme.test",
        source="website",
        status="nurturing",
        tags=["nurture"],
        consent={},
        custom_fields={},
    )
    plain = CrmLead(
        company_name=f"Plain Co {suffix}",
        email=f"plain-{suffix}@acme.test",
        source="website",
        tags=[],
        consent={},
        custom_fields={},
    )
    db.add_all([with_draft, nurturing, plain])
    db.commit()

    draft_rows = svc.list_leads(db, has_open_draft=True, search=suffix, limit=50)
    assert {r.id for r in draft_rows} == {with_draft.id}

    nurture_rows = svc.list_leads(db, nurture_scheduled=True, search=suffix, limit=50)
    assert nurturing.id in {r.id for r in nurture_rows}
    assert plain.id not in {r.id for r in nurture_rows}


def test_list_leads_has_abandoned_filter(db) -> None:
    svc = CrmSalesService()
    suffix = uuid.uuid4().hex[:8]
    quote_id = str(uuid.uuid4())
    lead = CrmLead(
        company_name=f"Abandon Co {suffix}",
        email=f"abandon-{suffix}@acme.test",
        source="website_booking",
        quote_id=quote_id,
        tags=[],
        consent={},
        custom_fields={"quote_id": quote_id},
    )
    db.add(lead)
    db.add(
        AbandonedCheckout(
            quote_id=quote_id,
            email=lead.email,
            reason="session_expired",
        )
    )
    db.commit()

    rows = svc.list_leads(db, has_abandoned=True, search=suffix, limit=50)
    assert lead.id in {r.id for r in rows}


def test_pipeline_board_lead_card_flags(db) -> None:
    svc = CrmSalesService()
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(UTC)
    lead = CrmLead(
        company_name=f"Pipe Co {suffix}",
        email=f"pipe-{suffix}@acme.test",
        source="website",
        status="new",
        booking_draft_id=str(uuid.uuid4()),
        sla_first_response_due_at=now - timedelta(hours=2),
        tags=["nurture"],
        consent={},
        custom_fields={},
        lead_score=55,
    )
    db.add(lead)
    db.commit()

    cols = svc.pipeline_board(db, search=suffix)
    cards = [c for col in cols for c in col["cards"] if c["type"] == "lead" and c["id"] == lead.id]
    assert len(cards) == 1
    assert cards[0]["has_draft"] is True
    assert cards[0]["sla_breached"] is True
    assert cards[0]["nurture"] is True

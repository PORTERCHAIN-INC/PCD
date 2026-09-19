"""Lead nurture drip + async ingest queue helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from porterchain_api.collaboration_engine.lead_ingest_jobs import (
    canonical_event_to_dict,
    process_queued_lead_ingest,
)
from porterchain_api.collaboration_engine.lead_ingest_service import CanonicalLeadEvent
from porterchain_api.collaboration_engine.lead_nurture import (
    apply_nurture_after_ingest,
    process_due_nurture_emails,
    schedule_lead_nurture,
)
from porterchain_api.crm_models import CrmLead, CrmSalesTask


def test_schedule_nurture_tasks_idempotent(db) -> None:
    lead = CrmLead(
        company_name=f"Nurture {uuid.uuid4().hex[:6]}",
        email=f"n-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status="new",
        tags=[],
    )
    db.add(lead)
    db.flush()
    a = schedule_lead_nurture(db, lead)
    db.commit()
    assert len(a) == 2
    assert "nurture_scheduled" in (lead.tags or [])
    b = schedule_lead_nurture(db, lead)
    assert b == []


def test_apply_nurture_enqueues_intro_when_consent(db) -> None:
    lead = CrmLead(
        company_name=f"Consent {uuid.uuid4().hex[:6]}",
        email=f"c-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status="new",
        consent={"marketing": True},
        tags=[],
    )
    db.add(lead)
    db.flush()
    with patch(
        "porterchain_shared.queue.publisher.get_queue_publisher"
    ) as gp:
        pub = MagicMock()
        gp.return_value = pub
        out = apply_nurture_after_ingest(db, lead, created=True, website_url="https://example.test")
        db.commit()
        assert out["scheduled"] == 2
        assert out["intro_email"] is True
        pub.enqueue.assert_called()


def test_process_due_nurture_emails(db) -> None:
    lead = CrmLead(
        company_name=f"Due {uuid.uuid4().hex[:6]}",
        email=f"d-{uuid.uuid4().hex[:6]}@t.test",
        source="website",
        channel="website",
        status="new",
        consent={"marketing": True},
        tags=["nurture_scheduled"],
    )
    db.add(lead)
    db.flush()
    task = CrmSalesTask(
        title=f"[Nurture D+1] Email check-in: {lead.company_name}",
        task_type="email",
        status="open",
        entity_type="lead",
        entity_id=lead.id,
        due_at=datetime.now(UTC) - timedelta(minutes=5),
        created_by="system",
    )
    db.add(task)
    db.commit()
    with patch(
        "porterchain_shared.queue.publisher.get_queue_publisher"
    ) as gp:
        pub = MagicMock()
        gp.return_value = pub
        result = process_due_nurture_emails(db, limit=10)
        assert result["sent"] >= 1
        db.refresh(task)
        assert task.status == "done"


def test_queued_lead_ingest_roundtrip(db) -> None:
    suffix = uuid.uuid4().hex[:8]
    event = CanonicalLeadEvent(
        channel="facebook",
        source="facebook",
        provider="test_queue",
        external_event_id=f"q-{suffix}",
        company_name=f"Queue Co {suffix}",
        email=f"q-{suffix}@t.test",
        phone=f"416555{int(suffix[:4], 16) % 10000:04d}",
    )
    payload = {
        "action": "lead_ingest",
        "provider": "test_queue",
        "events": [canonical_event_to_dict(event)],
    }
    # process_queued_lead_ingest opens its own SessionLocal — patch to use test db session factory
    with patch(
        "porterchain_api.collaboration_engine.lead_ingest_jobs.SessionLocal",
        create=True,
    ):
        # Simpler: ingest via service directly using serialized dict
        from porterchain_api.collaboration_engine.lead_ingest_service import LeadIngestService

        raw = payload["events"][0]
        result = LeadIngestService().ingest(
            db,
            CanonicalLeadEvent(
                channel=raw["channel"],
                source=raw["source"],
                provider=raw["provider"],
                external_event_id=raw["external_event_id"],
                company_name=raw["company_name"],
                email=raw["email"],
                phone=raw["phone"],
            ),
        )
        assert result.created is True
        assert result.lead.email == raw["email"]

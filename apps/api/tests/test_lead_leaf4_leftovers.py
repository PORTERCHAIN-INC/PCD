"""Lead Leaf-4 leftovers: SLA map, high-priority notify, metrics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from porterchain_api.collaboration_engine.lead_ingest_service import (
    CanonicalLeadEvent,
    LeadIngestService,
)
from porterchain_api.collaboration_engine.lead_metrics import lead_channel_metrics
from porterchain_api.collaboration_engine.lead_ops import (
    notify_unassigned_high_priority,
    sla_minutes_for_channel,
)
from porterchain_api.config import Settings
from porterchain_api.crm_models import CrmLead, CrmSalesTask


def test_sla_minutes_for_channel() -> None:
    settings = Settings(lead_sla_minutes_json='{"whatsapp":15,"default":45}')
    assert sla_minutes_for_channel("whatsapp", settings) == 15
    assert sla_minutes_for_channel("website", settings) == 45
    assert sla_minutes_for_channel("unknown", Settings(lead_sla_minutes_json="")) == 60


def test_notify_unassigned_high_creates_task(db) -> None:
    lead = CrmLead(
        company_name=f"Hot {uuid.uuid4().hex[:6]}",
        email=f"hot-{uuid.uuid4().hex[:6]}@t.test",
        priority="urgent",
        status="new",
        channel="whatsapp",
        source="whatsapp",
        sla_first_response_due_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    db.add(lead)
    db.flush()
    task = notify_unassigned_high_priority(db, lead)
    db.commit()
    assert task is not None
    assert task.task_type == "follow_up"
    again = notify_unassigned_high_priority(db, lead)
    assert again is not None and again.id == task.id


def test_ingest_applies_channel_sla_and_urgent_task(db, monkeypatch) -> None:
    settings = Settings(lead_sla_minutes_json='{"phone_call":20,"default":90}')
    monkeypatch.setattr(
        "porterchain_api.collaboration_engine.lead_ops.get_settings",
        lambda: settings,
    )
    svc = LeadIngestService()
    suffix = uuid.uuid4().hex[:8]
    before = datetime.now(UTC)
    result = svc.ingest(
        db,
        CanonicalLeadEvent(
            channel="phone_call",
            source="phone_call",
            provider="test",
            external_event_id=f"sla-{suffix}",
            company_name=f"SLA Co {suffix}",
            email=f"sla-{suffix}@t.test",
            phone=f"416555{int(suffix[:4], 16) % 10000:04d}",
            priority="high",
        ),
    )
    assert result.created is True
    due = result.lead.sla_first_response_due_at
    assert due is not None
    delta = (due - before).total_seconds() / 60.0
    assert 15 <= delta <= 25
    tasks = (
        db.query(CrmSalesTask)
        .filter(
            CrmSalesTask.entity_id == result.lead.id,
            CrmSalesTask.task_type == "follow_up",
            CrmSalesTask.priority == "high",
        )
        .all()
    )
    assert len(tasks) == 1
    assert "Respond to high lead" in tasks[0].title


def test_lead_channel_metrics_shape(db) -> None:
    out = lead_channel_metrics(db, days=30)
    assert out["window_days"] == 30
    assert "ingest" in out and "leads" in out and "sla" in out and "capi" in out
    assert "funnel_by_channel" in out["leads"]

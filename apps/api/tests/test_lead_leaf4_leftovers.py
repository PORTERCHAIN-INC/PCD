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
            phone=f"416{suffix[:7].ljust(7, '0')}",
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


def test_growth_alert_does_not_email_staff(db, monkeypatch) -> None:
    captured: list[dict] = []

    def _capture(_db, specs, *, event_type, correlation_id):
        captured.extend(specs)

    monkeypatch.setattr(
        "porterchain_api.platform.staff_notify.dispatch_staff_specs",
        _capture,
    )
    lead = CrmLead(
        company_name=f"Mail {uuid.uuid4().hex[:6]}",
        email=f"mail-{uuid.uuid4().hex[:6]}@t.test",
        priority="high",
        status="new",
        channel="website",
        source="website",
    )
    db.add(lead)
    db.flush()
    notify_unassigned_high_priority(db, lead)
    assert captured == []


def test_growth_alert_emails_watch_list_only_when_admin_app_is_empty(db, monkeypatch) -> None:
    captured: list[dict] = []

    def _capture(_db, specs, *, event_type, correlation_id):
        captured.extend(specs)

    monkeypatch.setattr(
        "porterchain_api.platform.staff_notify.dispatch_staff_specs",
        _capture,
    )
    monkeypatch.setattr(
        "porterchain_api.notification_engine.staff_fanout.ops_watch_emails",
        lambda: {"growth@porterchain.com"},
    )
    monkeypatch.setattr(
        "porterchain_api.notification_engine.realtime.anyone_online",
        lambda role: role == "admin",
    )
    online = CrmLead(
        company_name="Online Co",
        email=f"online-{uuid.uuid4().hex[:6]}@t.test",
        priority="high",
        status="new",
        channel="website",
        source="website",
    )
    db.add(online)
    db.flush()
    notify_unassigned_high_priority(db, online)
    assert captured == []

    captured.clear()
    monkeypatch.setattr(
        "porterchain_api.notification_engine.realtime.anyone_online",
        lambda role: False,
    )
    empty = CrmLead(
        company_name="Empty Office",
        email=f"empty-{uuid.uuid4().hex[:6]}@t.test",
        priority="urgent",
        status="new",
        channel="website",
        source="website",
    )
    db.add(empty)
    db.flush()
    notify_unassigned_high_priority(db, empty)
    emails = [spec for spec in captured if spec["channel"] == "email"]
    assert len(emails) == 1
    assert emails[0]["context"]["offline_watch"] is True
    assert emails[0]["deep_link"].startswith("http")
    assert emails[0]["deep_link"].endswith(f"/leads/{empty.id}")
    assert emails[0]["context"]["title"] == "Empty Office — unassigned high lead"
    assert "notice_body" not in emails[0]["context"]
    assert not any(spec["channel"] == "in_app" for spec in captured)


def test_agent_inbox_lists_unassigned_and_notices(db) -> None:
    from datetime import timedelta

    from porterchain_api.collaboration_engine.lead_agent_activity import lead_agent_activity

    suffix = uuid.uuid4().hex[:6]
    quiet = CrmLead(
        company_name=f"Quiet {suffix}",
        email=f"quiet-{suffix}@t.test",
        priority="medium",
        status="new",
        channel="website",
        source="website",
    )
    hot = CrmLead(
        company_name=f"Hot {suffix}",
        email=f"hot-{suffix}@t.test",
        priority="urgent",
        status="new",
        channel="whatsapp",
        source="whatsapp",
    )
    breached = CrmLead(
        company_name=f"Late {suffix}",
        email=f"late-{suffix}@t.test",
        priority="medium",
        status="new",
        channel="phone_call",
        source="phone_call",
        assigned_to="staff-1",
        sla_first_response_due_at=datetime.now(UTC) - timedelta(hours=2),
    )
    done = CrmLead(
        company_name=f"Done {suffix}",
        email=f"done-{suffix}@t.test",
        priority="high",
        status="converted",
    )
    db.add_all([quiet, hot, breached, done])
    db.commit()

    payload = lead_agent_activity(db)
    unassigned_names = {row["company_name"] for row in payload["inbox"]["unassigned"]}
    assert f"Quiet {suffix}" in unassigned_names
    assert f"Hot {suffix}" in unassigned_names
    assert f"Late {suffix}" not in unassigned_names
    assert f"Done {suffix}" not in unassigned_names

    notices = payload["inbox"]["notices"]
    sla = [n for n in notices if n["company_name"] == f"Late {suffix}"]
    hot_notes = [n for n in notices if n["company_name"] == f"Hot {suffix}"]
    assert sla and sla[0]["notice_kind"] == "sla"
    assert "past first response" in sla[0]["notice_body"]
    assert hot_notes and hot_notes[0]["notice_kind"] == "unassigned"
    assert hot_notes[0]["notice_subject"].endswith("— unassigned high lead")
    assert "is unassigned" in hot_notes[0]["notice_body"]
    assert not any(n["company_name"] == f"Quiet {suffix}" for n in notices)
    assert payload["config"]["internal_email"] is False


def test_notification_center_hides_unassigned_high_lead(db) -> None:
    from porterchain_api.notification_engine.engine import get_notification_engine

    engine = get_notification_engine()
    user_id = f"growth-{uuid.uuid4().hex[:8]}"
    lead = engine.dispatch(
        db,
        event_type="lead.unassigned",
        template_key="lead_sla_escalation",
        channel="in_app",
        recipient_type="admin",
        recipient_id=user_id,
        context={"title": "Acme — unassigned high lead", "company_name": "Acme", "deep_link": "/leads/x"},
        category="crm",
        priority="high",
        deep_link="/leads/x",
    )
    ops = engine.dispatch(
        db,
        event_type="test.ops",
        template_key="exception_opened",
        channel="in_app",
        recipient_type="admin",
        recipient_id=user_id,
        context={"order_number": "1001"},
        category="orders",
        priority="high",
    )
    assert lead is not None and ops is not None
    center = engine.inbox_payload(db, user_role="admin", user_id=user_id)
    assert lead.id not in {item["id"] for item in center["items"]}
    assert ops.id in {item["id"] for item in center["items"]}
    assert center["unread_count"] == 1

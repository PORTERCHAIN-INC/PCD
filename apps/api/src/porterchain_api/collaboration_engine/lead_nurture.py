"""Lead nurture — CRM follow-up tasks + optional marketing-consent email drip."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead, CrmSalesTask
from porterchain_api.domain.crm_states import LeadStatus, TaskType

logger = logging.getLogger(__name__)

_NURTURE_TAG = "nurture_scheduled"
_D1_TITLE_PREFIX = "[Nurture D+1]"
_D3_TITLE_PREFIX = "[Nurture D+3]"


def _now() -> datetime:
    return datetime.now(UTC)


def schedule_lead_nurture(db: Session, lead: CrmLead) -> list[CrmSalesTask]:
    """Create day+1 email + day+3 call tasks for new leads (idempotent via tag)."""
    if lead.status == LeadStatus.CONVERTED.value:
        return []
    tags = list(lead.tags or [])
    if _NURTURE_TAG in tags:
        return []
    if not (lead.email or lead.phone):
        return []

    created: list[CrmSalesTask] = []
    now = _now()
    company = lead.company_name or "lead"

    d1 = CrmSalesTask(
        title=f"{_D1_TITLE_PREFIX} Email check-in: {company}",
        description=(
            "Nurture drip day 1 — send capacity FAQ / next-step email if marketing consent; "
            "otherwise staff personal note."
        ),
        task_type=TaskType.EMAIL.value if hasattr(TaskType, "EMAIL") else "email",
        status="open",
        priority="medium",
        entity_type="lead",
        entity_id=lead.id,
        due_at=now + timedelta(days=1),
        created_by="system",
    )
    d3 = CrmSalesTask(
        title=f"{_D3_TITLE_PREFIX} Call / WhatsApp: {company}",
        description=(
            "Nurture drip day 3 — personal outreach. WhatsApp templates only with consent "
            "or approved template."
        ),
        task_type=TaskType.FOLLOW_UP.value if hasattr(TaskType, "FOLLOW_UP") else "follow_up",
        status="open",
        priority="medium",
        entity_type="lead",
        entity_id=lead.id,
        due_at=now + timedelta(days=3),
        created_by="system",
    )
    db.add(d1)
    db.add(d3)
    tags.append(_NURTURE_TAG)
    lead.tags = tags
    db.flush()
    created.extend([d1, d3])
    return created


def enqueue_nurture_intro_email(lead: CrmLead, *, website_url: str = "") -> bool:
    """Day-0 intro email when marketing consent is true. Enqueues EMAILS queue."""
    consent = lead.consent or {}
    if not consent.get("marketing"):
        return False
    email = (lead.email or "").strip()
    if not email or "@" not in email:
        return False
    base = (website_url or "https://porterchain.com").rstrip("/")
    try:
        from porterchain_shared.queue.names import QueueName
        from porterchain_shared.queue.publisher import get_queue_publisher

        get_queue_publisher().enqueue(
            QueueName.EMAILS,
            {
                "channel": "email",
                "template": "lead_nurture_intro",
                "recipient": email,
                "recipient_type": "lead",
                "recipient_id": lead.id,
                "context": {
                    "company_name": lead.company_name,
                    "contact_name": lead.primary_contact_name or "",
                    "quote_url": f"{base}/sign-up?intent=quote&utm_source=nurture&utm_medium=email",
                    "lead_id": lead.id,
                },
            },
        )
        return True
    except Exception:
        logger.exception("lead_nurture_intro_enqueue_failed lead=%s", lead.id)
        return False


def process_due_nurture_emails(db: Session, *, limit: int = 20) -> dict[str, int]:
    """Send D+1 nurture emails for due open email tasks when marketing consent holds."""
    now = _now()
    tasks = (
        db.query(CrmSalesTask)
        .filter(
            CrmSalesTask.status == "open",
            CrmSalesTask.task_type == "email",
            CrmSalesTask.entity_type == "lead",
            CrmSalesTask.due_at.isnot(None),
            CrmSalesTask.due_at <= now,
            CrmSalesTask.title.like(f"{_D1_TITLE_PREFIX}%"),
        )
        .order_by(CrmSalesTask.due_at.asc())
        .limit(limit)
        .all()
    )
    sent = 0
    skipped = 0
    for task in tasks:
        lead = db.get(CrmLead, task.entity_id) if task.entity_id else None
        if not lead or lead.status == LeadStatus.CONVERTED.value:
            task.status = "cancelled"
            skipped += 1
            continue
        consent = lead.consent or {}
        if not consent.get("marketing") or not lead.email:
            # Leave open for staff; don't auto-email without consent.
            skipped += 1
            continue
        from porterchain_api.config import get_settings

        settings = get_settings()
        website = getattr(settings, "website_url", "") or ""
        ok = _enqueue_d1_email(lead, website_url=website)
        if ok:
            task.status = "done"
            task.completed_at = now
            sent += 1
        else:
            skipped += 1
    if sent or skipped:
        db.commit()
    return {"due": len(tasks), "sent": sent, "skipped": skipped}


def _enqueue_d1_email(lead: CrmLead, *, website_url: str) -> bool:
    base = (website_url or "https://porterchain.com").rstrip("/")
    try:
        from porterchain_shared.queue.names import QueueName
        from porterchain_shared.queue.publisher import get_queue_publisher

        get_queue_publisher().enqueue(
            QueueName.EMAILS,
            {
                "channel": "email",
                "template": "lead_nurture_d1",
                "recipient": lead.email,
                "recipient_type": "lead",
                "recipient_id": lead.id,
                "context": {
                    "company_name": lead.company_name,
                    "contact_name": lead.primary_contact_name or "",
                    "quote_url": f"{base}/sign-up?intent=quote&utm_source=nurture&utm_medium=email&utm_campaign=d1",
                    "lead_id": lead.id,
                },
            },
        )
        return True
    except Exception:
        logger.exception("lead_nurture_d1_enqueue_failed lead=%s", lead.id)
        return False


def apply_nurture_after_ingest(
    db: Session, lead: CrmLead, *, created: bool, website_url: str = ""
) -> dict[str, Any]:
    """Hook for LeadIngestService — schedule tasks; day-0 email if consented."""
    if not created:
        return {"scheduled": 0, "intro_email": False}
    tasks = schedule_lead_nurture(db, lead)
    intro = enqueue_nurture_intro_email(lead, website_url=website_url)
    return {"scheduled": len(tasks), "intro_email": intro}


__all__ = [
    "apply_nurture_after_ingest",
    "enqueue_nurture_intro_email",
    "process_due_nurture_emails",
    "schedule_lead_nurture",
]

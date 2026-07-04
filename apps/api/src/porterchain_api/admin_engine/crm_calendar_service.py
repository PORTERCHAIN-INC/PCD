"""CRM ↔ Zoho Calendar sync for sales tasks and meetings."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmContact, CrmLead, CrmSalesTask
from porterchain_api.domain.crm_states import TaskStatus
from porterchain_api.integrations.zoho_calendar import ZohoCalendarClient
from porterchain_shared.config.settings import PlatformSettings, get_platform_settings

logger = logging.getLogger(__name__)

CALENDAR_TASK_TYPES = frozenset({"meeting", "demo", "merchant_visit", "call", "follow_up"})


class CrmCalendarService:
    def __init__(self, settings: PlatformSettings | None = None) -> None:
        self._settings = settings or get_platform_settings()
        self._zoho = ZohoCalendarClient(self._settings)

    def status(self) -> dict[str, Any]:
        base = self._zoho.integration_status()
        base["sync_task_types"] = sorted(CALENDAR_TASK_TYPES)
        return base

    def should_sync(self, task: CrmSalesTask) -> bool:
        if task.task_type not in CALENDAR_TASK_TYPES:
            return False
        if not task.due_at:
            return False
        if task.status == TaskStatus.DONE.value:
            return False
        return self._zoho.configured

    def sync_task(self, db: Session, task: CrmSalesTask) -> CrmSalesTask:
        if not self.should_sync(task):
            return task
        try:
            attendees = self._attendee_emails(db, task)
            description = task.description or ""
            if task.entity_type and task.entity_id:
                description = f"{description}\n\nCRM: {task.entity_type}/{task.entity_id}".strip()
            if task.zoho_event_uid:
                self._zoho.delete_event(task.zoho_event_uid)
            uid = self._zoho.create_event(
                title=task.title,
                start=task.due_at,
                end=(task.due_at + timedelta(hours=1)) if task.due_at else None,
                description=description or None,
                attendee_emails=attendees,
            )
            task.zoho_event_uid = uid
            db.commit()
            db.refresh(task)
        except Exception as exc:  # noqa: BLE001
            logger.warning("zoho_calendar_sync_failed task=%s err=%s", task.id, exc)
        return task

    def unsync_task(self, db: Session, task: CrmSalesTask) -> None:
        if not task.zoho_event_uid or not self._zoho.configured:
            return
        try:
            self._zoho.delete_event(task.zoho_event_uid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("zoho_calendar_delete_failed task=%s err=%s", task.id, exc)
        task.zoho_event_uid = None
        db.commit()

    def list_merged(
        self,
        db: Session,
        *,
        start: datetime,
        end: datetime,
        entity_id: str | None = None,
    ) -> dict[str, Any]:
        tasks = (
            db.query(CrmSalesTask)
            .filter(CrmSalesTask.due_at.isnot(None), CrmSalesTask.due_at >= start, CrmSalesTask.due_at <= end)
            .order_by(CrmSalesTask.due_at.asc())
            .limit(500)
            .all()
        )
        if entity_id:
            tasks = [t for t in tasks if t.entity_id == entity_id]

        crm_events = [
            {
                "id": t.id,
                "title": t.title,
                "start": t.due_at.isoformat() if t.due_at else None,
                "end": (t.due_at + timedelta(hours=1)).isoformat() if t.due_at else None,
                "source": "crm",
                "task_type": t.task_type,
                "status": t.status,
                "zoho_event_uid": t.zoho_event_uid,
                "entity_type": t.entity_type,
                "entity_id": t.entity_id,
            }
            for t in tasks
        ]

        zoho_events: list[dict[str, Any]] = []
        zoho_error: str | None = None
        if self._zoho.configured:
            try:
                for ev in self._zoho.list_events(start=start, end=end):
                    if any(t.zoho_event_uid == ev.uid for t in tasks):
                        continue
                    zoho_events.append(
                        {
                            "id": ev.uid,
                            "title": ev.title,
                            "start": ev.start.isoformat(),
                            "end": ev.end.isoformat() if ev.end else None,
                            "source": "zoho",
                            "location": ev.location,
                            "organizer": ev.organizer,
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                zoho_error = str(exc)
                logger.warning("zoho_calendar_list_failed: %s", exc)

        return {
            "integration": self.status(),
            "crm_events": crm_events,
            "zoho_events": zoho_events,
            "zoho_error": zoho_error,
        }

    def _attendee_emails(self, db: Session, task: CrmSalesTask) -> list[str]:
        emails: list[str] = []
        if task.entity_type == "lead" and task.entity_id:
            lead = db.get(CrmLead, task.entity_id)
            if lead and lead.email:
                emails.append(lead.email.lower())
        if task.company_id:
            contact = (
                db.query(CrmContact)
                .filter(CrmContact.company_id == task.company_id, CrmContact.is_primary.is_(True))
                .first()
            )
            if contact and contact.email:
                emails.append(contact.email.lower())
        return list(dict.fromkeys(emails))

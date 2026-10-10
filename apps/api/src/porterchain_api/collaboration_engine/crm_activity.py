"""CRM activity timeline and admin audit."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import CrmActor, _now
from porterchain_api.crm_models import CrmActivity



class CrmActivityMixin:
    def _admin_audit(
        self,
        db: Session,
        ctx: CrmActor | None,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: dict | None = None,
    ) -> None:
        from porterchain_api.platform.admin_audit import log_admin_audit

        log_admin_audit(
            db,
            ctx,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )

    def log_activity(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: str,
        activity_type: str = "note",
        subject: str | None = None,
        body: str | None = None,
        metadata: dict | None = None,
        actor_id: str | None = None,
        occurred_at: datetime | None = None,
        commit: bool = True,
    ) -> CrmActivity:
        activity = CrmActivity(
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type=activity_type,
            subject=subject,
            body=body,
            metadata_json=metadata or {},
            actor_id=actor_id,
            occurred_at=occurred_at or _now(),
        )
        db.add(activity)
        if commit:
            db.commit()
            db.refresh(activity)
        return activity

    def list_activities(
        self, db: Session, *, entity_type: str | None = None, entity_id: str | None = None, limit: int = 100
    ) -> list[CrmActivity]:
        q = db.query(CrmActivity)
        if entity_type:
            q = q.filter(CrmActivity.entity_type == entity_type)
        if entity_id:
            q = q.filter(CrmActivity.entity_id == entity_id)
        return q.order_by(CrmActivity.occurred_at.desc()).limit(limit).all()

    @staticmethod
    def activity_dict(a: CrmActivity) -> dict[str, Any]:
        return {
            "id": a.id,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "activity_type": a.activity_type,
            "subject": a.subject,
            "body": a.body,
            "metadata": a.metadata_json or {},
            "actor_id": a.actor_id,
            "occurred_at": a.occurred_at,
            "created_at": a.created_at,
        }


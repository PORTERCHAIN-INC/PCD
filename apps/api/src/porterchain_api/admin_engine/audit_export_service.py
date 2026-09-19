"""Admin audit log export (§11.1.7)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.booking_models import DomainEvent


class AdminAuditExportService:
    def list_logs(
        self,
        db: Session,
        *,
        resource_type: str | None = None,
        action_prefix: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        q = db.query(AdminAuditLog).order_by(AdminAuditLog.created_at.desc())
        if resource_type:
            q = q.filter(AdminAuditLog.resource_type == resource_type)
        if action_prefix:
            q = q.filter(AdminAuditLog.action.like(f"{action_prefix}%"))
        rows = q.limit(min(limit, 2000)).all()
        return [self._serialize_admin_log(row) for row in rows]

    def domain_events(
        self,
        db: Session,
        *,
        aggregate_type: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        q = db.query(DomainEvent).order_by(DomainEvent.occurred_at.desc())
        if aggregate_type:
            q = q.filter(DomainEvent.aggregate_type == aggregate_type)
        rows = q.limit(min(limit, 2000)).all()
        return [
            {
                "id": row.id,
                "event_type": row.event_type,
                "aggregate_type": row.aggregate_type,
                "aggregate_id": row.aggregate_id,
                "actor_type": row.actor_type,
                "actor_id": row.actor_id,
                "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                "payload": row.payload,
            }
            for row in rows
        ]

    def export_bundle(
        self,
        db: Session,
        *,
        limit: int = 1000,
    ) -> dict[str, Any]:
        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "admin_audit_logs": self.list_logs(db, limit=limit),
            "domain_events": self.domain_events(db, limit=limit),
        }

    def export_csv(self, db: Session, *, limit: int = 1000) -> str:
        rows = self.list_logs(db, limit=limit)
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "created_at",
                "action",
                "actor_user_id",
                "resource_type",
                "resource_id",
                "payload",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "created_at": row.get("created_at"),
                    "action": row.get("action"),
                    "actor_user_id": row.get("actor_user_id"),
                    "resource_type": row.get("resource_type"),
                    "resource_id": row.get("resource_id"),
                    "payload": row.get("payload"),
                }
            )
        return buffer.getvalue()

    def _serialize_admin_log(self, row: AdminAuditLog) -> dict[str, Any]:
        return {
            "id": row.id,
            "action": row.action,
            "actor_user_id": row.actor_user_id,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "payload": row.payload,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

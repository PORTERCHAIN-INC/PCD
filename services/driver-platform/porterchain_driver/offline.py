"""Offline action queue — sync when connectivity restored."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class OfflineService:
    def queue_action(
        self,
        db: Session,
        driver: Any,
        *,
        action_type: str,
        payload: dict,
    ) -> dict:
        from porterchain_api.driver_models import DriverOfflineAction

        action = DriverOfflineAction(
            driver_id=driver.id,
            action_type=action_type,
            payload=payload,
            status="pending",
        )
        db.add(action)
        db.flush()
        return {"action_id": action.id, "status": "queued"}

    def list_pending(self, db: Session, driver_id: str) -> list[dict]:
        from porterchain_api.driver_models import DriverOfflineAction

        rows = (
            db.query(DriverOfflineAction)
            .filter(DriverOfflineAction.driver_id == driver_id, DriverOfflineAction.status == "pending")
            .order_by(DriverOfflineAction.created_at.asc())
            .all()
        )
        return [
            {"id": r.id, "action_type": r.action_type, "payload": r.payload, "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def sync_pending(self, db: Session, driver: Any, *, executor: Any) -> dict:
        from porterchain_api.driver_models import DriverOfflineAction

        rows = (
            db.query(DriverOfflineAction)
            .filter(DriverOfflineAction.driver_id == driver.id, DriverOfflineAction.status == "pending")
            .order_by(DriverOfflineAction.created_at.asc())
            .all()
        )
        synced, failed = 0, 0
        for row in rows:
            try:
                executor.execute(driver, row.action_type, row.payload)
                row.status = "synced"
                synced += 1
            except Exception as exc:
                row.status = "failed"
                row.error = str(exc)[:500]
                failed += 1
        db.flush()
        return {"synced": synced, "failed": failed, "pending": len(rows) - synced - failed}

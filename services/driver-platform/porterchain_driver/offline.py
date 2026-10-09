"""Offline action queue — sync when connectivity restored."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

UPLOAD_ACTION_TYPES = frozenset(
    {"pod_photo", "camera_upload", "pod_signature", "pod_barcode", "pod_id_check", "document_upload"}
)
GPS_ACTION_TYPES = frozenset({"location"})


class ConflictSkip(Exception):
    """Raised when server state already satisfies the queued action."""


class OfflineService:
    def queue_action(
        self,
        db: Session,
        driver: Any,
        *,
        action_type: str,
        payload: dict,
        client_id: str | None = None,
    ) -> dict:
        from porterchain_api.driver_models import DriverOfflineAction

        merged_payload = dict(payload)
        if client_id:
            merged_payload["client_id"] = client_id
            pending_rows = (
                db.query(DriverOfflineAction)
                .filter(
                    DriverOfflineAction.driver_id == driver.id,
                    DriverOfflineAction.status.in_(("pending", "failed")),
                )
                .all()
            )
            for existing in pending_rows:
                if (existing.payload or {}).get("client_id") == client_id:
                    return {
                        "action_id": existing.id,
                        "status": existing.status,
                        "action_type": existing.action_type,
                        "deduplicated": True,
                    }

        action = DriverOfflineAction(
            driver_id=driver.id,
            action_type=action_type,
            payload=merged_payload,
            status="pending",
        )
        db.add(action)
        db.flush()
        return {"action_id": action.id, "status": "queued", "action_type": action_type, "deduplicated": False}

    def list_pending(self, db: Session, driver_id: str) -> list[dict]:
        return self._list_by_status(db, driver_id, "pending")

    def status(self, db: Session, driver_id: str) -> dict[str, Any]:
        from porterchain_api.driver_models import DriverOfflineAction

        rows = (
            db.query(DriverOfflineAction)
            .filter(DriverOfflineAction.driver_id == driver_id)
            .order_by(DriverOfflineAction.created_at.desc())
            .limit(200)
            .all()
        )
        pending = [r for r in rows if r.status == "pending"]
        failed = [r for r in rows if r.status == "failed"]
        synced = sum(1 for r in rows if r.status == "synced")

        gps_pending = sum(1 for r in pending if r.action_type in GPS_ACTION_TYPES)
        camera_queue = sum(1 for r in pending if r.action_type in UPLOAD_ACTION_TYPES)
        failed_uploads = sum(1 for r in failed if r.action_type in UPLOAD_ACTION_TYPES)

        last_synced = max(
            (r.created_at for r in rows if r.status == "synced"),
            default=None,
        )

        return {
            "pending_count": len(pending),
            "failed_count": len(failed),
            "synced_count": synced,
            "gps_pending": gps_pending,
            "camera_upload_pending": camera_queue,
            "failed_uploads": failed_uploads,
            "pending": [self._serialize(r) for r in pending[:30]],
            "failed": [self._serialize(r) for r in failed[:30]],
            "last_sync_at": last_synced.isoformat() if last_synced else None,
        }

    def sync_pending(self, db: Session, driver: Any, *, executor: Any) -> dict:
        from porterchain_api.driver_models import DriverOfflineAction

        rows = (
            db.query(DriverOfflineAction)
            .filter(DriverOfflineAction.driver_id == driver.id, DriverOfflineAction.status == "pending")
            .order_by(DriverOfflineAction.created_at.asc())
            .all()
        )
        synced, failed = 0, 0
        conflicts = 0
        for row in rows:
            try:
                executor.execute(driver, row.action_type, row.payload)
                row.status = "synced"
                row.error = None
                synced += 1
            except ConflictSkip as exc:
                row.status = "synced"
                row.error = str(exc)[:500]
                conflicts += 1
                synced += 1
            except Exception as exc:
                row.status = "failed"
                row.error = str(exc)[:500]
                failed += 1
        db.flush()
        return {
            "synced": synced,
            "failed": failed,
            "conflicts_resolved": conflicts,
            "pending": len(rows) - synced - failed,
            "synced_at": datetime.now(UTC).isoformat(),
        }

    def retry_failed(self, db: Session, driver: Any, *, executor: Any) -> dict:
        from porterchain_api.driver_models import DriverOfflineAction

        rows = (
            db.query(DriverOfflineAction)
            .filter(DriverOfflineAction.driver_id == driver.id, DriverOfflineAction.status == "failed")
            .order_by(DriverOfflineAction.created_at.asc())
            .all()
        )
        for row in rows:
            row.status = "pending"
            row.error = None
        db.flush()
        result = self.sync_pending(db, driver, executor=executor)
        result["retried"] = len(rows)
        return result

    def _list_by_status(self, db: Session, driver_id: str, status: str) -> list[dict]:
        from porterchain_api.driver_models import DriverOfflineAction

        rows = (
            db.query(DriverOfflineAction)
            .filter(DriverOfflineAction.driver_id == driver_id, DriverOfflineAction.status == status)
            .order_by(DriverOfflineAction.created_at.asc())
            .all()
        )
        return [self._serialize(r) for r in rows]

    @staticmethod
    def _serialize(row: Any) -> dict:
        return {
            "id": row.id,
            "action_type": row.action_type,
            "payload": row.payload,
            "status": row.status,
            "error": row.error,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

"""AuditLogger — immutable record of every Fleetbase sync step."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.fleetbase_models import FleetbaseSyncAudit

logger = logging.getLogger(__name__)


class AuditLogger:
    @staticmethod
    def log(
        db: Session,
        *,
        direction: str,
        kind: str,
        status: str,
        order_id: str | None = None,
        fleetbase_order_id: str | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> FleetbaseSyncAudit:
        entry = FleetbaseSyncAudit(
            direction=direction,
            kind=kind,
            status=status,
            order_id=order_id,
            fleetbase_order_id=fleetbase_order_id,
            message=message,
            detail=detail or {},
        )
        db.add(entry)
        if commit:
            db.commit()
        logger.info("fleetbase-sync %s/%s %s order=%s %s", direction, kind, status, order_id, message or "")
        return entry

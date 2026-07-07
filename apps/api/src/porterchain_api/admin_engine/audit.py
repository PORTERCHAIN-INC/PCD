"""Central admin audit logging — all mutating admin actions."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog


def log_admin_audit(
    db: Session,
    ctx: AdminContext | None,
    *,
    action: str,
    resource_type: str,
    resource_id: str,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        AdminAuditLog(
            actor_user_id=ctx.user.id if ctx else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload or {},
        )
    )

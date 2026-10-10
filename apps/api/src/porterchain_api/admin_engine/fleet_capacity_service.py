"""Vehicle capacity table (system_config['dispatch_fleet']) — admin read/write."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def fleet_get(db: Session) -> dict[str, Any]:
    from porterchain_api.dispatch_engine.fleet_capacity import load_fleet

    return load_fleet(db)


def fleet_put(db: Session, ctx: Any, raw: dict[str, Any]) -> dict[str, Any]:
    from porterchain_api.admin_models import AdminAuditLog, SystemConfig
    from porterchain_api.dispatch_engine.fleet_capacity import STORAGE_KEY, normalize_fleet

    role = getattr(getattr(ctx, "role", None), "value", str(getattr(ctx, "role", "")))
    if role not in {"super_admin", "admin"}:
        raise PermissionError("fleet_capacity_admin_only")
    value = normalize_fleet(raw)
    row = db.get(SystemConfig, STORAGE_KEY)
    before = row.value if row is not None else None
    if row is None:
        db.add(SystemConfig(key=STORAGE_KEY, value=value))
    else:
        row.value = value
    db.add(
        AdminAuditLog(
            actor_user_id=ctx.user.id,
            action="settings.dispatch_fleet.updated",
            resource_type="system_config",
            resource_id=STORAGE_KEY,
            payload={"before": before, "after": value},
        )
    )
    db.commit()
    return value

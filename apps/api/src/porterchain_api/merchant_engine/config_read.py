"""Read-only SystemConfig values for merchant activation — no writes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import SystemConfig


def config_dict(db: Session, key: str) -> dict[str, Any]:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    value = getattr(row, "value", None) if row else None
    return value if isinstance(value, dict) else {}

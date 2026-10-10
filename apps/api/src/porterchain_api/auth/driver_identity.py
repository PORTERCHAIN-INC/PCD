"""Driver Clerk bind writes owned by admin_engine — auth façade so driver_engine does not import admin_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.driver_lookups import (
    bind_clerk_user_id as _bind_clerk_user_id,
)


def bind_clerk_user_id(db: Session, driver: Any, clerk_user_id: str) -> Any:
    return _bind_clerk_user_id(db, driver, clerk_user_id)

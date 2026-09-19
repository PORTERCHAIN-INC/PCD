"""Feature store — analytics stop legs removed (one-SoT cleanup)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def get_order_features(db: Session, order_id: str, *, flags: dict[str, bool]) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "features": {},
        "status": "analytics_tables_removed",
    }

"""Public-safe last-known driver pin for booking/merchant readers (no driver_engine import, D2)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def driver_pin(driver_id: str) -> dict[str, Any] | None:
    if not driver_id:
        return None
    try:
        from porterchain_api.driver_engine.last_known import read_last_known

        known = read_last_known(driver_id)
    except Exception:
        logger.debug("driver_pin read failed", exc_info=True)
        return None
    if known is None:
        return None
    return {
        "lat": known.lat,
        "lng": known.lng,
        "source": "last_known",
        "recorded_at": known.recorded_at.isoformat() if known.recorded_at else None,
    }

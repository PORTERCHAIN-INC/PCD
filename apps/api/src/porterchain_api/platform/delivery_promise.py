"""Checkout delivery promise read path (SystemConfig ``delivery_promise``).

Pure computation lives in ``porterchain_pricing.delivery_promise``; this module
only loads the super-admin setting. Any error or a disabled/missing setting
returns None so callers keep their previous fixed window.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

STORAGE_KEY = "delivery_promise"


def load_delivery_promise_config(db: Session) -> dict[str, Any] | None:
    from porterchain_api.admin_models import SystemConfig

    row = db.query(SystemConfig).filter(SystemConfig.key == STORAGE_KEY).first()
    value = getattr(row, "value", None)
    return value if isinstance(value, dict) else None


def checkout_promise(
    db: Session, *, dest_fsa: str | None, now: datetime | None = None
) -> Any:
    from porterchain_pricing.delivery_promise import compute_delivery_promise

    try:
        cfg = load_delivery_promise_config(db)
        if not cfg:
            return None
        return compute_delivery_promise(cfg, now=now or datetime.now(UTC), dest_fsa=dest_fsa)
    except Exception:  # noqa: BLE001
        logger.warning("delivery_promise_unavailable", exc_info=True)
        return None

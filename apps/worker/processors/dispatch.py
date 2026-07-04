"""Dispatch queue — reserved for outbound logistics jobs."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_dispatch(payload: dict[str, Any]) -> None:
    logger.info(
        "dispatch job: order_id=%s action=%s",
        payload.get("order_id"),
        payload.get("action"),
    )

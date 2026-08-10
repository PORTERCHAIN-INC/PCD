"""Dispatch queue — Fleetbase sync jobs (DD-05a)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def process_dispatch(payload: dict[str, Any]) -> None:
    order_id = payload.get("order_id")
    action = payload.get("action") or "dispatch_ready"
    if not order_id:
        logger.warning("dispatch job missing order_id: %s", payload)
        return

    if action == "score_suggestions":
        _score_suggestions(order_id)
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
    from porterchain_api.models import Order

    settings = get_settings()
    with SessionLocal() as db:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("dispatch job: order %s not found", order_id)
            return

        sync = BookingSyncService()
        if action == "assign":
            fleetbase_driver_id = _resolve_fleetbase_driver_id(db, settings, sync, payload.get("driver_id"))
            sync.push_driver_assignment(db, settings, order, fleetbase_driver_id=fleetbase_driver_id)
        else:
            sync.push_order(db, settings, order)
        db.commit()

    logger.info("dispatch job completed: order_id=%s action=%s", order_id, action)


def _score_suggestions(order_id: str) -> None:
    """P1-2: Valhalla-matrix ranking + capability/skills/window filters → Redis cache."""
    from porterchain_api.admin_engine.control_tower.scoring import (
        compute_ranked_suggestions,
        write_suggestions_cache,
    )
    from porterchain_api.db import SessionLocal

    with SessionLocal() as db:
        try:
            result = compute_ranked_suggestions(db, order_id)
        except LookupError:
            logger.warning("score_suggestions: order %s not found", order_id)
            return
        write_suggestions_cache(order_id, result)
    logger.info(
        "score_suggestions completed: order_id=%s drivers=%s filtered=%s matrix=%s",
        order_id,
        len(result.get("drivers") or []),
        result.get("filtered_out_count"),
        result.get("matrix_source"),
    )


def _resolve_fleetbase_driver_id(db, settings, sync, driver_id: str | None) -> str | None:
    if not driver_id:
        return None
    from porterchain_api.admin_models import Driver

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        logger.warning("dispatch assign: driver %s not found", driver_id)
        return None
    if not driver.fleetbase_driver_id:
        sync.push_driver(db, settings, driver)
        db.refresh(driver)
    return driver.fleetbase_driver_id

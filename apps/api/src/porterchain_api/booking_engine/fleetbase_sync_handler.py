"""Fleetbase sync event handlers — react to order events, never called directly."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def sync_order_from_event(envelope: dict[str, Any]) -> None:
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.models import Order
    from porterchain_api.booking_engine.fleetbase_sync_service import FleetbaseSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("fleetbase handler: order %s not found", order_id)
            return
        settings = get_settings()
        FleetbaseSyncService().sync_order(db, settings, order)
    finally:
        db.close()


def sync_driver_assignment_from_event(envelope: dict[str, Any]) -> None:
    order_id = envelope.get("aggregate_id")
    driver_id = envelope.get("payload", {}).get("driver_id")
    if not order_id:
        return

    from porterchain_api.admin_models import Driver
    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.models import Order
    from porterchain_api.booking_engine.fleetbase_sync_service import FleetbaseSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        settings = get_settings()
        sync = FleetbaseSyncService()
        sync.sync_order(db, settings, order)
        if driver_id:
            driver = db.query(Driver).filter(Driver.id == driver_id).first()
            if driver and not driver.fleetbase_driver_id:
                sync.sync_driver(db, settings, driver)
            if order.fleetbase_order_id and driver and driver.fleetbase_driver_id:
                sync.sync_dispatch(settings, order, fleetbase_driver_id=driver.fleetbase_driver_id)
    finally:
        db.close()


def apply_fleetbase_webhook_from_event(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    if payload.get("source") != "fleetbase":
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.fleetbase_engine import WebhookProcessor

    db = SessionLocal()
    try:
        update = payload.get("update")
        if not update:
            return
        WebhookProcessor().process(db, get_settings(), update, payload.get("raw"))
    finally:
        db.close()

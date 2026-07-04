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
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            logger.warning("fleetbase handler: order %s not found", order_id)
            return
        settings = get_settings()
        BookingSyncService().push_order(db, settings, order)
    finally:
        db.close()


def sync_cancellation_from_event(envelope: dict[str, Any]) -> None:
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.models import Order
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        BookingSyncService().sync_cancellation(db, get_settings(), order)
    finally:
        db.close()


def sync_return_from_event(envelope: dict[str, Any]) -> None:
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.models import Order
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        BookingSyncService().sync_return(db, get_settings(), order)
    finally:
        db.close()


def sync_damage_from_event(envelope: dict[str, Any]) -> None:
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.models import Order
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        BookingSyncService().sync_damage(db, get_settings(), order)
    finally:
        db.close()


def sync_claim_from_event(envelope: dict[str, Any]) -> None:
    claim_id = envelope.get("aggregate_id")
    order_id = envelope.get("payload", {}).get("order_id")
    if not order_id:
        return

    from porterchain_api.config import get_settings
    from porterchain_api.db import SessionLocal
    from porterchain_api.models import Order
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        BookingSyncService().sync_claim(db, get_settings(), order, claim_id=claim_id)
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
    from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return
        settings = get_settings()
        sync = BookingSyncService()
        sync.push_order(db, settings, order)
        db.refresh(order)
        if driver_id:
            driver = db.query(Driver).filter(Driver.id == driver_id).first()
            if driver and not driver.fleetbase_driver_id:
                sync.push_driver(db, settings, driver)
                db.refresh(driver)
            if driver and driver.fleetbase_driver_id and order.fleetbase_order_id:
                sync.push_driver_assignment(
                    db, settings, order, fleetbase_driver_id=driver.fleetbase_driver_id
                )
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

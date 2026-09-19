"""Persist Fleetbase IDs on Driver/Vehicle rows owned by admin_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def persist_driver_fleetbase_id(db: Session, driver: Any, fleetbase_id: str) -> None:
    driver.fleetbase_driver_id = fleetbase_id
    db.commit()
    db.refresh(driver)


def persist_vehicle_fleetbase_id(db: Session, vehicle: Any, fleetbase_id: str) -> None:
    vehicle.fleetbase_vehicle_id = fleetbase_id
    db.commit()
    db.refresh(vehicle)

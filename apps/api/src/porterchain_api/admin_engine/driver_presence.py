"""Keep Driver.is_online warm from PorterChain duty (open shift), not Fleetbase."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_models import DriverShift

logger = logging.getLogger(__name__)

_SHIFT_LOOKBACK = timedelta(hours=12)


def sync_online_from_duty(db: Session) -> None:
    """Set is_online from an open shift for approved drivers."""
    since = datetime.now(UTC) - _SHIFT_LOOKBACK
    try:
        open_ids = {
            row[0]
            for row in db.query(DriverShift.driver_id)
            .filter(DriverShift.started_at >= since, DriverShift.ended_at.is_(None))
            .distinct()
            .all()
        }
        rows = (
            db.query(Driver)
            .filter(Driver.status == DriverStatus.APPROVED.value)
            .all()
        )
        dirty = False
        for driver in rows:
            want = driver.id in open_ids
            if bool(driver.is_online) != want:
                driver.is_online = want
                driver.availability = "online" if want else "offline"
                dirty = True
        if dirty:
            db.commit()
    except Exception:
        logger.debug("duty presence sync failed", exc_info=True)
        db.rollback()


def patch_online_from_fleetbase(db: Session, fleetbase_drivers: list) -> None:
    """Deprecated no-op — Fleetbase online flags are no longer the source."""
    del db, fleetbase_drivers

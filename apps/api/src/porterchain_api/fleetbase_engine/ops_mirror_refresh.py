"""Worker-owned refresh of the Fleetbase ops Redis mirror.

All leftover GET HTTP (list_drivers, tracking, zones, position_history)
runs here — never on the API request thread.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine import ops_mirror
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import IN_FLIGHT
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)

ACTIVE_ORDER_CAP = 200
DRIVER_LIST_LIMIT = 300
HISTORY_CAP = 50  # position_history is heavier; refresh a subset per tick
TRACKING_FRESH_SECONDS = 30
HISTORY_INTERVAL_SECONDS = 60


class OpsMirrorRefreshService:
    def refresh(self, db: Session, settings: Settings) -> dict[str, Any]:
        if not settings.fleetbase_dispatch_bridge:
            return {"skipped": True, "reason": "bridge_off"}

        adapter = get_fleetbase_integration(settings)
        if not adapter.is_enabled:
            return {"skipped": True, "reason": "adapter_disabled"}

        drivers_n = self._refresh_drivers(db, adapter)
        zones_n = self._refresh_zones(adapter)
        tracking_n, history_n, skipped_tracking, history_refreshed_at = self._refresh_orders(
            db, adapter
        )

        ops_mirror.write_meta(
            refreshed_at=datetime.now(UTC).isoformat(),
            drivers=drivers_n,
            zones=zones_n,
            tracking=tracking_n,
            history=history_n,
            tracking_skipped=skipped_tracking,
            history_refreshed_at=history_refreshed_at,
        )
        return {
            "skipped": False,
            "drivers": drivers_n,
            "zones": zones_n,
            "tracking": tracking_n,
            "history": history_n,
            "tracking_skipped": skipped_tracking,
        }

    def _refresh_drivers(self, db: Session, adapter: Any) -> int:
        try:
            fleetbase_drivers = adapter.list_drivers(limit=DRIVER_LIST_LIMIT)
        except Exception as exc:
            logger.warning("ops_mirror list_drivers failed: %s", exc)
            return 0

        if not isinstance(fleetbase_drivers, list):
            fleetbase_drivers = []

        ops_mirror.write_drivers(fleetbase_drivers)
        from porterchain_api.admin_engine.driver_presence import patch_online_from_fleetbase

        patch_online_from_fleetbase(db, fleetbase_drivers)
        return len(fleetbase_drivers)

    def _refresh_zones(self, adapter: Any) -> int:
        try:
            zones = adapter.list_zone_overlays()
        except Exception as exc:
            logger.warning("ops_mirror list_zone_overlays failed: %s", exc)
            return 0
        if not isinstance(zones, list):
            zones = []
        ops_mirror.write_zones(zones)
        return len(zones)

    def _last_known_fresh(self, driver: Driver | None, now: datetime) -> bool:
        if driver is None:
            return False
        from porterchain_api.driver_engine.last_known import read_last_known

        known = read_last_known(driver.id)
        if known is None:
            return False
        return (now - known.recorded_at).total_seconds() < TRACKING_FRESH_SECONDS

    def _refresh_orders(self, db: Session, adapter: Any) -> tuple[int, int, int, str | None]:
        from porterchain_api.driver_engine.last_known import parse_recorded_at

        orders = (
            db.query(Order)
            .filter(
                Order.state.in_(IN_FLIGHT),
                Order.fleetbase_order_id.isnot(None),
            )
            .order_by(Order.scheduled_at.asc())
            .limit(ACTIVE_ORDER_CAP)
            .all()
        )

        now = datetime.now(UTC)
        meta = ops_mirror.read_meta() or {}
        prev_hist = parse_recorded_at(meta.get("history_refreshed_at"))
        history_due = (
            prev_hist is None or (now - prev_hist).total_seconds() >= HISTORY_INTERVAL_SECONDS
        )
        history_refreshed_at = meta.get("history_refreshed_at")
        if not isinstance(history_refreshed_at, str):
            history_refreshed_at = None

        tracking_n = 0
        history_n = 0
        skipped_tracking = 0
        for i, order in enumerate(orders):
            fb_id = order.fleetbase_order_id
            if not fb_id:
                continue
            driver = db.get(Driver, order.assigned_driver_id) if order.assigned_driver_id else None
            if self._last_known_fresh(driver, now):
                existing, _src = ops_mirror.read_tracking(fb_id)
                if existing:
                    ops_mirror.write_tracking(fb_id, existing)
                skipped_tracking += 1
                tracking_n += 1
            else:
                try:
                    payload = adapter.fetch_tracking(fb_id)
                    ops_mirror.write_tracking(fb_id, payload if isinstance(payload, dict) else {})
                    tracking_n += 1
                except Exception as exc:
                    logger.debug("ops_mirror fetch_tracking %s failed: %s", fb_id, exc)

            if not history_due or i >= HISTORY_CAP:
                continue
            subject_uuid: str | None = None
            if driver and driver.fleetbase_driver_id:
                subject_uuid = driver.fleetbase_driver_id
            try:
                hist = adapter.position_history(
                    order_uuid=fb_id,
                    subject_uuid=subject_uuid,
                )
                if isinstance(hist, dict):
                    ops_mirror.write_history(fb_id, hist)
                    history_n += 1
            except Exception as exc:
                logger.debug("ops_mirror position_history %s failed: %s", fb_id, exc)

        if history_due:
            history_refreshed_at = now.isoformat()
        return tracking_n, history_n, skipped_tracking, history_refreshed_at

"""Fleetbase bridge for driver platform — enqueue mutating sync; no request-path GET."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration


class DriverFleetbaseBridge:
    """Mutating methods enqueue RetryQueue (drain owns HTTP). Navigation uses Valhalla/OSRM."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._adapter = get_fleetbase_integration(settings)

    @property
    def enabled(self) -> bool:
        return bool(self._settings.fleetbase_dispatch_bridge and self._adapter.is_enabled)

    def track_driver_location(
        self,
        db: Session,
        *,
        driver_id: str,
        fleetbase_driver_id: str,
        lat: float,
        lng: float,
        heading: float | None = None,
        speed: float | None = None,
        recorded_at: str | None = None,
    ) -> bool:
        if not self.enabled:
            return False
        ts = recorded_at or datetime.now(UTC).isoformat()
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="tracking",
            idempotency_key=f"tracking:{driver_id}",
            payload={
                "fleetbase_driver_id": fleetbase_driver_id,
                "driver_id": driver_id,
                "lat": lat,
                "lng": lng,
                "heading": heading,
                "speed": speed,
                "recorded_at": ts,
            },
            commit=False,
        )
        return True

    def toggle_driver_online(
        self,
        db: Session,
        *,
        driver_id: str,
        fleetbase_driver_id: str,
        online: bool,
    ) -> bool:
        if not self.enabled:
            return False
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="driver_online",
            idempotency_key=f"driver_online:{driver_id}",
            payload={
                "fleetbase_driver_id": fleetbase_driver_id,
                "driver_id": driver_id,
                "online": online,
            },
            commit=False,
        )
        return True

    def fetch_route(self, fleetbase_order_id: str) -> dict | None:
        """Removed from request path. Kept as a no-op so old callers cannot HTTP."""
        del fleetbase_order_id
        return None

    def upload_pod_photo(
        self,
        db: Session,
        *,
        order_id: str,
        fleetbase_order_id: str,
        file_url: str,
    ) -> bool:
        if not self.enabled:
            return False
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="pod_photo",
            order_id=order_id,
            fleetbase_order_id=fleetbase_order_id,
            idempotency_key=f"pod_photo:{order_id}",
            payload={
                "order_id": order_id,
                "fleetbase_order_id": fleetbase_order_id,
                "file_url": file_url,
            },
            commit=False,
        )
        return True

    def upload_pod_signature(
        self,
        db: Session,
        *,
        order_id: str,
        fleetbase_order_id: str,
        signature_data: str,
    ) -> bool:
        if not self.enabled:
            return False
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="pod_signature",
            order_id=order_id,
            fleetbase_order_id=fleetbase_order_id,
            idempotency_key=f"pod_signature:{order_id}",
            payload={
                "order_id": order_id,
                "fleetbase_order_id": fleetbase_order_id,
                "signature_data": signature_data,
            },
            commit=False,
        )
        return True

    def upload_pod_barcode(
        self,
        db: Session,
        *,
        order_id: str,
        fleetbase_order_id: str,
        barcode: str,
    ) -> bool:
        if not self.enabled:
            return False
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="pod_barcode",
            order_id=order_id,
            fleetbase_order_id=fleetbase_order_id,
            idempotency_key=f"pod_barcode:{order_id}",
            payload={
                "order_id": order_id,
                "fleetbase_order_id": fleetbase_order_id,
                "barcode": barcode,
            },
            commit=False,
        )
        return True

    def sync_order_state(
        self,
        db: Session,
        *,
        order_id: str,
        fleetbase_order_id: str,
        order_state: str,
    ) -> bool:
        """Enqueue order-state mirror. HTTP in drain via kind=order_state."""
        if not self.enabled:
            return False
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="order_state",
            order_id=order_id,
            fleetbase_order_id=fleetbase_order_id,
            idempotency_key=f"order_state:{order_id}",
            payload={
                "order_id": order_id,
                "fleetbase_order_id": fleetbase_order_id,
                "order_state": order_state,
            },
            commit=False,
        )
        return True

"""Phase 3: GPS/POD/shift enqueue; GPS LWW by recorded_at; ping INSERT off by default."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.driver_engine.fleetbase_bridge import DriverFleetbaseBridge
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.fleetbase_models import FleetbaseSyncJob


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=True,
        fleetbase_api_key="test-key",
    )


def test_gps_skips_ping_insert_and_enqueues_tracking(db: Session, driver) -> None:
    from porterchain_driver.location import LocationService

    driver.fleetbase_driver_id = f"fb-{uuid4().hex[:8]}"
    db.flush()
    settings = _settings()
    bridge = DriverFleetbaseBridge(settings)
    # Pretend adapter enabled
    bridge._adapter = MagicMock(is_enabled=True)

    result = LocationService().record_ping(
        db,
        driver,
        lat=43.65,
        lng=-79.38,
        fleetbase_bridge=bridge,
    )
    db.flush()
    assert result["recorded"] is True
    assert result["ping_id"] is None

    from porterchain_api.driver_models import DriverLocationPing

    leftover = (
        db.query(DriverLocationPing)
        .filter(DriverLocationPing.driver_id == driver.id)
        .count()
    )
    assert leftover == 0

    jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"tracking:{driver.id}")
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].kind == "tracking"
    assert jobs[0].payload["lat"] == 43.65
    db.rollback()


def test_gps_lww_keeps_newer_recorded_at(db: Session) -> None:
    key = f"tracking:drv-{uuid4().hex[:8]}"
    RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 1.0, "lng": 1.0, "recorded_at": "2026-09-12T12:00:25Z"},
        commit=False,
    )
    RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 0.5, "lng": 0.5, "recorded_at": "2026-09-12T12:00:00Z"},
        commit=False,
    )
    jobs = db.query(FleetbaseSyncJob).filter(FleetbaseSyncJob.idempotency_key == key).all()
    assert len(jobs) == 1
    assert jobs[0].payload["lat"] == 1.0
    db.rollback()


def test_pod_photo_enqueues_without_http(db: Session, driver, dispatch_order) -> None:
    from porterchain_driver.pod import ProofOfDeliveryService

    dispatch_order.assigned_driver_id = driver.id
    dispatch_order.fleetbase_order_id = "fb-ord-1"
    db.flush()
    settings = _settings()
    bridge = DriverFleetbaseBridge(settings)
    bridge._adapter = MagicMock(is_enabled=True)

    stop_id = f"{dispatch_order.id}-dropoff"
    result = ProofOfDeliveryService().capture_photo(
        db, driver, stop_id, file_url="https://example.com/p.jpg", fleetbase_bridge=bridge
    )
    db.flush()
    assert result.success
    assert result.fleetbase_synced is True
    bridge._adapter.upload_pod_photo.assert_not_called()
    job = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"pod_photo:{dispatch_order.id}")
        .first()
    )
    assert job is not None
    db.rollback()


def test_toggle_online_enqueues(db: Session, driver) -> None:
    driver.fleetbase_driver_id = "fb-drv"
    db.flush()
    settings = _settings()
    bridge = DriverFleetbaseBridge(settings)
    bridge._adapter = MagicMock(is_enabled=True)
    ok = bridge.toggle_driver_online(
        db, driver_id=driver.id, fleetbase_driver_id=driver.fleetbase_driver_id, online=True
    )
    db.flush()
    assert ok is True
    bridge._adapter.toggle_driver_online.assert_not_called()
    job = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"driver_online:{driver.id}")
        .first()
    )
    assert job is not None
    assert job.payload["online"] is True
    db.rollback()

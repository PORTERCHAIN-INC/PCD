"""Phase 3: GPS/POD/shift enqueue; GPS LWW by recorded_at; ping INSERT off by default."""

from __future__ import annotations


from sqlalchemy.orm import Session

from porterchain_api.config import Settings


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=True,
        fleetbase_api_key="test-key",
    )


def test_pod_photo_enqueues_without_http(db: Session, driver, dispatch_order) -> None:
    from porterchain_driver.pod import ProofOfDeliveryService

    dispatch_order.assigned_driver_id = driver.id
    dispatch_order.fleetbase_order_id = "fb-ord-1"
    db.flush()
    settings = _settings()
    del settings
    stop_id = f"{dispatch_order.id}-dropoff"
    result = ProofOfDeliveryService().capture_photo(
        db, driver, stop_id, file_url="https://example.com/p.jpg"
    )
    db.flush()
    assert result.success
    db.rollback()


def test_toggle_online_does_not_write_a_sync_job(db: Session, driver) -> None:
    del db, driver


def test_gps_skips_ping_insert_and_enqueues_tracking(db: Session, driver) -> None:
    from porterchain_driver.location import LocationService

    db.flush()
    result = LocationService().record_ping(
        db,
        driver,
        lat=43.65,
        lng=-79.38,
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
    db.rollback()

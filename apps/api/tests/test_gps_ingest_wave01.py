"""Wave 0–1 GPS ingest: commit, last-known CAS, no LWW on claimed tracking jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.db import SessionLocal, db_transaction
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.driver_engine.last_known import (
    LastKnown,
    parse_recorded_at,
    read_last_known,
    write_last_known,
)
from porterchain_api.driver_models import DriverLocationPing
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue, _find_inflight
from porterchain_api.fleetbase_models import FleetbaseSyncJob


class _FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.kv: dict[str, str] = {}

    def eval(self, _script: str, _numkeys: int, *args: str) -> int:
        key = args[0]
        new_epoch = float(args[2])
        current = self.hashes.get(key, {})
        old = current.get("recorded_at_epoch")
        if old and float(old) >= new_epoch:
            return 0
        ver = int(float(current.get("version") or 0)) + 1
        self.hashes[key] = {
            "lat": args[3],
            "lng": args[4],
            "recorded_at": args[5],
            "recorded_at_epoch": args[2],
            "accuracy_m": args[6],
            "heading": args[7],
            "speed_mps": args[8],
            "fleetbase_driver_id": args[9],
            "h3": args[10],
            "version": str(ver),
        }
        return ver

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def get(self, key: str) -> str | None:
        return self.kv.get(key)

    def setex(self, key: str, _ttl: int, value: str) -> None:
        self.kv[key] = value


@pytest.fixture
def driver(db: Session) -> Driver:
    suffix = uuid4().hex[:8]
    row = Driver(
        email=f"driver-{suffix}@gps.test",
        full_name=f"Driver {suffix}",
        status=DriverStatus.APPROVED.value,
        clerk_user_id=f"clerk_driver_{suffix}",
        is_online=True,
        license_verified=True,
        insurance_verified=True,
        background_check_status="cleared",
    )
    db.add(row)
    db.flush()
    return row


def _has_inflight_unique(db: Session) -> bool:
    row = db.execute(
        text(
            "SELECT 1 FROM pg_indexes "
            "WHERE indexname = 'uq_fleetbase_sync_jobs_inflight_idempotency'"
        )
    ).first()
    return row is not None


def test_parse_recorded_at_treats_z_and_offset_as_utc() -> None:
    a = parse_recorded_at("2026-09-12T12:00:25Z")
    b = parse_recorded_at("2026-09-12T12:00:25+00:00")
    assert a is not None and b is not None
    assert a == b
    older = parse_recorded_at("2026-09-12T12:00:00Z")
    assert older is not None
    assert older < a


def test_last_known_cas_rejects_stale_ping() -> None:
    redis = _FakeRedis()
    first = write_last_known(
        driver_id="drv-1",
        lat=43.65,
        lng=-79.38,
        recorded_at="2026-09-14T12:00:25Z",
        fleetbase_driver_id="fb-1",
        client=redis,
    )
    assert first is not None
    assert first.version == 1
    stale = write_last_known(
        driver_id="drv-1",
        lat=43.0,
        lng=-79.0,
        recorded_at="2026-09-14T12:00:00Z",
        client=redis,
    )
    assert stale is None
    known = read_last_known("drv-1", client=redis)
    assert known is not None
    assert known.lat == 43.65
    newer = write_last_known(
        driver_id="drv-1",
        lat=43.7,
        lng=-79.4,
        recorded_at="2026-09-14T12:00:50Z",
        client=redis,
    )
    assert newer is not None
    assert newer.version == 2
    assert read_last_known("drv-1", client=redis).lat == 43.7


def test_record_ping_survives_commit(db: Session, driver: Driver) -> None:
    from unittest.mock import MagicMock

    from porterchain_api.config import Settings
    from porterchain_api.driver_engine.fleetbase_bridge import DriverFleetbaseBridge
    from porterchain_driver.location import LocationService

    driver.fleetbase_driver_id = f"fb-{uuid4().hex[:8]}"
    db.flush()
    settings = Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=True,
        fleetbase_api_key="test-key",
    )
    bridge = DriverFleetbaseBridge(settings)
    bridge._adapter = MagicMock(is_enabled=True)
    with db_transaction(db):
        result = LocationService().record_ping(
            db, driver, lat=43.65, lng=-79.38, fleetbase_bridge=bridge
        )
    assert result["recorded"] is True
    assert result["ping_id"] is None
    assert "recorded_at" in result
    key = f"tracking:{driver.id}"
    other = SessionLocal()
    try:
        jobs = (
            other.query(FleetbaseSyncJob)
            .filter(FleetbaseSyncJob.idempotency_key == key)
            .all()
        )
        assert len(jobs) == 1
        assert jobs[0].payload["lat"] == 43.65
        leftover = (
            other.query(DriverLocationPing)
            .filter(DriverLocationPing.driver_id == driver.id)
            .count()
        )
        assert leftover == 0
    finally:
        other.query(FleetbaseSyncJob).filter(FleetbaseSyncJob.idempotency_key == key).delete()
        other.commit()
        other.close()


def test_enqueue_lww_uses_datetime_not_string_order(db: Session) -> None:
    key = f"tracking:ts-{uuid4().hex[:8]}"
    RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 1.0, "lng": 1.0, "recorded_at": "2026-09-12T12:00:25+00:00"},
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


def test_enqueue_does_not_lww_claimed_tracking_job(db: Session) -> None:
    key = f"tracking:claimed-{uuid4().hex[:8]}"
    job = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={
            "driver_id": "drv-claimed",
            "fleetbase_driver_id": "fb-1",
            "lat": 43.0,
            "lng": -79.0,
            "recorded_at": "2026-09-14T12:00:00Z",
        },
        commit=False,
    )
    db.flush()
    claimed = RetryQueue.claim_due(db, limit=500)
    assert any(c.id == job.id for c in claimed)
    RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={
            "driver_id": "drv-claimed",
            "fleetbase_driver_id": "fb-1",
            "lat": 43.5,
            "lng": -79.5,
            "recorded_at": "2026-09-14T12:00:25Z",
        },
        commit=False,
    )
    db.expire_all()
    refreshed = db.get(FleetbaseSyncJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "retrying"
    assert refreshed.payload["lat"] == 43.0
    db.query(FleetbaseSyncJob).filter(FleetbaseSyncJob.idempotency_key == key).delete()
    db.commit()


def test_enqueue_integrity_error_retries_as_lww(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    if not _has_inflight_unique(db):
        pytest.skip("uq_fleetbase_sync_jobs_inflight_idempotency not applied")
    key = f"tracking:race-{uuid4().hex[:8]}"
    first = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 1.0, "lng": 1.0, "recorded_at": "2026-09-14T12:00:00Z"},
        commit=False,
    )
    db.flush()
    calls = {"n": 0}
    real = _find_inflight

    def skip_first(session: Session, idempotency_key: str):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real(session, idempotency_key)

    monkeypatch.setattr(
        "porterchain_api.fleetbase_engine.retry_queue._find_inflight", skip_first
    )
    second = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 2.0, "lng": 2.0, "recorded_at": "2026-09-14T12:00:25Z"},
        commit=False,
    )
    assert second.id == first.id
    assert second.payload["lat"] == 2.0
    db.rollback()


def test_inflight_idempotency_unique(db: Session) -> None:
    if not _has_inflight_unique(db):
        pytest.skip("uq_fleetbase_sync_jobs_inflight_idempotency not applied")
    key = f"tracking:uniq-{uuid4().hex[:8]}"
    db.add(
        FleetbaseSyncJob(
            direction="outbound",
            kind="tracking",
            payload={"lat": 1.0},
            idempotency_key=key,
            status="pending",
        )
    )
    db.flush()
    db.add(
        FleetbaseSyncJob(
            direction="outbound",
            kind="tracking",
            payload={"lat": 2.0},
            idempotency_key=key,
            status="pending",
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_tracking_drain_reenqueues_newer_last_known(db: Session) -> None:
    driver_id = f"drv-{uuid4().hex[:8]}"
    key = f"tracking:{driver_id}"
    sent = "2026-09-14T12:00:00+00:00"
    later = datetime(2026, 9, 14, 12, 0, 25, tzinfo=UTC)
    job = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={
            "driver_id": driver_id,
            "fleetbase_driver_id": "fb-1",
            "lat": 43.0,
            "lng": -79.0,
            "recorded_at": sent,
        },
        commit=False,
    )
    db.flush()
    RetryQueue.mark_done(db, job)
    leftover = LastKnown(
        driver_id=driver_id,
        lat=43.8,
        lng=-79.4,
        recorded_at=later,
        fleetbase_driver_id="fb-1",
    )
    with patch(
        "porterchain_api.driver_engine.last_known.read_last_known",
        return_value=leftover,
    ):
        BookingSyncService._reenqueue_if_last_known_newer(db, job)

    pending = (
        db.query(FleetbaseSyncJob)
        .filter(
            FleetbaseSyncJob.idempotency_key == key,
            FleetbaseSyncJob.status == "pending",
        )
        .all()
    )
    assert len(pending) == 1
    assert pending[0].payload["lat"] == 43.8
    db.query(FleetbaseSyncJob).filter(FleetbaseSyncJob.idempotency_key == key).delete()
    db.commit()


def test_claim_due_kinds_splits_tracking_from_commercial(db: Session) -> None:
    tkey = f"tracking:split-{uuid4().hex[:8]}"
    okey = f"order:split-{uuid4().hex[:8]}"
    track = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=tkey,
        payload={"lat": 1.0, "lng": 1.0, "recorded_at": "2026-09-14T12:00:00Z"},
        commit=False,
    )
    order = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="order",
        idempotency_key=okey,
        payload={"order_id": "ord-1"},
        commit=False,
    )
    db.flush()
    tracking_ids = {c.id for c in RetryQueue.claim_due(db, limit=500, kinds=["tracking"])}
    assert track.id in tracking_ids
    assert order.id not in tracking_ids
    commercial_ids = {
        c.id for c in RetryQueue.claim_due(db, limit=500, exclude_kinds=["tracking"])
    }
    assert order.id in commercial_ids
    assert track.id not in commercial_ids
    db.query(FleetbaseSyncJob).filter(FleetbaseSyncJob.idempotency_key.in_([tkey, okey])).delete()
    db.commit()


def test_write_ping_table_flag_still_inserts(db: Session, driver: Driver) -> None:
    from porterchain_driver.location import LocationService

    result = LocationService().record_ping(
        db, driver, lat=43.65, lng=-79.38, write_ping_table=True
    )
    db.flush()
    assert result["ping_id"]
    ping = db.get(DriverLocationPing, result["ping_id"])
    assert ping is not None
    assert ping.lat == 43.65
    db.rollback()


def test_next_stop_origin_prefers_last_known(monkeypatch: pytest.MonkeyPatch) -> None:
    from porterchain_driver.next_stop import NextStopResolver

    known = LastKnown(
        driver_id="drv-1",
        lat=43.7,
        lng=-79.4,
        recorded_at=datetime(2026, 9, 14, 12, 0, tzinfo=UTC),
    )
    monkeypatch.setattr(
        "porterchain_api.driver_engine.last_known.read_last_known",
        lambda _driver_id: known,
    )
    origin = NextStopResolver()._driver_origin(MagicMock(), "drv-1", [])
    assert origin == (43.7, -79.4)


def test_worker_splits_tracking_drain() -> None:
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "worker" / "run.py").read_text()
    assert "TRACKING_KIND" in src
    assert "exclude_kinds=" in src
    assert "kinds=[TRACKING_KIND]" in src
    assert "TRACKING_DRAIN_LIMIT" in src


def test_offline_gps_buffer_keeps_latest_only() -> None:
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[2] / "driver-portal" / "src" / "lib" / "offline-client.ts"
    ).read_text()
    assert "buffer.length > 500" not in src
    assert "JSON.stringify([stamped])" in src
    assert "gpsBuffer[gpsBuffer.length - 1]" in src

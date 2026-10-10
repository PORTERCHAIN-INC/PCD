"""Wave 0–1 GPS ingest: commit, last-known CAS, no LWW on claimed tracking jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api import crm_models, merchant_models, user_models  # noqa: F401 — FK targets
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
            "h3": args[9],
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


def test_worker_does_not_drain_a_sync_queue() -> None:
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "worker" / "run.py").read_text()
    assert "TRACKING_KIND" not in src
    assert "_drain_fleetbase_retry_queue" not in src


def test_offline_gps_buffer_keeps_latest_only() -> None:
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[2] / "driver-portal" / "src" / "lib" / "offline-client.ts"
    ).read_text()
    assert "buffer.length > 500" not in src
    assert "JSON.stringify([stamped])" in src
    assert "gpsBuffer[gpsBuffer.length - 1]" in src


def test_last_known_cas_rejects_stale_ping() -> None:
    redis = _FakeRedis()
    first = write_last_known(
        driver_id="drv-1",
        lat=43.65,
        lng=-79.38,
        recorded_at="2026-09-14T12:00:25Z",
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
    from porterchain_driver.location import LocationService

    db.flush()
    settings = Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
    )
    with db_transaction(db):
        result = LocationService().record_ping(
            db, driver, lat=43.65, lng=-79.38
        )
    assert result["recorded"] is True
    assert result["ping_id"] is None
    other = SessionLocal()
    try:
        leftover = (
            other.query(DriverLocationPing)
            .filter(DriverLocationPing.driver_id == driver.id)
            .count()
        )
        assert leftover == 0
    finally:
        other.close()

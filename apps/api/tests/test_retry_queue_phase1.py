"""Phase 1 RetryQueue: LWW payload update, claim lease, new drain kinds."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_engine.retry_queue import CLAIM_LEASE_SECONDS, RetryQueue
from porterchain_api.fleetbase_models import FleetbaseSyncJob


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=False,
    )


def test_enqueue_lww_updates_payload_on_existing_pending(db: Session) -> None:
    key = f"tracking:driver-{uuid4().hex[:8]}"
    first = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 43.0, "lng": -79.0, "recorded_at": "2026-01-01T00:00:00Z"},
        commit=False,
    )
    db.flush()
    second = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=key,
        payload={"lat": 43.1, "lng": -79.1, "recorded_at": "2026-01-01T00:00:25Z"},
        commit=False,
    )
    db.flush()
    assert first.id == second.id
    assert second.payload["lat"] == 43.1
    assert second.payload["lng"] == -79.1
    count = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == key)
        .count()
    )
    assert count == 1
    db.rollback()


def test_claim_due_sets_lease_so_job_is_not_immediately_due_again(db: Session) -> None:
    job = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        idempotency_key=f"tracking:lease-{uuid4().hex[:8]}",
        payload={"fleetbase_driver_id": "fb-d1", "lat": 1.0, "lng": 2.0},
        commit=False,
    )
    db.flush()

    # Shared test DB may have other due jobs — claim enough to include ours.
    claimed = RetryQueue.claim_due(db, limit=500)
    assert any(c.id == job.id for c in claimed)
    db.expire_all()
    refreshed = db.get(FleetbaseSyncJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "retrying"
    assert refreshed.next_attempt_at is not None
    # Still under lease → due() should not return it.
    due = RetryQueue.due(db, limit=500)
    assert all(d.id != job.id for d in due)
    db.rollback()


def test_new_drain_kinds_are_not_unhandled(db: Session) -> None:
    """Kinds Phase 3 will enqueue must not dead-letter as unhandled_retry_kind."""
    job = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="tracking",
        # Missing fleetbase_driver_id → handled branch raises a typed error, not unhandled.
        payload={"lat": 43.0, "lng": -79.0},
        idempotency_key=f"tracking:kind-{uuid4().hex[:6]}",
        commit=False,
    )
    db.flush()

    BookingSyncService().process_retry_queue(db, _settings(), limit=500)
    db.expire_all()
    refreshed = db.get(FleetbaseSyncJob, job.id)
    assert refreshed is not None
    assert refreshed.status in ("retrying", "dead")
    assert "unhandled_retry_kind" not in (refreshed.last_error or "")
    assert "tracking_missing_fleetbase_driver_id" in (refreshed.last_error or "")
    db.rollback()


def test_claim_lease_constant_is_sixty_seconds() -> None:
    assert CLAIM_LEASE_SECONDS == 60
    assert timedelta(seconds=CLAIM_LEASE_SECONDS).total_seconds() == 60


def test_requeue_dead_is_superseded_when_inflight_has_same_key(db: Session) -> None:
    from porterchain_api.fleetbase_engine.retry_queue import ErrorQueue

    key = f"order:{uuid4()}"
    live = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="order",
        idempotency_key=key,
        payload={"order_id": "live"},
        commit=False,
    )
    db.flush()
    dead = FleetbaseSyncJob(
        direction="outbound",
        kind="order",
        payload={"order_id": "dead"},
        idempotency_key=key,
        status="dead",
        attempts=5,
        last_error="fleetbase_order_id_not_returned",
    )
    db.add(dead)
    db.flush()

    result = ErrorQueue.requeue(db, dead.id)
    db.expire_all()
    dead = db.get(FleetbaseSyncJob, dead.id)
    assert result is not None
    assert result.id == live.id
    assert result.status in ("pending", "retrying")
    assert dead is not None
    assert dead.status == "done"
    assert "superseded_by_inflight" in (dead.last_error or "")
    db.rollback()

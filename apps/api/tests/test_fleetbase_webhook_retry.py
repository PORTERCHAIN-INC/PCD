"""
Inbound Fleetbase webhook retries.

`kind="webhook"` jobs matched no branch in `process_retry_queue`, fell through to
`mark_done` and were counted as processed — so a failed driver status or POD
update was discarded while the queue reported success.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.fleetbase_models import FleetbaseSyncJob
from porterchain_api.booking_models import Order


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=False,
    )


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _make_order(db: Session) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        fleetbase_order_id=f"fb-{uuid4().hex[:8]}",
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def _drain_only(db: Session, job: FleetbaseSyncJob) -> FleetbaseSyncJob:
    """Process exactly this job.

    Shared local DBs accumulate hundreds of pending/retrying FleetbaseSyncJob
    rows; a bulk claim_due(limit=N) never reaches the row under test.
    """
    job_id = job.id

    def _claim_this(_db, *, limit: int = 1, kinds=None, exclude_kinds=None):
        row = _db.get(FleetbaseSyncJob, job_id)
        assert row is not None
        row.status = "retrying"
        _db.flush()
        return [row]

    with patch.object(RetryQueue, "claim_due", side_effect=_claim_this):
        BookingSyncService().process_retry_queue(db, _settings(), limit=1)
    db.expire_all()
    return db.get(FleetbaseSyncJob, job_id)


def test_malformed_webhook_job_is_retried_not_silently_completed(db: Session) -> None:
    order = _make_order(db)
    job = RetryQueue.enqueue(
        db,
        direction="inbound",
        kind="webhook",
        order_id=order.id,
        payload={},  # no "update" — the processor cannot act on this
        idempotency_key=f"webhook:{order.id}:{uuid4().hex[:6]}",
        commit=False,
    )
    db.flush()

    refreshed = _drain_only(db, job)
    assert refreshed.status in ("retrying", "dead")
    assert refreshed.status != "done"
    assert refreshed.attempts == 1
    assert "webhook_payload_missing_update" in (refreshed.last_error or "")
    db.rollback()


def test_webhook_job_for_deleted_order_is_skipped(db: Session) -> None:
    job = RetryQueue.enqueue(
        db,
        direction="inbound",
        kind="webhook",
        order_id=str(uuid4()),  # order row does not exist
        payload={"update": {"event": "order.delivered"}},
        idempotency_key=f"webhook:missing:{uuid4().hex[:6]}",
        commit=False,
    )
    db.flush()

    refreshed = _drain_only(db, job)
    assert refreshed.status == "done"
    db.rollback()


def test_unknown_kind_surfaces_instead_of_vanishing(db: Session) -> None:
    job = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="not_a_real_kind",
        payload={},
        idempotency_key=f"bogus:{uuid4().hex[:6]}",
        commit=False,
    )
    db.flush()

    refreshed = _drain_only(db, job)
    assert refreshed.status != "done"
    assert "unhandled_retry_kind" in (refreshed.last_error or "")
    db.rollback()


def test_webhook_replay_reprocesses_the_update(db: Session) -> None:
    """A well-formed payload is handed back to the processor rather than dropped."""
    order = _make_order(db)
    seen: list[dict] = []

    class _FakeProcessor:
        def process(self, _db, _settings, update):
            seen.append(update)
            return order

    import porterchain_api.fleetbase_engine.webhook_processor as wp

    original = wp.WebhookProcessor
    wp.WebhookProcessor = _FakeProcessor  # type: ignore[misc]
    try:
        job = RetryQueue.enqueue(
            db,
            direction="inbound",
            kind="webhook",
            order_id=order.id,
            payload={"update": {"event": "order.delivered", "order_id": order.id}},
            idempotency_key=f"webhook:{order.id}:delivered",
            commit=False,
        )
        db.flush()
        refreshed = _drain_only(db, job)
    finally:
        wp.WebhookProcessor = original  # type: ignore[misc]

    assert seen and seen[0]["event"] == "order.delivered"
    assert refreshed.status == "done"
    db.rollback()

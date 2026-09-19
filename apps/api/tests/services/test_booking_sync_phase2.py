"""Phase 2: commercial invert — enqueue-only push_*, assign/cancel once via drain."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.fleetbase_models import FleetbaseSyncJob


def _settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=True,
    )
    base.update(overrides)
    return Settings(**base)


def test_push_order_enqueues_without_http(db: Session, dispatch_order) -> None:
    settings = _settings()
    svc = BookingSyncService()
    with patch.object(svc, "_bridge") as bridge:
        result = svc.push_order(db, settings, dispatch_order, commit=False)
        db.flush()
        bridge.sync_order.assert_not_called()
    assert result is None
    jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"order:{dispatch_order.id}")
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == "pending"
    db.rollback()


def test_push_driver_assignment_lww_one_job(db: Session, dispatch_order) -> None:
    settings = _settings()
    dispatch_order.fleetbase_order_id = "fb-ord-1"
    svc = BookingSyncService()
    svc.push_driver_assignment(
        db,
        settings,
        dispatch_order,
        fleetbase_driver_id="fb-drv-1",
        driver_id="drv-1",
        commit=False,
    )
    svc.push_driver_assignment(
        db,
        settings,
        dispatch_order,
        fleetbase_driver_id="fb-drv-1",
        driver_id="drv-1",
        commit=False,
    )
    db.flush()
    jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.kind == "driver", FleetbaseSyncJob.order_id == dispatch_order.id)
        .all()
    )
    assert len(jobs) == 1
    db.rollback()


def test_assign_handler_enqueues_without_waiting_for_fleetbase_ids(
    db: Session, dispatch_order, driver
) -> None:
    """After invert, assignment enqueue must not require fleetbase_* ids already set."""
    settings = _settings()
    assert dispatch_order.fleetbase_order_id is None
    assert driver.fleetbase_driver_id is None
    svc = BookingSyncService()
    with patch.object(svc, "_bridge") as bridge:
        svc.push_driver(db, settings, driver, commit=False)
        svc.push_driver_assignment(
            db,
            settings,
            dispatch_order,
            fleetbase_driver_id=None,
            driver_id=driver.id,
            commit=False,
        )
        db.flush()
        bridge.sync_dispatch.assert_not_called()
        bridge.sync_order.assert_not_called()

    order_jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"order:{dispatch_order.id}")
        .count()
    )
    driver_jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.kind == "driver", FleetbaseSyncJob.order_id == dispatch_order.id)
        .count()
    )
    profile_jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"driver_profile:{driver.id}")
        .count()
    )
    assert order_jobs == 1
    assert driver_jobs == 1
    assert profile_jobs == 1
    db.rollback()


def test_cancel_enqueues_without_http(db: Session, dispatch_order) -> None:
    settings = _settings()
    dispatch_order.fleetbase_order_id = f"fb-{uuid4().hex[:8]}"
    svc = BookingSyncService()
    with patch.object(svc, "_bridge") as bridge:
        svc.sync_cancellation(db, settings, dispatch_order)
        bridge.cancel_order.assert_not_called()
    jobs = (
        db.query(FleetbaseSyncJob)
        .filter(FleetbaseSyncJob.idempotency_key == f"cancellation:{dispatch_order.id}")
        .all()
    )
    assert len(jobs) == 1
    db.rollback()


def test_http_dispatch_driver_syncs_order_then_dispatch(db: Session, dispatch_order, settings) -> None:
    settings.fleetbase_dispatch_bridge = True
    assert dispatch_order.fleetbase_order_id is None
    job = RetryQueue.enqueue(
        db,
        direction="outbound",
        kind="driver",
        order_id=dispatch_order.id,
        idempotency_key=f"driver:{dispatch_order.id}:fb-drv-{uuid4().hex[:6]}",
        payload={
            "order_id": dispatch_order.id,
            "fleetbase_driver_id": "fb-drv",
            "driver_id": None,
        },
        commit=False,
    )
    db.flush()
    svc = BookingSyncService()
    bridge = MagicMock()
    bridge.sync_order.return_value = "fb-new"
    bridge.sync_dispatch.return_value = {"ok": True}

    def _link_order(_db, _settings, order):
        order.fleetbase_order_id = "fb-new"
        return "fb-new"

    bridge.sync_order.side_effect = _link_order
    svc._http_dispatch_kind(bridge, db, settings, job, dispatch_order)
    bridge.sync_order.assert_called_once()
    bridge.sync_dispatch.assert_called_once()
    db.rollback()



def test_http_dispatch_permanent_skips_empty_webhook(db: Session, settings) -> None:
    from porterchain_api.fleetbase_engine.booking_sync_service import PermanentSyncSkip

    job = MagicMock(kind="webhook", payload={})
    svc = BookingSyncService()
    bridge = MagicMock()
    try:
        svc._http_dispatch_kind(bridge, db, settings, job, None)
        raise AssertionError("expected PermanentSyncSkip")
    except PermanentSyncSkip as exc:
        assert "webhook_payload_missing_update" in str(exc)


def test_http_dispatch_permanent_skips_unknown_kind(db: Session, settings) -> None:
    from porterchain_api.fleetbase_engine.booking_sync_service import PermanentSyncSkip

    job = MagicMock(kind="not_a_real_kind", payload={})
    svc = BookingSyncService()
    try:
        svc._http_dispatch_kind(MagicMock(), db, settings, job, None)
        raise AssertionError("expected PermanentSyncSkip")
    except PermanentSyncSkip as exc:
        assert "unhandled_retry_kind" in str(exc)

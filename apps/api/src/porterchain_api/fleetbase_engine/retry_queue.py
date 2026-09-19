"""RetryQueue + ErrorQueue — durable retry and dead-letter for Fleetbase sync.

Failed sync attempts (outbound order/cancellation/etc. or inbound webhook
processing) are persisted as FleetbaseSyncJob rows and retried with exponential
backoff. After max attempts a job moves to the ErrorQueue (status='dead').

GPS tracking jobs: LWW only while ``pending``. A ``retrying`` (claimed) row is
never overwritten — leftover coordinates live in Redis last-known and are
re-enqueued after mark_done. In-flight uniqueness is a partial unique index on
``idempotency_key`` (see Alembic ``r0s1t2u3v4w5``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.fleetbase_models import FleetbaseSyncJob

BACKOFF_SECONDS = [30, 120, 600, 3600, 21600]  # 30s, 2m, 10m, 1h, 6h

# Outbound order link rate when dispatch bridge is enabled (§3.5.5, DD-13).
FLEETBASE_SYNC_SLO_TARGET_PCT = 98.0

# Claim lease: worker crash mid-HTTP → job becomes due again after this window.
CLAIM_LEASE_SECONDS = 60

_IN_FLIGHT = ("pending", "retrying")
TRACKING_KIND = "tracking"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _due_query(
    db: Session,
    now: datetime,
    *,
    kinds: Sequence[str] | None = None,
    exclude_kinds: Sequence[str] | None = None,
):
    q = db.query(FleetbaseSyncJob).filter(
        FleetbaseSyncJob.status.in_(_IN_FLIGHT),
        (FleetbaseSyncJob.next_attempt_at == None) | (FleetbaseSyncJob.next_attempt_at <= now),  # noqa: E711
    )
    if kinds:
        q = q.filter(FleetbaseSyncJob.kind.in_(tuple(kinds)))
    if exclude_kinds:
        q = q.filter(~FleetbaseSyncJob.kind.in_(tuple(exclude_kinds)))
    return q.order_by(FleetbaseSyncJob.next_attempt_at.asc())


def _payload_is_stale(existing_payload: dict | None, new_payload: dict) -> bool:
    from porterchain_api.driver_engine.last_known import parse_recorded_at

    new_ts = parse_recorded_at((new_payload or {}).get("recorded_at"))
    old_ts = parse_recorded_at((existing_payload or {}).get("recorded_at"))
    if new_ts is None or old_ts is None:
        return False
    return new_ts <= old_ts


def _find_inflight(db: Session, idempotency_key: str) -> FleetbaseSyncJob | None:
    return (
        db.query(FleetbaseSyncJob)
        .filter(
            FleetbaseSyncJob.idempotency_key == idempotency_key,
            FleetbaseSyncJob.status.in_(_IN_FLIGHT),
        )
        .first()
    )


def _persist(db: Session, row: FleetbaseSyncJob, *, commit: bool) -> FleetbaseSyncJob:
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row


def _merge_existing(
    db: Session,
    existing: FleetbaseSyncJob,
    *,
    payload: dict,
    order_id: str | None,
    fleetbase_order_id: str | None,
    commit: bool,
) -> FleetbaseSyncJob:
    """LWW pending rows. Never mutate a claimed (retrying) tracking job."""
    if existing.status == "retrying" and existing.kind == "tracking":
        return _persist(db, existing, commit=commit)
    if _payload_is_stale(existing.payload, payload):
        return _persist(db, existing, commit=commit)
    existing.payload = payload
    if order_id is not None:
        existing.order_id = order_id
    if fleetbase_order_id is not None:
        existing.fleetbase_order_id = fleetbase_order_id
    return _persist(db, existing, commit=commit)


class RetryQueue:
    @staticmethod
    def enqueue(
        db: Session,
        *,
        direction: str,
        kind: str,
        payload: dict,
        order_id: str | None = None,
        fleetbase_order_id: str | None = None,
        idempotency_key: str | None = None,
        max_attempts: int | None = None,
        commit: bool = True,
    ) -> FleetbaseSyncJob:
        """Enqueue or LWW-update an existing pending job (Python upsert + unique index)."""
        if max_attempts is None:
            from porterchain_api.admin_engine.platform_settings import queue_retry_max

            max_attempts = queue_retry_max(db)
        if idempotency_key:
            existing = _find_inflight(db, idempotency_key)
            if existing:
                return _merge_existing(
                    db,
                    existing,
                    payload=payload,
                    order_id=order_id,
                    fleetbase_order_id=fleetbase_order_id,
                    commit=commit,
                )
        job = FleetbaseSyncJob(
            direction=direction,
            kind=kind,
            payload=payload,
            order_id=order_id,
            fleetbase_order_id=fleetbase_order_id,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            status="pending",
            next_attempt_at=_now(),
        )
        try:
            with db.begin_nested():
                db.add(job)
                db.flush()
        except IntegrityError:
            insp = inspect(job)
            if insp.session is not None:
                db.expunge(job)
            if not idempotency_key:
                raise
            existing = _find_inflight(db, idempotency_key)
            if existing is None:
                raise
            return _merge_existing(
                db,
                existing,
                payload=payload,
                order_id=order_id,
                fleetbase_order_id=fleetbase_order_id,
                commit=commit,
            )
        return _persist(db, job, commit=commit)

    @staticmethod
    def due(
        db: Session,
        *,
        limit: int = 1,
        kinds: Sequence[str] | None = None,
        exclude_kinds: Sequence[str] | None = None,
    ) -> list[FleetbaseSyncJob]:
        """Return due jobs. Default limit=1 so one 15s Fleetbase call cannot starve email."""
        now = _now()
        return _due_query(db, now, kinds=kinds, exclude_kinds=exclude_kinds).limit(limit).all()

    @staticmethod
    def claim_due(
        db: Session,
        *,
        limit: int = 1,
        kinds: Sequence[str] | None = None,
        exclude_kinds: Sequence[str] | None = None,
    ) -> list[FleetbaseSyncJob]:
        """Claim due jobs with a lease so worker and /sync/process cannot double-HTTP.

        Uses FOR UPDATE SKIP LOCKED, then sets status=retrying and
        next_attempt_at = now + CLAIM_LEASE_SECONDS. Crash mid-HTTP → job
        becomes due again after the lease. Does not hold the row lock across HTTP.

        ``kinds`` / ``exclude_kinds`` split GPS tracking from commercial drain.
        """
        now = _now()
        jobs = (
            _due_query(db, now, kinds=kinds, exclude_kinds=exclude_kinds)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .all()
        )
        lease_until = now + timedelta(seconds=CLAIM_LEASE_SECONDS)
        for job in jobs:
            job.status = "retrying"
            job.next_attempt_at = lease_until
        if jobs:
            db.commit()
            for job in jobs:
                db.refresh(job)
        return jobs

    @staticmethod
    def mark_done(db: Session, job: FleetbaseSyncJob, *, commit: bool = True) -> None:
        job.attempts += 1
        job.status = "done"
        job.last_error = None
        if commit:
            db.commit()

    @staticmethod
    def mark_failed(db: Session, job: FleetbaseSyncJob, error: str, *, commit: bool = True) -> None:
        job.attempts += 1
        job.last_error = error[:2000]
        if job.attempts >= job.max_attempts:
            job.status = "dead"
            job.next_attempt_at = None
        else:
            job.status = "retrying"
            from porterchain_api.admin_engine.platform_settings import dispatch_retry_seconds

            base = dispatch_retry_seconds(db)
            # Settings floor first delay; then grow with the historic backoff curve.
            curve = [base, *BACKOFF_SECONDS[1:]]
            delay = curve[min(job.attempts - 1, len(curve) - 1)]
            job.next_attempt_at = _now() + timedelta(seconds=delay)
        if commit:
            db.commit()


class ErrorQueue:
    """Dead-letter view + manual recovery for jobs that exhausted retries."""

    @staticmethod
    def list_dead(db: Session, *, limit: int = 100) -> list[FleetbaseSyncJob]:
        return (
            db.query(FleetbaseSyncJob)
            .filter(FleetbaseSyncJob.status == "dead")
            .order_by(FleetbaseSyncJob.updated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def requeue(db: Session, job_id: str) -> FleetbaseSyncJob | None:
        job = db.get(FleetbaseSyncJob, job_id)
        if not job:
            return None
        if job.status in _IN_FLIGHT:
            return job
        if job.idempotency_key:
            existing = _find_inflight(db, job.idempotency_key)
            if existing is not None and existing.id != job.id:
                job.status = "done"
                job.last_error = (job.last_error or "")[:1800] + " [superseded_by_inflight]"
                db.commit()
                db.refresh(existing)
                return existing
        job.status = "pending"
        job.attempts = 0
        job.last_error = None
        job.next_attempt_at = _now()
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def stats(db: Session) -> dict:
        from sqlalchemy import func

        rows = (
            db.query(FleetbaseSyncJob.status, func.count(FleetbaseSyncJob.id))
            .group_by(FleetbaseSyncJob.status)
            .all()
        )
        return {s: n for s, n in rows}

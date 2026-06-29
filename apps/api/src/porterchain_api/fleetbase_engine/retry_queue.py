"""RetryQueue + ErrorQueue — durable retry and dead-letter for Fleetbase sync.

Failed sync attempts (outbound order/cancellation/etc. or inbound webhook
processing) are persisted as FleetbaseSyncJob rows and retried with exponential
backoff. After max attempts a job moves to the ErrorQueue (status='dead').
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.fleetbase_models import FleetbaseSyncJob

BACKOFF_SECONDS = [30, 120, 600, 3600, 21600]  # 30s, 2m, 10m, 1h, 6h


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
        max_attempts: int = 5,
        commit: bool = True,
    ) -> FleetbaseSyncJob:
        if idempotency_key:
            existing = (
                db.query(FleetbaseSyncJob)
                .filter(
                    FleetbaseSyncJob.idempotency_key == idempotency_key,
                    FleetbaseSyncJob.status.in_(["pending", "retrying"]),
                )
                .first()
            )
            if existing:
                return existing
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
        db.add(job)
        if commit:
            db.commit()
            db.refresh(job)
        return job

    @staticmethod
    def due(db: Session, *, limit: int = 50) -> list[FleetbaseSyncJob]:
        now = _now()
        return (
            db.query(FleetbaseSyncJob)
            .filter(
                FleetbaseSyncJob.status.in_(["pending", "retrying"]),
                (FleetbaseSyncJob.next_attempt_at == None) | (FleetbaseSyncJob.next_attempt_at <= now),  # noqa: E711
            )
            .order_by(FleetbaseSyncJob.next_attempt_at.asc())
            .limit(limit)
            .all()
        )

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
            delay = BACKOFF_SECONDS[min(job.attempts - 1, len(BACKOFF_SECONDS) - 1)]
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

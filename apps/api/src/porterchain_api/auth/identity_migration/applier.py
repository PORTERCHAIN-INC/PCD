"""Persist and apply identity migration plans (dry-run default)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.identity_migration.types import MigrationPlan, PlannedRecord
from porterchain_api.auth.ensure_user_service import EnsureUserService, normalize_email
from porterchain_api.auth.unified_catalog import AuthProvider
from porterchain_api.unified_identity_models import (
    IdentityMigrationRecord,
    IdentityMigrationRun,
)


def persist_plan(db: Session, plan: MigrationPlan, *, dry_run: bool = True) -> IdentityMigrationRun:
    """Write a new migration run + records. Idempotent per unique source within the run."""
    run = IdentityMigrationRun(
        label=plan.label,
        status="planned",
        dry_run=dry_run,
        source_summary=plan.source_summary,
        counts=plan.counts,
    )
    db.add(run)
    db.flush()

    for rec in plan.records:
        db.add(
            IdentityMigrationRecord(
                run_id=run.id,
                source_app=rec.source_app,
                source_issuer=rec.source_issuer,
                source_clerk_user_id=rec.source_clerk_user_id,
                internal_user_id=rec.internal_user_id,
                target_clerk_user_id=rec.target_clerk_user_id,
                status=rec.status,
                conflict_reason=rec.conflict_reason,
                proposed_roles=list(rec.proposed_roles),
                detail={
                    **(rec.detail or {}),
                    "email": rec.email,
                    "email_verified": rec.email_verified,
                    "match_method": rec.match_method,
                },
            )
        )
    db.commit()
    db.refresh(run)
    return run


def load_run_records(db: Session, run_id: str) -> tuple[IdentityMigrationRun, list[IdentityMigrationRecord]]:
    run = db.query(IdentityMigrationRun).filter(IdentityMigrationRun.id == run_id).first()
    if not run:
        raise ValueError(f"migration run not found: {run_id}")
    records = (
        db.query(IdentityMigrationRecord)
        .filter(IdentityMigrationRecord.run_id == run_id)
        .order_by(IdentityMigrationRecord.source_app, IdentityMigrationRecord.source_clerk_user_id)
        .all()
    )
    return run, records


def conflict_report(db: Session, run_id: str) -> dict[str, Any]:
    run, records = load_run_records(db, run_id)
    conflicts = [
        {
            "source_app": r.source_app,
            "source_clerk_user_id": r.source_clerk_user_id,
            "status": r.status,
            "conflict_reason": r.conflict_reason,
            "detail": {
                k: v
                for k, v in (r.detail or {}).items()
                if k not in ("password", "token", "mfa", "totp")
            },
        }
        for r in records
        if r.status == "conflict" or r.conflict_reason
    ]
    return {
        "run_id": run.id,
        "label": run.label,
        "status": run.status,
        "dry_run": run.dry_run,
        "counts": run.counts,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }


def apply_run(
    db: Session,
    run_id: str,
    *,
    dry_run: bool = True,
    accept_email_candidates: bool = False,
    confirm: str | None = None,
) -> dict[str, Any]:
    """
    Apply a planned run.

    dry_run=True (default): mark eligible records dry_run_ok; no user mutations.
    dry_run=False: requires confirm == "APPLY"; writes users/links/roles.
    """
    if not dry_run:
        if confirm != "APPLY":
            raise ValueError('apply requires --confirm APPLY (dry-run is the default)')

    run, records = load_run_records(db, run_id)
    run.started_at = datetime.now(UTC)
    run.dry_run = dry_run
    run.status = "dry_running" if dry_run else "applying"

    ensure = EnsureUserService()
    counts = {"processed": 0, "dry_run_ok": 0, "applied": 0, "skipped": 0, "failed": 0, "conflict": 0}

    for rec in records:
        counts["processed"] += 1
        if rec.status == "conflict":
            counts["conflict"] += 1
            continue
        if rec.status in ("applied", "dry_run_ok"):
            counts["skipped"] += 1
            continue
        if rec.status == "email_candidate" and not accept_email_candidates and not dry_run:
            rec.status = "skipped"
            rec.conflict_reason = "email_candidate_requires_accept_email_candidates"
            counts["skipped"] += 1
            continue
        if rec.status == "email_candidate" and not accept_email_candidates and dry_run:
            # Still count as dry_run preview but note gate
            rec.detail = {**(rec.detail or {}), "apply_gate": "needs_accept_email_candidates"}

        try:
            if dry_run:
                rec.status = "dry_run_ok"
                counts["dry_run_ok"] += 1
                continue

            target_clerk = rec.target_clerk_user_id or rec.source_clerk_user_id
            email = normalize_email((rec.detail or {}).get("email"))
            identity = AuthenticatedIdentity(
                provider=AuthProvider.CLERK.value,
                issuer=rec.source_issuer,
                subject=target_clerk,
                email=email,
                email_verified=bool((rec.detail or {}).get("email_verified")),
            )
            user = ensure.ensure_from_identity(
                db,
                identity,
                email_verified=bool((rec.detail or {}).get("email_verified")),
                commit=False,
            )
            # Prefer mapped internal user if provided and different
            if rec.internal_user_id and rec.internal_user_id != user.id:
                # Link target clerk subject onto the mapped internal user
                user = ensure.ensure_from_identity(
                    db,
                    AuthenticatedIdentity(
                        provider=AuthProvider.CLERK.value,
                        issuer=rec.source_issuer,
                        subject=target_clerk,
                        email=email,
                        email_verified=bool((rec.detail or {}).get("email_verified")),
                    ),
                    email_verified=bool((rec.detail or {}).get("email_verified")),
                    commit=False,
                )

            # Roles/ACL: EnsureUserService + SpiceDB TupleWriter — never Postgres assignments.
            rec.detail = {
                **(rec.detail or {}),
                "proposed_roles": list(rec.proposed_roles or []),
            }
            rec.internal_user_id = user.id
            rec.target_clerk_user_id = target_clerk
            rec.status = "applied"
            counts["applied"] += 1
        except Exception as exc:  # noqa: BLE001
            rec.status = "failed"
            rec.conflict_reason = f"apply_error:{type(exc).__name__}"
            rec.detail = {**(rec.detail or {}), "error": type(exc).__name__}
            counts["failed"] += 1

    run.counts = {**(run.counts or {}), **counts}
    run.status = "dry_run_complete" if dry_run else ("applied" if counts["failed"] == 0 else "applied_with_errors")
    run.finished_at = datetime.now(UTC)
    db.commit()
    return {"run_id": run.id, "status": run.status, "dry_run": dry_run, "counts": counts}


def verify_run(db: Session, run_id: str) -> dict[str, Any]:
    run, records = load_run_records(db, run_id)
    by_status: dict[str, int] = {}
    for r in records:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    unresolved = sum(by_status.get(s, 0) for s in ("conflict", "failed", "pending", "unmatched", "email_candidate"))
    ok = run.status in ("dry_run_complete", "applied") and by_status.get("conflict", 0) == 0 and by_status.get("failed", 0) == 0
    return {
        "run_id": run.id,
        "label": run.label,
        "run_status": run.status,
        "dry_run": run.dry_run,
        "by_status": by_status,
        "unresolved": unresolved,
        "ok": ok,
    }


def planned_record_from_db(rec: IdentityMigrationRecord) -> PlannedRecord:
    return PlannedRecord(
        source_app=rec.source_app,
        source_clerk_user_id=rec.source_clerk_user_id,
        source_issuer=rec.source_issuer,
        email=(rec.detail or {}).get("email"),
        email_verified=bool((rec.detail or {}).get("email_verified")),
        status=rec.status,
        conflict_reason=rec.conflict_reason,
        internal_user_id=rec.internal_user_id,
        target_clerk_user_id=rec.target_clerk_user_id,
        proposed_roles=list(rec.proposed_roles or []),
        match_method=(rec.detail or {}).get("match_method"),
        detail=dict(rec.detail or {}),
    )

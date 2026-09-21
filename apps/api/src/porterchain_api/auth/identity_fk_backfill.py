"""Phase 8 — resolve clerk subject → porterchain_users.id; backfill profile FKs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.driver_lookups import (
    list_drivers,
    stamp_porterchain_user_id as stamp_driver_porterchain_user_id,
)
from porterchain_api.admin_engine.staff_lookups import (
    list_admin_users,
    stamp_porterchain_user_id as stamp_admin_porterchain_user_id,
)
from porterchain_api.auth.dev import is_dev_bypass_subject
from porterchain_api.auth.ensure_user_service import normalize_email
from porterchain_api.auth.unified_catalog import AccountStatus, OnboardingStatus
from porterchain_api.identity_models import IdentityLink
from porterchain_api.invitation_models import UserInvitation
from porterchain_api.merchant_engine.lookups import (
    list_merchant_users,
    stamp_porterchain_user_id as stamp_merchant_porterchain_user_id,
)
from porterchain_api.booking_models import Customer
from porterchain_api.user_models import PorterchainUser

ProfileKind = Literal["admin_users", "merchant_users", "customers", "drivers", "user_invitations"]

PROFILE_TARGETS: tuple[ProfileKind, ...] = (
    "admin_users",
    "merchant_users",
    "customers",
    "drivers",
    "user_invitations",
)


def _is_skippable_clerk_id(clerk_user_id: str | None) -> bool:
    if not clerk_user_id or not str(clerk_user_id).strip():
        return True
    cid = str(clerk_user_id).strip()
    return cid.startswith("pending:") or is_dev_bypass_subject(cid)


@dataclass
class BackfillAction:
    table: str
    row_id: str
    clerk_user_id: str | None
    current_porterchain_user_id: str | None
    resolved_porterchain_user_id: str | None
    status: str  # already_set | would_set | set | unmatched | skipped | healed_link
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BackfillReport:
    dry_run: bool
    create_missing: bool
    actions: list[BackfillAction] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    identity_links_healed: int = 0

    def recompute(self) -> None:
        counts: dict[str, int] = {"total": len(self.actions)}
        for a in self.actions:
            counts[a.status] = counts.get(a.status, 0) + 1
        counts["identity_links_healed"] = self.identity_links_healed
        self.counts = counts

    def to_dict(self) -> dict[str, Any]:
        self.recompute()
        return {
            "dry_run": self.dry_run,
            "create_missing": self.create_missing,
            "counts": self.counts,
            "unmatched_sample": [
                a.to_dict() for a in self.actions if a.status == "unmatched"
            ][:25],
            "note": "clerk_user_id columns are retained; no drops in Phase 8",
        }


def resolve_porterchain_user_id(
    db: Session,
    clerk_user_id: str | None,
    *,
    create_missing: bool = False,
    email: str | None = None,
) -> tuple[str | None, str]:
    """
    Return (porterchain_users.id, method).

    Methods: porterchain_users | identity_link | created | none
    """
    if _is_skippable_clerk_id(clerk_user_id):
        return None, "skipped"
    assert clerk_user_id is not None
    cid = clerk_user_id.strip()

    user = db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == cid).first()
    if user:
        return user.id, "porterchain_users"

    link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == cid).first()
    if not link:
        link = (
            db.query(IdentityLink)
            .filter(IdentityLink.subject == cid, IdentityLink.deactivated_at.is_(None))
            .first()
        )
    if link:
        pc = db.query(PorterchainUser).filter(PorterchainUser.id == link.platform_user_id).first()
        if pc:
            return pc.id, "identity_link"
        # Mis-pointed platform_user_id (legacy profile UUID) — fall through

    if create_missing:
        created = PorterchainUser(
            clerk_user_id=cid,
            email=normalize_email(email),
            role="unprovisioned",
            status=AccountStatus.PENDING.value,
            onboarding_status=OnboardingStatus.NOT_STARTED.value,
            profile={"source": "phase8_fk_backfill", "provisioned": False},
        )
        db.add(created)
        db.flush()
        return created.id, "created"

    return None, "none"


def _iter_profile_rows(db: Session, table: ProfileKind):
    if table == "admin_users":
        return list_admin_users(db)
    if table == "merchant_users":
        return list_merchant_users(db)
    if table == "customers":
        return db.query(Customer).all()
    if table == "drivers":
        return list_drivers(db)
    if table == "user_invitations":
        return db.query(UserInvitation).all()
    return []


def _stamp_porterchain_user_id(table: ProfileKind, row: Any, user_id: str) -> None:
    if table == "admin_users":
        stamp_admin_porterchain_user_id(row, user_id)
        return
    if table == "merchant_users":
        stamp_merchant_porterchain_user_id(row, user_id)
        return
    if table == "drivers":
        stamp_driver_porterchain_user_id(row, user_id)
        return
    row.porterchain_user_id = user_id


def _row_email(row: Any) -> str | None:
    return getattr(row, "email", None)


def backfill_profile_fks(
    db: Session,
    *,
    dry_run: bool = True,
    create_missing: bool = False,
    tables: tuple[ProfileKind, ...] | None = None,
    heal_identity_links: bool = True,
) -> BackfillReport:
    """
    Idempotent backfill of porterchain_user_id on profile tables.

    dry_run=True: no commits (caller should rollback); report would_set.
    dry_run=False: write + commit.
    """
    report = BackfillReport(dry_run=dry_run, create_missing=create_missing)
    targets = tables or PROFILE_TARGETS

    if heal_identity_links:
        report.identity_links_healed = _heal_identity_links(db, dry_run=dry_run, create_missing=create_missing)

    for table in targets:
        for row in _iter_profile_rows(db, table):
            clerk_id = getattr(row, "clerk_user_id", None)
            current = getattr(row, "porterchain_user_id", None)
            if current:
                report.actions.append(
                    BackfillAction(
                        table=table,
                        row_id=row.id,
                        clerk_user_id=clerk_id,
                        current_porterchain_user_id=current,
                        resolved_porterchain_user_id=current,
                        status="already_set",
                    )
                )
                continue
            if _is_skippable_clerk_id(clerk_id):
                report.actions.append(
                    BackfillAction(
                        table=table,
                        row_id=row.id,
                        clerk_user_id=clerk_id,
                        current_porterchain_user_id=None,
                        resolved_porterchain_user_id=None,
                        status="skipped",
                        detail={"reason": "empty_or_pending_clerk_id"},
                    )
                )
                continue

            resolved, method = resolve_porterchain_user_id(
                db,
                clerk_id,
                create_missing=False,
                email=_row_email(row),
            )
            if not resolved:
                if create_missing:
                    if dry_run:
                        report.actions.append(
                            BackfillAction(
                                table=table,
                                row_id=row.id,
                                clerk_user_id=clerk_id,
                                current_porterchain_user_id=None,
                                resolved_porterchain_user_id=None,
                                status="would_create",
                                detail={"method": "created"},
                            )
                        )
                        continue
                    resolved, method = resolve_porterchain_user_id(
                        db,
                        clerk_id,
                        create_missing=True,
                        email=_row_email(row),
                    )
                if not resolved:
                    report.actions.append(
                        BackfillAction(
                            table=table,
                            row_id=row.id,
                            clerk_user_id=clerk_id,
                            current_porterchain_user_id=None,
                            resolved_porterchain_user_id=None,
                            status="unmatched",
                            detail={"method": method},
                        )
                    )
                    continue

            if dry_run:
                report.actions.append(
                    BackfillAction(
                        table=table,
                        row_id=row.id,
                        clerk_user_id=clerk_id,
                        current_porterchain_user_id=None,
                        resolved_porterchain_user_id=resolved,
                        status="would_set",
                        detail={"method": method},
                    )
                )
            else:
                _stamp_porterchain_user_id(table, row, resolved)
                report.actions.append(
                    BackfillAction(
                        table=table,
                        row_id=row.id,
                        clerk_user_id=clerk_id,
                        current_porterchain_user_id=None,
                        resolved_porterchain_user_id=resolved,
                        status="set",
                        detail={"method": method},
                    )
                )

    report.recompute()
    if not dry_run:
        db.commit()
    else:
        db.rollback()
    return report


def _heal_identity_links(db: Session, *, dry_run: bool, create_missing: bool) -> int:
    """Point identity_links.platform_user_id at porterchain_users.id when mis-pointed."""
    healed = 0
    links = db.query(IdentityLink).filter(IdentityLink.deactivated_at.is_(None)).all()
    for link in links:
        pc = db.query(PorterchainUser).filter(PorterchainUser.id == link.platform_user_id).first()
        if pc:
            continue
        resolved, _method = resolve_porterchain_user_id(
            db,
            link.clerk_user_id or link.subject,
            create_missing=create_missing and not dry_run,
            email=link.email,
        )
        if not resolved:
            continue
        healed += 1
        if not dry_run:
            link.platform_user_id = resolved
            if not link.subject and link.clerk_user_id:
                link.subject = link.clerk_user_id
    return healed


def audit_fk_coverage(db: Session) -> dict[str, Any]:
    """Counts only — no PII."""
    out: dict[str, Any] = {}
    for table in PROFILE_TARGETS:
        rows = _iter_profile_rows(db, table)
        total = len(rows)
        with_fk = sum(1 for r in rows if getattr(r, "porterchain_user_id", None))
        with_clerk = sum(
            1 for r in rows if getattr(r, "clerk_user_id", None) and not _is_skippable_clerk_id(r.clerk_user_id)
        )
        out[table] = {
            "total": total,
            "with_clerk_user_id": with_clerk,
            "with_porterchain_user_id": with_fk,
            "missing_porterchain_user_id": max(0, with_clerk - with_fk),
        }

    links = db.query(IdentityLink).filter(IdentityLink.deactivated_at.is_(None)).all()
    mispointed = 0
    for link in links:
        if not db.query(PorterchainUser.id).filter(PorterchainUser.id == link.platform_user_id).first():
            mispointed += 1
    out["identity_links"] = {
        "active": len(links),
        "platform_user_id_not_in_porterchain_users": mispointed,
    }
    out["note"] = "Phase 8 keeps clerk_user_id; orders/quotes already FK to customers.id not Clerk"
    return out

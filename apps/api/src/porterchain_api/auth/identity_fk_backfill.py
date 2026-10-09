"""Phase 8 — resolve clerk subject → porterchain_users.id; backfill profile FKs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from sqlalchemy.orm import Session

from porterchain_api.auth.dev import is_dev_bypass_subject
from porterchain_api.auth.ensure_user_service import normalize_email
from porterchain_api.auth.unified_catalog import AccountStatus, OnboardingStatus
from porterchain_api.identity_models import IdentityLink
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

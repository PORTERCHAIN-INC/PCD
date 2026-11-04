"""Admin Organisations use-cases (doc 70) — DB access for ``routers/admin_orgs.py``."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from porterchain_api.org_engine import packs, service
from porterchain_api.org_engine.models import Organisation


def find_org(db: Session, org_id: str) -> Organisation | None:
    return db.get(Organisation, org_id) or db.scalar(select(Organisation).where(Organisation.public_id == org_id))


def list_orgs(
    db: Session,
    *,
    business_type: str | None,
    needs_review: bool | None,
    status: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    conds = []
    if business_type:
        conds.append(Organisation.business_type == business_type)
    if needs_review is not None:
        conds.append(Organisation.needs_review.is_(needs_review))
    if status:
        conds.append(Organisation.status == status)
    if q and q.strip():
        like = f"%{q.strip()}%"
        conds.append(
            or_(
                Organisation.display_name.ilike(like),
                Organisation.public_id.ilike(like),
                Organisation.legal_name.ilike(like),
            )
        )
    total = db.scalar(select(func.count()).select_from(Organisation).where(*conds)) or 0
    page = (
        select(Organisation)
        .where(*conds)
        .order_by(Organisation.display_name)
        .offset(max(0, offset))
        .limit(max(1, min(limit, 500)))
    )
    by_type = dict(
        db.execute(select(Organisation.business_type, func.count()).group_by(Organisation.business_type)).all()
    )
    review = db.scalar(select(func.count()).select_from(Organisation).where(Organisation.needs_review.is_(True))) or 0
    return {
        "items": [service.org_out(db, o) for o in db.scalars(page)],
        "total": total,
        "counts": {"by_type": by_type, "needs_review": review, "all": sum(by_type.values())},
    }


def create_org(
    db: Session, *, display_name: str, business_type: str, subtype: str | None, legal_name: str | None
) -> dict[str, Any]:
    """Raises ValueError for an invalid type/subtype."""
    org = service.provision(
        db, display_name=display_name, business_type=business_type, subtype=subtype, legal_name=legal_name
    )
    db.commit()
    return service.org_out(db, org)


def set_type(
    db: Session,
    org: Organisation,
    *,
    business_type: str,
    subtype: str | None,
    reset_capabilities: bool,
    actor: Any,
) -> dict[str, Any]:
    """Raises ValueError for an invalid type/subtype."""
    caps = packs.default_capabilities(business_type, subtype)
    org.business_type, org.subtype, org.needs_review = business_type, subtype, False
    org.role_flags = list(packs.business_type(business_type)["roles"])
    if reset_capabilities:
        current = service.capabilities(db, org.id)
        service.set_capabilities(
            db, org.id, {c: False for c in current if c not in caps} | {c: True for c in caps}, source="default"
        )
        service.set_profile(db, org.id, packs.default_profile(business_type), actor=actor)
    db.commit()
    return service.org_out(db, org)


def set_capabilities(db: Session, org: Organisation, capabilities: dict[str, bool]) -> dict[str, Any]:
    """Raises ValueError for unknown capabilities."""
    service.set_capabilities(db, org.id, capabilities)
    db.commit()
    return service.org_out(db, org)


def set_profile(db: Session, org: Organisation, profile: dict[str, Any], actor: Any) -> dict[str, Any]:
    """Raises ValueError for an invalid profile."""
    service.set_profile(db, org.id, profile, actor=actor)
    db.commit()
    return service.org_out(db, org)


def backfill_from_merchants(db: Session, *, dry_run: bool) -> dict[str, Any]:
    out = service.backfill_from_merchants(db, dry_run=dry_run)
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return out

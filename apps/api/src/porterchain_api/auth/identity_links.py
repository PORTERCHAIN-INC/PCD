"""IdentityLink writes owned by auth — SSO and ensure-user call this."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.identity_models import IdentityLink
from porterchain_api.user_models import PorterchainUser


def find_link(db: Session, subject: str) -> IdentityLink | None:
    """Locate link by clerk_user_id — committed rows first, then session-staged."""
    link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == subject).first()
    if link is not None:
        return link
    for pending in db.new:
        if isinstance(pending, IdentityLink) and pending.clerk_user_id == subject:
            return pending
    return None


def require_porterchain_user_id(db: Session, subject: str, porterchain_user_id: str | None) -> str:
    if porterchain_user_id:
        return porterchain_user_id
    pc = db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == subject).first()
    if not pc:
        raise ValueError("porterchain_user_missing_for_sso")
    return pc.id


def upsert_sso_link(
    db: Session,
    *,
    subject: str,
    email: str | None,
    user_type: str,
    platform_user_id: str,
    platform_org_id: str | None,
    provider: str,
    issuer: str | None,
    fleetbase_permissions: list[str] | None = None,
    fleetbase_roles: list[str] | None = None,
) -> IdentityLink:
    def _sync(link: IdentityLink) -> IdentityLink:
        link.email = email or link.email
        link.user_type = user_type
        link.platform_user_id = platform_user_id
        link.platform_org_id = platform_org_id
        link.fleetbase_permissions = fleetbase_permissions
        link.fleetbase_roles = fleetbase_roles
        link.last_synced_at = datetime.now(UTC)
        if issuer:
            link.issuer = issuer
        link.subject = subject
        link.provider = provider or link.provider
        return link

    link = find_link(db, subject)
    if link is None:
        link = IdentityLink(
            clerk_user_id=subject,
            email=email,
            user_type=user_type,
            platform_user_id=platform_user_id,
            platform_org_id=platform_org_id,
            fleetbase_permissions=fleetbase_permissions,
            fleetbase_roles=fleetbase_roles,
            provider=provider,
            issuer=issuer,
            subject=subject,
            is_current=True,
            is_legacy=False,
            linked_at=datetime.now(UTC),
        )
        db.add(link)
    else:
        _sync(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == subject).first()
        if link is None:
            raise
        _sync(link)
        db.commit()
    db.refresh(link)
    return link


def stamp_fleetbase_user_uuid(link: IdentityLink, fleetbase_user_uuid: str) -> None:
    link.fleetbase_user_uuid = fleetbase_user_uuid
    link.last_synced_at = datetime.now(UTC)

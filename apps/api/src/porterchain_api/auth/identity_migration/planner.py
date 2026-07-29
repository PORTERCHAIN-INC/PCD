"""Plan identity migration records — matching rules, no auto-elevate."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.identity_migration.types import (
    AdminAllowlist,
    ExplicitMapLink,
    MigrationPlan,
    PlannedRecord,
    SourceExportUser,
)
from porterchain_api.auth.unified_catalog import AssignableRole, is_invite_only
from porterchain_api.identity_models import IdentityLink
from porterchain_api.user_models import PorterchainUser
from porterchain_api.unified_identity_models import UserEmail


def _default_persona_roles(source_app: str) -> list[str]:
    if source_app == "customer":
        return [AssignableRole.CUSTOMER.value]
    if source_app == "driver":
        return [AssignableRole.DRIVER.value]
    # merchant/admin never from source_app alone
    return []


def _filter_roles(
    roles: list[str],
    *,
    clerk_user_id: str,
    allowlist: AdminAllowlist,
) -> tuple[list[str], list[str]]:
    """Return (accepted, rejected_invite_only)."""
    accepted: list[str] = []
    rejected: list[str] = []
    for role in roles:
        key = role.strip()
        if not key:
            continue
        if is_invite_only(key) and not allowlist.allows_admin_id(clerk_user_id):
            rejected.append(key)
            continue
        # Allowlist may further constrain admin roles
        if is_invite_only(key):
            allowed_roles = allowlist.roles_for(clerk_user_id)
            if allowed_roles and key not in allowed_roles:
                rejected.append(key)
                continue
        accepted.append(key)
    return accepted, rejected


def build_migration_plan(
    *,
    label: str,
    sources: list[SourceExportUser],
    explicit_map: list[ExplicitMapLink],
    allowlist: AdminAllowlist,
    db: Session | None = None,
) -> MigrationPlan:
    """
    Matching priority:
      1. Explicit reviewed migration map
      2. Existing identity_links / porterchain_users.clerk_user_id
      3. Verified email candidate (unique) — never auto-merge multi-app same email
    Admin/invite-only roles only via allowlist.
    Metadata role hints are ignored for elevation (recorded in detail only).
    """
    map_index: dict[tuple[str, str], ExplicitMapLink] = {
        (m.source_app, m.source_clerk_user_id): m for m in explicit_map if m.source_app and m.source_clerk_user_id
    }

    # Same verified email across multiple source apps → conflict unless mapped
    email_apps: dict[str, set[str]] = defaultdict(set)
    for s in sources:
        if s.email and s.email_verified:
            email_apps[s.email].add(s.source_app)

    records: list[PlannedRecord] = []
    for src in sources:
        detail: dict[str, Any] = {}
        if src.metadata_role_hint:
            detail["metadata_role_hint_ignored"] = src.metadata_role_hint

        map_hit = map_index.get((src.source_app, src.source_clerk_user_id))
        if map_hit:
            roles = list(map_hit.roles) or _default_persona_roles(src.source_app)
            # Merge allowlist roles for admin ids
            if allowlist.allows_admin_id(src.source_clerk_user_id):
                for r in allowlist.roles_for(src.source_clerk_user_id):
                    if r not in roles:
                        roles.append(r)
            accepted, rejected = _filter_roles(
                roles, clerk_user_id=src.source_clerk_user_id, allowlist=allowlist
            )
            if rejected:
                detail["rejected_invite_roles"] = rejected
            if not accepted and rejected:
                records.append(
                    PlannedRecord(
                        source_app=src.source_app,
                        source_clerk_user_id=src.source_clerk_user_id,
                        source_issuer=src.source_issuer,
                        email=src.email,
                        email_verified=src.email_verified,
                        status="conflict",
                        conflict_reason="invite_only_roles_not_allowlisted",
                        proposed_roles=[],
                        match_method="map",
                        detail=detail,
                    )
                )
                continue
            records.append(
                PlannedRecord(
                    source_app=src.source_app,
                    source_clerk_user_id=src.source_clerk_user_id,
                    source_issuer=src.source_issuer,
                    email=src.email,
                    email_verified=src.email_verified,
                    status="matched_map",
                    internal_user_id=map_hit.internal_user_id,
                    target_clerk_user_id=map_hit.target_clerk_user_id or src.source_clerk_user_id,
                    proposed_roles=accepted,
                    match_method="map",
                    detail=detail,
                )
            )
            continue

        # Multi-app same email without map → conflict
        if src.email and src.email_verified and len(email_apps.get(src.email, set())) > 1:
            records.append(
                PlannedRecord(
                    source_app=src.source_app,
                    source_clerk_user_id=src.source_clerk_user_id,
                    source_issuer=src.source_issuer,
                    email=src.email,
                    email_verified=src.email_verified,
                    status="conflict",
                    conflict_reason="same_email_across_legacy_apps_requires_explicit_map",
                    proposed_roles=[],
                    match_method=None,
                    detail={**detail, "apps_sharing_email": sorted(email_apps[src.email])},
                )
            )
            continue

        # Existing identity
        internal_id = None
        target_id = src.source_clerk_user_id
        if db is not None:
            link = (
                db.query(IdentityLink)
                .filter(IdentityLink.clerk_user_id == src.source_clerk_user_id)
                .first()
            )
            if link:
                internal_id = link.platform_user_id
            if not internal_id:
                user = (
                    db.query(PorterchainUser)
                    .filter(PorterchainUser.clerk_user_id == src.source_clerk_user_id)
                    .first()
                )
                if user:
                    internal_id = user.id

        if internal_id:
            roles = _default_persona_roles(src.source_app)
            if allowlist.allows_admin_id(src.source_clerk_user_id):
                roles = list(dict.fromkeys(roles + allowlist.roles_for(src.source_clerk_user_id)))
            accepted, rejected = _filter_roles(
                roles, clerk_user_id=src.source_clerk_user_id, allowlist=allowlist
            )
            if rejected:
                detail["rejected_invite_roles"] = rejected
            if src.source_app == "admin" and not accepted:
                records.append(
                    PlannedRecord(
                        source_app=src.source_app,
                        source_clerk_user_id=src.source_clerk_user_id,
                        source_issuer=src.source_issuer,
                        email=src.email,
                        email_verified=src.email_verified,
                        status="conflict",
                        conflict_reason="admin_source_requires_allowlist",
                        internal_user_id=internal_id,
                        target_clerk_user_id=target_id,
                        proposed_roles=[],
                        match_method="identity",
                        detail=detail,
                    )
                )
                continue
            records.append(
                PlannedRecord(
                    source_app=src.source_app,
                    source_clerk_user_id=src.source_clerk_user_id,
                    source_issuer=src.source_issuer,
                    email=src.email,
                    email_verified=src.email_verified,
                    status="matched_identity",
                    internal_user_id=internal_id,
                    target_clerk_user_id=target_id,
                    proposed_roles=accepted,
                    match_method="identity",
                    detail=detail,
                )
            )
            continue

        # Verified email candidate
        if db is not None and src.email and src.email_verified:
            email_hits = (
                db.query(UserEmail)
                .filter(UserEmail.normalized_email == src.email, UserEmail.is_verified.is_(True))
                .all()
            )
            user_ids = {e.user_id for e in email_hits}
            if not user_ids:
                pc = (
                    db.query(PorterchainUser)
                    .filter(PorterchainUser.email == src.email)
                    .all()
                )
                user_ids = {u.id for u in pc}
            if len(user_ids) > 1:
                records.append(
                    PlannedRecord(
                        source_app=src.source_app,
                        source_clerk_user_id=src.source_clerk_user_id,
                        source_issuer=src.source_issuer,
                        email=src.email,
                        email_verified=src.email_verified,
                        status="conflict",
                        conflict_reason="verified_email_matches_multiple_internal_users",
                        proposed_roles=[],
                        match_method="email",
                        detail=detail,
                    )
                )
                continue
            if len(user_ids) == 1:
                roles = _default_persona_roles(src.source_app)
                if allowlist.allows_admin_id(src.source_clerk_user_id):
                    roles = list(dict.fromkeys(roles + allowlist.roles_for(src.source_clerk_user_id)))
                accepted, rejected = _filter_roles(
                    roles, clerk_user_id=src.source_clerk_user_id, allowlist=allowlist
                )
                if rejected:
                    detail["rejected_invite_roles"] = rejected
                if src.source_app in ("admin", "merchant") and not accepted:
                    records.append(
                        PlannedRecord(
                            source_app=src.source_app,
                            source_clerk_user_id=src.source_clerk_user_id,
                            source_issuer=src.source_issuer,
                            email=src.email,
                            email_verified=src.email_verified,
                            status="conflict",
                            conflict_reason=f"{src.source_app}_requires_explicit_map_or_allowlist",
                            internal_user_id=next(iter(user_ids)),
                            proposed_roles=[],
                            match_method="email",
                            detail=detail,
                        )
                    )
                    continue
                records.append(
                    PlannedRecord(
                        source_app=src.source_app,
                        source_clerk_user_id=src.source_clerk_user_id,
                        source_issuer=src.source_issuer,
                        email=src.email,
                        email_verified=src.email_verified,
                        status="email_candidate",
                        internal_user_id=next(iter(user_ids)),
                        target_clerk_user_id=src.source_clerk_user_id,
                        proposed_roles=accepted,
                        match_method="email",
                        detail=detail,
                    )
                )
                continue

        # Unmatched — customer/driver may create; admin/merchant conflict
        roles = _default_persona_roles(src.source_app)
        if allowlist.allows_admin_id(src.source_clerk_user_id):
            roles = list(dict.fromkeys(roles + allowlist.roles_for(src.source_clerk_user_id)))
        accepted, rejected = _filter_roles(
            roles, clerk_user_id=src.source_clerk_user_id, allowlist=allowlist
        )
        if rejected:
            detail["rejected_invite_roles"] = rejected

        if src.source_app in ("admin", "merchant") and not accepted:
            records.append(
                PlannedRecord(
                    source_app=src.source_app,
                    source_clerk_user_id=src.source_clerk_user_id,
                    source_issuer=src.source_issuer,
                    email=src.email,
                    email_verified=src.email_verified,
                    status="conflict",
                    conflict_reason=f"{src.source_app}_requires_explicit_map_or_allowlist",
                    proposed_roles=[],
                    match_method=None,
                    detail=detail,
                )
            )
            continue

        records.append(
            PlannedRecord(
                source_app=src.source_app,
                source_clerk_user_id=src.source_clerk_user_id,
                source_issuer=src.source_issuer,
                email=src.email,
                email_verified=src.email_verified,
                status="unmatched",
                target_clerk_user_id=src.source_clerk_user_id,
                proposed_roles=accepted,
                match_method=None,
                detail=detail,
            )
        )

    by_app: dict[str, int] = defaultdict(int)
    for s in sources:
        by_app[s.source_app] += 1

    plan = MigrationPlan(
        label=label,
        records=records,
        source_summary={
            "source_count": len(sources),
            "by_app": dict(by_app),
            "map_links": len(explicit_map),
            "allowlist_admins": len(allowlist.legacy_admin_clerk_user_ids),
        },
    )
    plan.recompute_counts()
    return plan

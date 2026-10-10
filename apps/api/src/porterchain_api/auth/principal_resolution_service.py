"""Resolve AuthenticatedIdentity → CurrentPrincipal.

Identity + account status come from PostgreSQL.
Permissions / org membership come from SpiceDB (Zanzibar), not role-assignment tables.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.auth.current_principal import (
    CurrentPrincipal,
    RoleAssignmentView,
)
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.persona_bundle import PersonaBundle, load_persona_bundle
from porterchain_api.auth.unified_catalog import (
    AccountStatus,
    AssignableRole,
    AuthProvider,
    UnifiedPermission,
    admin_role_to_assignable,
    merchant_role_to_assignable,
)
from porterchain_api.authz.client import get_authz_client
from porterchain_api.authz.tuples import PLATFORM_ID
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.identity_models import IdentityLink
from porterchain_api.merchant_engine.rbac import parse_merchant_role
from porterchain_api.user_models import PorterchainUser

logger = logging.getLogger("porterchain.security")


class PrincipalResolutionService:
    """Resolve internal user from Postgres; authorize via SpiceDB Lookup/Check."""

    def resolve(self, db: Session, identity: AuthenticatedIdentity) -> CurrentPrincipal:
        user = self._resolve_user(db, identity)
        if not user:
            logger.info(
                "auth_reject reason=user_not_provisioned subject_present=%s",
                bool(identity.subject),
            )
            raise HTTPException(status_code=403, detail="user_not_provisioned")

        if user.status in (AccountStatus.SUSPENDED.value, AccountStatus.DEACTIVATED.value):
            logger.info("auth_reject reason=account_%s user_id=%s", user.status, user.id)
            raise HTTPException(status_code=403, detail=f"account_{user.status}")

        # IdentityLink is written on EnsureUser prepare; only heal if missing.
        self._ensure_identity_link(db, identity, user)

        # SpiceDB tuple sync belongs on EnsureUser (login prepare) / authorize mutations —
        # not on every principal resolve.
        roles, views, org_ids, legacy_ids = self._roles_from_profiles(db, identity.subject)
        permissions = self._permissions_from_spicedb(user.id, org_ids)

        status = user.status
        if status == AccountStatus.PENDING.value and roles:
            status = AccountStatus.ACTIVE.value

        return CurrentPrincipal(
            user_id=user.id,
            status=status,
            onboarding_status=getattr(user, "onboarding_status", None) or "not_started",
            email=user.email or identity.email,
            session_id=identity.session_id,
            default_workspace=getattr(user, "default_workspace", None),
            roles=frozenset(roles),
            role_assignments=views,
            permissions=permissions,
            organization_ids=frozenset(org_ids),
            auth_subject=identity.subject,
            auth_issuer=identity.issuer,
            auth_provider=identity.provider,
            legacy_profile_ids=legacy_ids,
        )

    def _permissions_from_spicedb(
        self, user_id: str, org_ids: set[str]
    ) -> frozenset[UnifiedPermission]:
        from porterchain_api.auth.modules_catalog import ADMIN_MODULE_TO_PERMISSION
        from porterchain_api.authz.client import BulkCheckItem

        client = get_authz_client()
        perms: set[UnifiedPermission] = set()
        try:
            # One BulkCheck for portal / system_all / admin modules / org portal.
            # Live require_module / require_relation remain the Check SoT — this pack
            # is session nav only. No Check-result cache.
            items: list[BulkCheckItem] = [
                BulkCheckItem("platform", PLATFORM_ID, "portal", subject_id=user_id),
                BulkCheckItem("platform", PLATFORM_ID, "system_all", subject_id=user_id),
            ]
            module_entries = list(ADMIN_MODULE_TO_PERMISSION.items())
            for module, _unified in module_entries:
                items.append(
                    BulkCheckItem("platform", PLATFORM_ID, module, subject_id=user_id)
                )
            org_list = sorted(org_ids)
            for org_id in org_list:
                items.append(
                    BulkCheckItem(
                        "organization", org_id, "portal", subject_id=user_id
                    )
                )

            results = client.bulk_check(items)
            if results[0]:
                perms.add(UnifiedPermission.PLATFORM_ADMIN_ACCESS)
            if results[1]:
                perms.add(UnifiedPermission.SYSTEM_ALL)
            else:
                # Project module Checks into unified perms for session nav.
                for idx, (_module, unified) in enumerate(module_entries):
                    if results[2 + idx]:
                        perms.add(unified)
            org_offset = 2 + len(module_entries)
            for i, _org_id in enumerate(org_list):
                if results[org_offset + i]:
                    perms.add(UnifiedPermission.MERCHANT_PORTAL_ACCESS)

            if client.lookup_resources(
                resource_type="driver_profile",
                permission="access",
                subject_id=user_id,
            ):
                perms.add(UnifiedPermission.DRIVER_PORTAL_ACCESS)
            if client.lookup_resources(
                resource_type="customer_profile",
                permission="access",
                subject_id=user_id,
            ):
                perms.add(UnifiedPermission.CUSTOMER_PORTAL_ACCESS)
        except Exception:  # noqa: BLE001
            logger.exception("spicedb_permission_lookup_failed user_id=%s", user_id)
        return frozenset(perms)

    def _roles_from_profiles(
        self, db: Session, subject: str
    ) -> tuple[set[AssignableRole], tuple[RoleAssignmentView, ...], set[str], dict[str, str]]:
        bundle = load_persona_bundle(db, subject)
        return self._roles_from_bundle(bundle)

    def _roles_from_bundle(
        self, bundle: PersonaBundle
    ) -> tuple[set[AssignableRole], tuple[RoleAssignmentView, ...], set[str], dict[str, str]]:
        roles: set[AssignableRole] = set()
        views: list[RoleAssignmentView] = []
        org_ids: set[str] = set()
        legacy_ids = bundle.legacy_profile_ids()

        admin = bundle.admin
        if admin is not None and admin.is_active:
            role = admin_role_to_assignable(parse_admin_role(admin.role))
            roles.add(role)
            views.append(RoleAssignmentView(role_key=role.value, scope_type="global", scope_id=""))

        for mu in bundle.merchant_users:
            if not mu.is_active:
                continue
            m_role = merchant_role_to_assignable(parse_merchant_role(mu.role))
            roles.add(m_role)
            org_ids.add(mu.merchant_id)
            views.append(
                RoleAssignmentView(
                    role_key=m_role.value,
                    scope_type="organization",
                    scope_id=mu.merchant_id,
                )
            )

        driver = bundle.driver
        if driver is not None and driver.status in (
            DriverStatus.APPROVED.value,
            DriverStatus.PENDING.value,
        ):
            roles.add(AssignableRole.DRIVER)
            views.append(
                RoleAssignmentView(
                    role_key=AssignableRole.DRIVER.value,
                    scope_type="self",
                    scope_id=driver.id,
                )
            )

        customer = bundle.customer
        if customer is not None:
            roles.add(AssignableRole.CUSTOMER)
            views.append(
                RoleAssignmentView(
                    role_key=AssignableRole.CUSTOMER.value,
                    scope_type="self",
                    scope_id=customer.id,
                )
            )

        return roles, tuple(views), org_ids, legacy_ids

    def _resolve_user(self, db: Session, identity: AuthenticatedIdentity) -> PorterchainUser | None:
        if identity.issuer and identity.subject:
            link = (
                db.query(IdentityLink)
                .filter(
                    IdentityLink.provider == (identity.provider or AuthProvider.CLERK.value),
                    IdentityLink.issuer == identity.issuer,
                    IdentityLink.subject == identity.subject,
                    IdentityLink.deactivated_at.is_(None),
                )
                .first()
            )
            if link:
                user = (
                    db.query(PorterchainUser)
                    .filter(PorterchainUser.id == link.platform_user_id)
                    .first()
                )
                if user:
                    return user
        if identity.subject:
            return (
                db.query(PorterchainUser)
                .filter(PorterchainUser.clerk_user_id == identity.subject)
                .first()
            )
        return None

    def _ensure_identity_link(
        self, db: Session, identity: AuthenticatedIdentity, user: PorterchainUser
    ) -> None:
        """Heal missing IdentityLink only — EnsureUser owns the primary write."""
        if not identity.subject:
            return
        existing = (
            db.query(IdentityLink)
            .filter(
                IdentityLink.provider == (identity.provider or AuthProvider.CLERK.value),
                IdentityLink.subject == identity.subject,
                IdentityLink.deactivated_at.is_(None),
            )
            .first()
        )
        if existing:
            if existing.platform_user_id != user.id:
                existing.platform_user_id = user.id
            return
        by_clerk = (
            db.query(IdentityLink)
            .filter(IdentityLink.clerk_user_id == identity.subject)
            .first()
        )
        if by_clerk:
            by_clerk.platform_user_id = user.id
            by_clerk.provider = identity.provider or AuthProvider.CLERK.value
            by_clerk.issuer = identity.issuer
            by_clerk.subject = identity.subject
            return
        db.add(
            IdentityLink(
                clerk_user_id=identity.subject,
                provider=identity.provider or AuthProvider.CLERK.value,
                issuer=identity.issuer,
                subject=identity.subject,
                platform_user_id=user.id,
                user_type=user.role or "unprovisioned",
            )
        )

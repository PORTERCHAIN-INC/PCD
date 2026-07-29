"""Synchronize Clerk-authenticated users into porterchain_users (masterrule §15)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.email_identity import (
    emails_match,
    normalize_email,
    unlink_email_mismatched_bindings,
)
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.auth.persona_principal import resolve_persona_principal
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.identity_models import IdentityLink
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.models import Customer
from porterchain_api.user_models import PorterchainUser
from porterchain_shared.auth.principal import AuthPrincipal
from porterchain_shared.types.user_types import UserType


def _is_pending_clerk_id(clerk_user_id: str | None) -> bool:
    if not clerk_user_id:
        return True
    if clerk_user_id == "dev_clerk_user":
        return True
    return clerk_user_id.startswith("pending:") or clerk_user_id.startswith("pending_")


class UserSyncService:
    """Login prepare: persona rebind + ensure account (SpiceDB + identity_link).

    Auth path is single-flight: rebind → EnsureUserService (no parallel identity_link
    writes that pointed platform_user_id at persona PKs).
    """

    def sync(self, db: Session, claims: ClerkClaims) -> PorterchainUser:
        from porterchain_api.auth.clerk_identity_provider import claims_to_identity
        from porterchain_api.auth.ensure_user_service import EnsureUserService

        unlink_email_mismatched_bindings(
            db, clerk_user_id=claims.clerk_user_id, clerk_email=claims.email
        )
        self._link_pending_domain_records(db, claims)
        if claims.email:
            InvitationService().mark_accepted(db, email=claims.email, clerk_user_id=claims.clerk_user_id)

        identity = claims_to_identity(claims)
        user = EnsureUserService().ensure_from_identity(
            db,
            identity,
            email_verified=bool(identity.email_verified if identity.email_verified is not None else identity.email),
            commit=True,
        )
        self._sync_fleetbase_link_metadata(db, claims, user)
        return user

    def get_by_clerk_id(self, db: Session, clerk_user_id: str) -> PorterchainUser | None:
        return db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == clerk_user_id).first()

    def _sync_fleetbase_link_metadata(
        self, db: Session, claims: ClerkClaims, user: PorterchainUser
    ) -> None:
        """Update Fleetbase SSO metadata on IdentityLink without mis-pointing platform_user_id."""
        principal = resolve_persona_principal(db, claims)
        link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == claims.clerk_user_id).first()
        if not link:
            return
        link.platform_user_id = user.id
        if not principal:
            db.commit()
            return

        fleetbase_perms: list[str] | None = None
        fleetbase_roles: list[str] | None = None
        if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
            admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
            if admin:
                from porterchain_api.auth.fleetbase_roles import fleetbase_permissions_for_admin

                admin_role = parse_admin_role(admin.role)
                fleetbase_perms = fleetbase_permissions_for_admin(admin_role)
                fleetbase_roles = [admin.role]

        link.user_type = principal.user_type.value
        link.platform_org_id = principal.org_id
        link.fleetbase_permissions = fleetbase_perms
        link.fleetbase_roles = fleetbase_roles
        link.last_synced_at = datetime.now(UTC)
        db.commit()

    def _link_pending_domain_records(self, db: Session, claims: ClerkClaims) -> None:
        """Attach Clerk user id when invite email equals Clerk verified email.

        Covers:
        - pending:* / null clerk ids (first accept)
        - stale clerk ids after Clerk account recreation (same verified email only)
        """
        email = normalize_email(claims.email)
        if not email or not claims.clerk_user_id:
            return
        clerk_id = claims.clerk_user_id

        if self._clerk_id_bound_to_other_email(db, clerk_id, email):
            return

        if self._rebind_persona_clerk_id(db, AdminUser, email, clerk_id):
            self._rebind_registry_clerk_id(db, email=email, new_clerk_id=clerk_id)
            return

        if self._rebind_persona_clerk_id(db, MerchantUser, email, clerk_id):
            self._rebind_registry_clerk_id(db, email=email, new_clerk_id=clerk_id)
            return

        if self._rebind_persona_clerk_id(db, Driver, email, clerk_id):
            self._rebind_registry_clerk_id(db, email=email, new_clerk_id=clerk_id)

    @staticmethod
    def _rebind_persona_clerk_id(db: Session, model: type, email: str, clerk_id: str) -> bool:
        """Rebind a single persona row to clerk_id when email matches. Returns True if rebound."""
        row = db.query(model).filter(model.email == email).first()
        if not row or not emails_match(getattr(row, "email", None), email):
            return False
        if row.clerk_user_id == clerk_id:
            return False

        taken = db.query(model).filter(model.clerk_user_id == clerk_id).first()
        if taken and taken.id != row.id:
            return False

        # Allow pending first-link OR stale-id rebind for the same verified email.
        row.clerk_user_id = clerk_id
        return True

    @staticmethod
    def _rebind_registry_clerk_id(db: Session, *, email: str, new_clerk_id: str) -> None:
        """Move porterchain_users + identity_links to the new Clerk subject for this email."""
        user = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.email == email)
            .order_by(PorterchainUser.created_at.asc())
            .first()
        )
        if not user:
            return
        if user.clerk_user_id == new_clerk_id:
            return

        shell = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.clerk_user_id == new_clerk_id, PorterchainUser.id != user.id)
            .first()
        )
        if shell:
            # Drop empty auto-provisioned shell for the new Clerk id.
            db.query(IdentityLink).filter(IdentityLink.platform_user_id == shell.id).delete(
                synchronize_session=False
            )
            db.delete(shell)
            db.flush()

        old_clerk_id = user.clerk_user_id
        user.clerk_user_id = new_clerk_id
        for link in (
            db.query(IdentityLink)
            .filter(
                or_(
                    IdentityLink.platform_user_id == user.id,
                    IdentityLink.clerk_user_id == old_clerk_id,
                )
            )
            .all()
        ):
            link.clerk_user_id = new_clerk_id
            link.subject = new_clerk_id
            link.email = email
            link.is_current = True

    @staticmethod
    def _clerk_id_bound_to_other_email(db: Session, clerk_user_id: str, email: str) -> bool:
        """True when this Clerk id is already linked to a different email in any user class."""
        for model in (AdminUser, MerchantUser, Driver, Customer):
            row = db.query(model).filter(model.clerk_user_id == clerk_user_id).first()
            if row and not emails_match(getattr(row, "email", None), email):
                return True
        return False

    def _platform_snapshot(
        self,
        db: Session,
        claims: ClerkClaims,
        principal: AuthPrincipal | None,
    ) -> dict[str, Any]:
        if not principal:
            # Never promote Clerk metadata into an elevated registry role
            return {
                "role": "unprovisioned",
                "status": "pending",
                "phone": claims.phone,
                "profile": {
                    "clerk_org_id": claims.org_id,
                    "public_metadata": claims.public_metadata or {},
                    "provisioned": False,
                },
            }

        phone = claims.phone
        profile: dict[str, Any] = {
            "user_type": principal.user_type.value,
            "platform_user_id": principal.user_id,
            "clerk_org_id": claims.org_id or principal.org_id,
            "public_metadata": claims.public_metadata or {},
            "provisioned": True,
        }

        if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT, UserType.SALES):
            admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
            if admin:
                profile["name"] = admin.name
                return {
                    "role": admin.role,
                    "status": "active" if admin.is_active else "inactive",
                    "phone": phone,
                    "profile": {**profile, "admin_role": admin.role},
                }

        if principal.user_type == UserType.MERCHANT:
            mu = db.query(MerchantUser).filter(MerchantUser.id == principal.user_id).first()
            merchant = db.query(Merchant).filter(Merchant.id == principal.org_id).first() if principal.org_id else None
            if mu:
                profile["merchant_id"] = mu.merchant_id
                status = "active"
                if merchant and merchant.status != MerchantStatus.ACTIVE.value:
                    status = "inactive"
                elif not mu.is_active:
                    status = "inactive"
                return {
                    "role": mu.role,
                    "status": status,
                    "phone": phone,
                    "profile": {
                        **profile,
                        "merchant_role": mu.role,
                    },
                }

        if principal.user_type == UserType.DRIVER:
            driver = db.query(Driver).filter(Driver.id == principal.user_id).first()
            if driver:
                profile["name"] = driver.full_name
                phone = phone or driver.phone
                status = "active"
                if driver.status == DriverStatus.SUSPENDED.value:
                    status = "suspended"
                elif driver.status not in (DriverStatus.APPROVED.value, DriverStatus.PENDING.value):
                    status = "inactive"
                return {"role": "driver", "status": status, "phone": phone, "profile": profile}

        if principal.user_type == UserType.CUSTOMER:
            customer = db.query(Customer).filter(Customer.id == principal.user_id).first()
            if customer:
                phone = phone or customer.phone
                return {"role": "customer", "status": "active", "phone": phone, "profile": profile}

        return {
            "role": principal.user_type.value,
            "status": "active",
            "phone": phone,
            "profile": profile,
        }

    def _upsert_user(self, db: Session, claims: ClerkClaims, snapshot: dict[str, Any]) -> PorterchainUser:
        now = datetime.now(UTC)
        row = db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == claims.clerk_user_id).first()
        email = (claims.email or "").lower() or None

        if row:
            if email:
                row.email = email
            if snapshot.get("phone"):
                row.phone = snapshot["phone"]
            row.role = snapshot["role"]
            row.status = snapshot["status"]
            merged_profile = {**(row.profile or {}), **snapshot["profile"]}
            row.profile = merged_profile
            row.last_synced_at = now
            return row

        row = PorterchainUser(
            clerk_user_id=claims.clerk_user_id,
            email=email,
            phone=snapshot.get("phone"),
            role=snapshot["role"],
            status=snapshot["status"],
            profile=snapshot["profile"],
            last_synced_at=now,
        )
        db.add(row)
        return row

    def _upsert_identity_link(self, db: Session, claims: ClerkClaims, principal: AuthPrincipal) -> IdentityLink:
        """Upsert IdentityLink. platform_user_id is always porterchain_users.id (never persona PK)."""
        user = self.get_by_clerk_id(db, claims.clerk_user_id)
        if not user:
            snapshot = self._platform_snapshot(db, claims, principal)
            user = self._upsert_user(db, claims, snapshot)
            db.flush()

        link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == claims.clerk_user_id).first()
        fleetbase_perms: list[str] | None = None
        fleetbase_roles: list[str] | None = None

        if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
            admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
            if admin:
                from porterchain_api.auth.fleetbase_roles import fleetbase_permissions_for_admin

                admin_role = parse_admin_role(admin.role)
                fleetbase_perms = fleetbase_permissions_for_admin(admin_role)
                fleetbase_roles = [admin.role]

        if not link:
            link = IdentityLink(
                clerk_user_id=claims.clerk_user_id,
                email=claims.email or principal.email,
                user_type=principal.user_type.value,
                platform_user_id=user.id,
                platform_org_id=principal.org_id,
                fleetbase_permissions=fleetbase_perms,
                fleetbase_roles=fleetbase_roles,
                provider="clerk",
                issuer=claims.issuer,
                subject=claims.clerk_user_id,
                is_current=True,
                is_legacy=False,
                linked_at=datetime.now(UTC),
            )
            db.add(link)
        else:
            link.email = claims.email or principal.email or link.email
            link.user_type = principal.user_type.value
            link.platform_user_id = user.id
            link.platform_org_id = principal.org_id
            link.fleetbase_permissions = fleetbase_perms
            link.fleetbase_roles = fleetbase_roles
            link.last_synced_at = datetime.now(UTC)
            if claims.issuer:
                link.issuer = claims.issuer
            link.subject = claims.clerk_user_id
            link.provider = link.provider or "clerk"

        return link

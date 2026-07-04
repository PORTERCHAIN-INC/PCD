"""Synchronize Clerk-authenticated users into porterchain_users (masterrule §15)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.enterprise_rbac import (
    enterprise_role_for_admin,
    enterprise_role_for_merchant,
)
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.auth.principal_resolver import PrincipalResolver
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
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
    """Upsert canonical user row + identity link on every Clerk authentication."""

    def __init__(self) -> None:
        self._resolver = PrincipalResolver()

    def sync(self, db: Session, claims: ClerkClaims) -> PorterchainUser:
        self._link_pending_domain_records(db, claims)
        principal = self._resolver.resolve(db, claims)
        snapshot = self._platform_snapshot(db, claims, principal)
        user = self._upsert_user(db, claims, snapshot)
        if principal:
            self._upsert_identity_link(db, claims, principal)
        if claims.email:
            InvitationService().mark_accepted(db, email=claims.email, clerk_user_id=claims.clerk_user_id)
        db.commit()
        db.refresh(user)
        return user

    def get_by_clerk_id(self, db: Session, clerk_user_id: str) -> PorterchainUser | None:
        return db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == clerk_user_id).first()

    def _link_pending_domain_records(self, db: Session, claims: ClerkClaims) -> None:
        """Attach Clerk user id to at most one pre-provisioned row (invite / pending:* only)."""
        if not claims.email or not claims.clerk_user_id:
            return
        email = claims.email.lower()
        clerk_id = claims.clerk_user_id

        if self._clerk_id_bound_to_other_email(db, clerk_id, email):
            return

        admin = db.query(AdminUser).filter(AdminUser.email == email).first()
        if admin and admin.clerk_user_id != clerk_id and _is_pending_clerk_id(admin.clerk_user_id):
            admin.clerk_user_id = clerk_id
            return

        merchant_user = db.query(MerchantUser).filter(MerchantUser.email == email).first()
        if (
            merchant_user
            and merchant_user.clerk_user_id != clerk_id
            and _is_pending_clerk_id(merchant_user.clerk_user_id)
        ):
            merchant_user.clerk_user_id = clerk_id
            return

        driver = db.query(Driver).filter(Driver.email == email).first()
        if driver and driver.clerk_user_id != clerk_id and _is_pending_clerk_id(driver.clerk_user_id):
            driver.clerk_user_id = clerk_id

    @staticmethod
    def _clerk_id_bound_to_other_email(db: Session, clerk_user_id: str, email: str) -> bool:
        """True when this Clerk id is already linked to a different email in any user class."""
        normalized = email.lower()
        for model, email_attr in (
            (AdminUser, "email"),
            (MerchantUser, "email"),
            (Driver, "email"),
            (Customer, "email"),
        ):
            row = db.query(model).filter(model.clerk_user_id == clerk_user_id).first()
            if row and getattr(row, email_attr, "").lower() != normalized:
                return True
        return False

    def _platform_snapshot(
        self,
        db: Session,
        claims: ClerkClaims,
        principal: AuthPrincipal | None,
    ) -> dict[str, Any]:
        if not principal:
            meta_role = (claims.metadata_role or claims.org_role or "unprovisioned").lower()
            return {
                "role": meta_role,
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
                ent = enterprise_role_for_admin(parse_admin_role(admin.role))
                return {
                    "role": ent.value,
                    "status": "active" if admin.is_active else "inactive",
                    "phone": phone,
                    "profile": {**profile, "admin_role": admin.role, "enterprise_role": ent.value},
                }

        if principal.user_type == UserType.MERCHANT:
            mu = db.query(MerchantUser).filter(MerchantUser.id == principal.user_id).first()
            merchant = db.query(Merchant).filter(Merchant.id == principal.org_id).first() if principal.org_id else None
            if mu:
                profile["merchant_id"] = mu.merchant_id
                m_role = MerchantRole(mu.role) if mu.role in {r.value for r in MerchantRole} else MerchantRole.OPS
                ent = enterprise_role_for_merchant(m_role)
                status = "active"
                if merchant and merchant.status != MerchantStatus.ACTIVE.value:
                    status = "inactive"
                elif not mu.is_active:
                    status = "inactive"
                return {
                    "role": ent.value,
                    "status": status,
                    "phone": phone,
                    "profile": {
                        **profile,
                        "merchant_role": mu.role,
                        "enterprise_role": ent.value,
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
                platform_user_id=principal.user_id,
                platform_org_id=principal.org_id,
                fleetbase_permissions=fleetbase_perms,
                fleetbase_roles=fleetbase_roles,
            )
            db.add(link)
        else:
            link.email = claims.email or principal.email or link.email
            link.user_type = principal.user_type.value
            link.platform_user_id = principal.user_id
            link.platform_org_id = principal.org_id
            link.fleetbase_permissions = fleetbase_perms
            link.fleetbase_roles = fleetbase_roles
            link.last_synced_at = datetime.now(UTC)

        return link

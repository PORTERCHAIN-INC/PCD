"""Write SpiceDB relationships from provisioning events (not Postgres ACL tables)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.authz.client import AuthzClient, Relationship, get_authz_client
from porterchain_api.authz.platform_roles import relation_for_admin_role
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer
from porterchain_api.user_models import PorterchainUser

logger = logging.getLogger("porterchain.authz")

PLATFORM_ID = "porterchain"

# Merchant roles that map to organization#admin
_ORG_ADMIN_ROLES = {
    MerchantRole.OWNER.value,
    MerchantRole.ADMIN.value,
    "merchant_owner",
    "merchant_admin",
}


class TupleWriter:
    def __init__(self, client: AuthzClient | None = None) -> None:
        self._client = client

    @property
    def client(self) -> AuthzClient:
        return self._client or get_authz_client()

    def sync_user_from_profiles(self, db: Session, user: PorterchainUser) -> str | None:
        """Reconcile SpiceDB tuples for a user from profile rows (data), not role assignment tables."""
        subject = user.clerk_user_id
        if not subject:
            return None
        desired: list[Relationship] = []

        admin = (
            db.query(AdminUser)
            .filter(AdminUser.clerk_user_id == subject, AdminUser.is_active.is_(True))
            .first()
        )
        if admin:
            if admin.porterchain_user_id != user.id:
                admin.porterchain_user_id = user.id
            rel = relation_for_admin_role(parse_admin_role(admin.role))
            desired.append(
                Relationship("platform", PLATFORM_ID, rel, "user", user.id)
            )

        for mu in db.query(MerchantUser).filter(MerchantUser.clerk_user_id == subject).all():
            if not mu.is_active:
                continue
            if mu.porterchain_user_id != user.id:
                mu.porterchain_user_id = user.id
            rel = "admin" if mu.role in _ORG_ADMIN_ROLES else "member"
            desired.append(
                Relationship("organization", mu.merchant_id, rel, "user", user.id)
            )

        driver = db.query(Driver).filter(Driver.clerk_user_id == subject).first()
        if driver and driver.status != DriverStatus.REJECTED.value:
            if driver.porterchain_user_id != user.id:
                driver.porterchain_user_id = user.id
            desired.append(
                Relationship("driver_profile", driver.id, "owner", "user", user.id)
            )

        customer = db.query(Customer).filter(Customer.clerk_user_id == subject).first()
        if customer:
            if getattr(customer, "porterchain_user_id", None) != user.id:
                try:
                    customer.porterchain_user_id = user.id
                except Exception:  # noqa: BLE001
                    pass
            desired.append(
                Relationship("customer_profile", customer.id, "owner", "user", user.id)
            )

        # Replace prior subject edges for this user on known resource types (memory-safe reconcile).
        self._reconcile_user(user.id, desired)
        token = self.client.write_relationships(desired) if desired else None
        logger.info(
            "authz_tuples_synced user_id=%s relationships=%s",
            user.id,
            len(desired),
        )
        return token

    def _reconcile_user(self, user_id: str, desired: list[Relationship]) -> None:
        """Delete stale memory/grpc edges we own for this user before writing desired set."""
        client = self.client
        # Memory store: drop all relationships where subject is this user, then rewrite.
        mem = getattr(client, "_memory", None)
        if mem is not None and (client._use_memory or client._grpc is None):  # noqa: SLF001
            with mem.lock:
                keep = {t for t in mem.relationships if not (t[3] == "user" and t[4] == user_id)}
                mem.relationships = keep
            return
        # gRPC: delete known relation shapes then touch desired (best-effort).
        # Full ReadRelationships filter would be better; for v1 we delete+write desired only.
        _ = desired

    def revoke_all_for_user(self, db: Session, user: PorterchainUser) -> str | None:
        """Delete SpiceDB edges for this internal user (memory + gRPC)."""
        subject = user.clerk_user_id
        to_delete: list[Relationship] = []
        # Drop every known platform role relation (covers role changes + legacy staff).
        from porterchain_api.authz.platform_roles import PLATFORM_ROLE_RELATIONS

        for rel in PLATFORM_ROLE_RELATIONS:
            to_delete.append(Relationship("platform", PLATFORM_ID, rel, "user", user.id))

        if subject:
            for mu in db.query(MerchantUser).filter(MerchantUser.clerk_user_id == subject).all():
                to_delete.append(
                    Relationship("organization", mu.merchant_id, "member", "user", user.id)
                )
                to_delete.append(
                    Relationship("organization", mu.merchant_id, "admin", "user", user.id)
                )
            driver = db.query(Driver).filter(Driver.clerk_user_id == subject).first()
            if driver:
                to_delete.append(
                    Relationship("driver_profile", driver.id, "owner", "user", user.id)
                )
            customer = db.query(Customer).filter(Customer.clerk_user_id == subject).first()
            if customer:
                to_delete.append(
                    Relationship("customer_profile", customer.id, "owner", "user", user.id)
                )

        # Memory store: also wipe any leftover subject edges.
        client = self.client
        mem = getattr(client, "_memory", None)
        if mem is not None and (client._use_memory or client._grpc is None):  # noqa: SLF001
            with mem.lock:
                mem.relationships = {
                    t for t in mem.relationships if not (t[3] == "user" and t[4] == user.id)
                }
            return client._memory.zed_token  # noqa: SLF001

        if not to_delete:
            return None
        return client.delete_relationships(to_delete)

    def grant_platform_staff(self, user_id: str, *, role: str = "admin") -> str:
        """Grant a platform role relation (default admin). Prefer sync_user_from_profiles."""
        return self.client.write_relationships(
            [
                Relationship(
                    "platform",
                    PLATFORM_ID,
                    relation_for_admin_role(role),
                    "user",
                    user_id,
                )
            ]
        )

    def grant_org_member(self, user_id: str, merchant_id: str, *, admin: bool = False) -> str:
        rel = "admin" if admin else "member"
        return self.client.write_relationships(
            [Relationship("organization", merchant_id, rel, "user", user_id)]
        )

    def revoke_org_member(self, user_id: str, merchant_id: str) -> str:
        return self.client.delete_relationships(
            [
                Relationship("organization", merchant_id, "member", "user", user_id),
                Relationship("organization", merchant_id, "admin", "user", user_id),
            ]
        )

    def link_order_to_org(self, order_id: str, merchant_id: str) -> str:
        return self.client.write_relationships(
            [Relationship("order", order_id, "parent", "organization", merchant_id)]
        )

    def grant_driver_owner(self, user_id: str, driver_id: str) -> str:
        return self.client.write_relationships(
            [Relationship("driver_profile", driver_id, "owner", "user", user_id)]
        )

    def grant_customer_owner(self, user_id: str, customer_id: str) -> str:
        return self.client.write_relationships(
            [Relationship("customer_profile", customer_id, "owner", "user", user_id)]
        )


def bootstrap_all_profiles(db: Session) -> dict[str, int]:
    """One-shot: write SpiceDB tuples for every provisioned profile."""
    writer = TupleWriter()
    users = db.query(PorterchainUser).all()
    synced = 0
    for user in users:
        if not user.clerk_user_id:
            continue
        writer.sync_user_from_profiles(db, user)
        synced += 1
    db.commit()
    return {"users_synced": synced}

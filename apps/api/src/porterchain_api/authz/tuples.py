"""Write SpiceDB relationships from provisioning events (not Postgres ACL tables)."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.driver_lookups import (
    get_driver_by_clerk,
    stamp_driver_porterchain_user_id,
)
from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_engine.staff_lookups import stamp_admin_porterchain_user_id
from porterchain_api.authz.client import AuthzClient, Relationship, get_authz_client
from porterchain_api.authz.platform_roles import relation_for_admin_role
from porterchain_api.booking_models import Customer
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.lookups import (
    active_seats_for_clerk,
    seats_for_clerk,
)
from porterchain_api.user_models import PorterchainUser

logger = logging.getLogger("porterchain.authz")

PLATFORM_ID = "porterchain"

# organization relations — mirrors MerchantRole (plus legacy ``member`` for revoke)
ORG_ROLE_RELATIONS: tuple[str, ...] = (
    "owner",
    "admin",
    "ops",
    "finance",
    "readonly",
    "member",
)

_MERCHANT_ROLE_TO_ORG_RELATION: dict[str, str] = {
    MerchantRole.OWNER.value: "owner",
    MerchantRole.ADMIN.value: "admin",
    MerchantRole.OPS.value: "ops",
    MerchantRole.FINANCE.value: "finance",
    MerchantRole.READONLY.value: "readonly",
    "merchant_owner": "owner",
    "merchant_admin": "admin",
    "merchant_ops": "ops",
    "merchant_finance": "finance",
    "merchant_readonly": "readonly",
}


def relation_for_merchant_role(role: str) -> str:
    return _MERCHANT_ROLE_TO_ORG_RELATION.get(role, "ops")


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

        admin = stamp_admin_porterchain_user_id(db, subject, user.id)
        if admin:
            rel = relation_for_admin_role(parse_admin_role(admin.role))
            desired.append(
                Relationship("platform", PLATFORM_ID, rel, "user", user.id)
            )

        for mu in active_seats_for_clerk(db, subject, user_id=user.id):
            rel = relation_for_merchant_role(mu.role)
            desired.append(
                Relationship("organization", mu.merchant_id, rel, "user", user.id)
            )

        driver = stamp_driver_porterchain_user_id(db, subject, user.id)
        # PENDING needs portal access for onboarding; SUSPENDED/REJECTED must lose tuples.
        if driver and driver.status in (
            DriverStatus.APPROVED.value,
            DriverStatus.PENDING.value,
        ):
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

        # Full reconcile: drop all known edges (memory + gRPC), then write the desired set.
        self.revoke_all_for_user(db, user)
        token = self.client.write_relationships(desired) if desired else None
        logger.info(
            "authz_tuples_synced user_id=%s relationships=%s",
            user.id,
            len(desired),
        )
        return token

    def revoke_all_for_user(self, db: Session, user: PorterchainUser) -> str | None:
        """Delete SpiceDB edges for this internal user (memory + gRPC)."""
        subject = user.clerk_user_id
        to_delete: list[Relationship] = []
        # Drop every known platform role relation (covers role changes + legacy staff).
        from porterchain_api.authz.platform_roles import PLATFORM_ROLE_RELATIONS

        for rel in PLATFORM_ROLE_RELATIONS:
            to_delete.append(Relationship("platform", PLATFORM_ID, rel, "user", user.id))

        if subject:
            for mu in seats_for_clerk(db, subject):
                for rel in ORG_ROLE_RELATIONS:
                    to_delete.append(
                        Relationship("organization", mu.merchant_id, rel, "user", user.id)
                    )
            driver = get_driver_by_clerk(db, subject)
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
        if mem is not None and (client._use_memory or client._grpc is None):
            with mem.lock:
                mem.relationships = {
                    t for t in mem.relationships if not (t[3] == "user" and t[4] == user.id)
                }
            return client._memory.zed_token

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

    def grant_org_member(
        self,
        user_id: str,
        merchant_id: str,
        *,
        admin: bool = False,
        role: str | None = None,
    ) -> str:
        if role:
            rel = relation_for_merchant_role(role)
        else:
            rel = "admin" if admin else "ops"
        return self.client.write_relationships(
            [Relationship("organization", merchant_id, rel, "user", user_id)]
        )

    def revoke_org_member(self, user_id: str, merchant_id: str) -> str:
        return self.client.delete_relationships(
            [
                Relationship("organization", merchant_id, rel, "user", user_id)
                for rel in ORG_ROLE_RELATIONS
            ]
        )

    def link_order_to_org(self, order_id: str, merchant_id: str) -> str:
        return self.client.write_relationships(
            [Relationship("order", order_id, "parent", "organization", merchant_id)]
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

"""Single-flight persona lookup for a Clerk subject.

All auth hot-path callers (portal_guard, EnsureUser role hint, principal
resolution, conflict checks) should use ``load_persona_bundle`` instead of
re-querying AdminUser / MerchantUser / Driver / Customer independently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.dev import is_dev_bypass_subject
from porterchain_api.booking_models import Customer
from porterchain_api.merchant_models import MerchantUser

_CACHE_KEY = "_persona_bundles"


@dataclass
class PersonaBundle:
    clerk_user_id: str
    admin: AdminUser | None = None
    merchant_users: list[MerchantUser] = field(default_factory=list)
    driver: Driver | None = None
    customer: Customer | None = None

    def membership(self) -> dict[str, bool]:
        return {
            "admin": self.admin is not None,
            "merchant": bool(self.merchant_users),
            "driver": self.driver is not None,
            "customer": self.customer is not None,
        }

    def staff_portal(self) -> str | None:
        """First non-customer portal this Clerk id is provisioned for."""
        if self.admin is not None:
            return "admin"
        if self.merchant_users:
            return "merchant"
        if self.driver is not None:
            return "driver"
        return None

    def legacy_profile_ids(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if self.admin is not None:
            out["admin_user_id"] = self.admin.id
        if self.merchant_users:
            mu = self.merchant_users[0]
            out["merchant_user_id"] = mu.id
            out["merchant_id"] = mu.merchant_id
        if self.driver is not None:
            out["driver_id"] = self.driver.id
        if self.customer is not None:
            out["customer_id"] = self.customer.id
        return out

    def active_merchant_users(self) -> list[MerchantUser]:
        return [mu for mu in self.merchant_users if mu.is_active]


def load_persona_bundle(db: Session, clerk_user_id: str, *, force: bool = False) -> PersonaBundle:
    """Load (and request-cache) persona rows for a Clerk subject."""
    if not clerk_user_id or clerk_user_id.startswith("pending:") or is_dev_bypass_subject(clerk_user_id):
        return PersonaBundle(clerk_user_id=clerk_user_id or "")

    cache: dict[str, PersonaBundle] = db.info.setdefault(_CACHE_KEY, {})
    if not force and clerk_user_id in cache:
        return cache[clerk_user_id]

    bundle = PersonaBundle(
        clerk_user_id=clerk_user_id,
        admin=db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_user_id).first(),
        merchant_users=list(
            db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).all()
        ),
        driver=db.query(Driver).filter(Driver.clerk_user_id == clerk_user_id).first(),
        customer=db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first(),
    )
    cache[clerk_user_id] = bundle
    return bundle


def invalidate_persona_bundle(db: Session, clerk_user_id: str | None = None) -> None:
    """Drop cached bundles after persona mutations in the same request."""
    cache = db.info.get(_CACHE_KEY)
    if not cache:
        return
    if clerk_user_id is None:
        cache.clear()
        return
    cache.pop(clerk_user_id, None)

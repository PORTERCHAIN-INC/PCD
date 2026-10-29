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
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.booking_models import Customer

_CACHE_KEY = "_persona_bundles"


@dataclass
class PersonaBundle:
    auth_subject: str
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


def load_persona_bundle(db: Session, auth_subject: str, *, force: bool = False) -> PersonaBundle:
    """Load (and request-cache) persona rows for a Clerk subject."""
    if not auth_subject or auth_subject.startswith("pending:") or is_dev_bypass_subject(auth_subject):
        return PersonaBundle(auth_subject=auth_subject or "")

    cache: dict[str, PersonaBundle] = db.info.setdefault(_CACHE_KEY, {})
    if not force and auth_subject in cache:
        return cache[auth_subject]

    bundle = PersonaBundle(
        auth_subject=auth_subject,
        admin=db.query(AdminUser).filter(AdminUser.auth_subject == auth_subject).first(),
        merchant_users=list(
            db.query(MerchantUser).filter(MerchantUser.auth_subject == auth_subject).all()
        ),
        driver=db.query(Driver).filter(Driver.auth_subject == auth_subject).first(),
        customer=db.query(Customer).filter(Customer.auth_subject == auth_subject).first(),
    )
    cache[auth_subject] = bundle
    return bundle


def invalidate_persona_bundle(db: Session, auth_subject: str | None = None) -> None:
    """Drop cached bundles after persona mutations in the same request."""
    cache = db.info.get(_CACHE_KEY)
    if not cache:
        return
    if auth_subject is None:
        cache.clear()
        return
    cache.pop(auth_subject, None)

"""Ensure internal user + SpiceDB tuple sync — never elevate from Clerk metadata."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.auth.email_identity import (
    emails_match,
    normalize_email,
    unlink_email_mismatched_bindings,
)
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.account_lifecycle import activate_pending_user
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.auth.unified_catalog import (
    AccountStatus,
    AssignableRole,
    AuthProvider,
    OnboardingStatus,
    admin_role_to_assignable,
    is_invite_only,
    merchant_role_to_assignable,
)
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.identity_models import IdentityLink
from porterchain_api.merchant_engine.rbac import parse_merchant_role
from porterchain_api.unified_identity_models import UserEmail
from porterchain_api.user_models import PorterchainUser

logger = logging.getLogger("porterchain.security")

__all__ = ["EnsureUserService", "normalize_email"]


class EnsureUserService:
    """
    Synchronous ensure-internal-user used after authentication and by webhooks.

    Rules:
    - Never grant invite-only / admin roles from Clerk metadata or email domain.
    - Dual-write role assignments only from legacy profiles whose email matches Clerk.
    - System profile email must equal Clerk verified email (mismatch → unlink, no authz).
    """

    def ensure_from_identity(
        self,
        db: Session,
        identity: AuthenticatedIdentity,
        *,
        email_verified: bool | None = None,
        commit: bool = False,
        skip_unlink: bool = False,
        sync_spicedb: bool = True,
    ) -> PorterchainUser:
        if not skip_unlink:
            unlink_email_mismatched_bindings(
                db, clerk_user_id=identity.subject, clerk_email=identity.email
            )
        user = self._resolve_or_create_user(db, identity)
        verified = bool(email_verified if email_verified is not None else identity.email_verified)
        self._upsert_email(db, user, identity.email, verified=verified)
        self._upsert_identity_link(db, identity, user)
        self._refresh_account_role_hint(db, user, identity.subject, identity.email)
        # Authz lives in SpiceDB — sync relationship tuples from profile rows (data).
        # Single write site on the login prepare path (principal resolve must not re-sync).
        if commit:
            db.commit()
            db.refresh(user)
        else:
            db.flush()
        if sync_spicedb:
            try:
                from porterchain_api.authz.tuples import TupleWriter

                TupleWriter().sync_user_from_profiles(db, user)
                if commit:
                    db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("spicedb_tuple_sync_failed user_id=%s", user.id)
        try:
            from porterchain_api.auth.principal_cache import cache_invalidate

            cache_invalidate(user.id)
        except Exception:  # noqa: BLE001
            pass
        return user

    def ensure_from_clerk_user_payload(
        self,
        db: Session,
        *,
        clerk_user_id: str,
        email: str | None,
        email_verified: bool,
        phone: str | None,
        issuer: str | None,
        commit: bool = True,
    ) -> PorterchainUser:
        identity = AuthenticatedIdentity(
            provider=AuthProvider.CLERK.value,
            issuer=issuer,
            subject=clerk_user_id,
            email=normalize_email(email),
            email_verified=email_verified,
        )
        user = self.ensure_from_identity(db, identity, email_verified=email_verified, commit=False)
        if phone and not user.phone:
            user.phone = phone
        if commit:
            db.commit()
            db.refresh(user)
        else:
            db.flush()
        return user

    def deactivate_clerk_user(self, db: Session, *, clerk_user_id: str, commit: bool = True) -> None:
        """Deactivate auth identity + account. Never cascade-delete operational data."""
        now = datetime.now(UTC)
        user = db.query(PorterchainUser).filter(PorterchainUser.clerk_user_id == clerk_user_id).first()
        if user:
            user.status = AccountStatus.DEACTIVATED.value
            try:
                from porterchain_api.authz.tuples import TupleWriter

                TupleWriter().revoke_all_for_user(db, user)
            except Exception:  # noqa: BLE001
                logger.exception("spicedb_revoke_on_deactivate_failed user_id=%s", user.id)
        for link in db.query(IdentityLink).filter(IdentityLink.clerk_user_id == clerk_user_id).all():
            link.is_current = False
            link.deactivated_at = now
        for link in (
            db.query(IdentityLink)
            .filter(IdentityLink.subject == clerk_user_id, IdentityLink.deactivated_at.is_(None))
            .all()
        ):
            link.is_current = False
            link.deactivated_at = now
        logger.info("clerk_user_deactivated")
        if commit:
            db.commit()
        else:
            db.flush()

    def _resolve_or_create_user(self, db: Session, identity: AuthenticatedIdentity) -> PorterchainUser:
        user = (
            db.query(PorterchainUser)
            .filter(PorterchainUser.clerk_user_id == identity.subject)
            .first()
        )
        if not user and identity.issuer:
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
                user = db.query(PorterchainUser).filter(PorterchainUser.id == link.platform_user_id).first()

        email = normalize_email(identity.email)
        if not user:
            user = PorterchainUser(
                clerk_user_id=identity.subject,
                email=email,
                role="unprovisioned",
                status=AccountStatus.PENDING.value,
                onboarding_status=OnboardingStatus.NOT_STARTED.value,
                profile={"provisioned": False, "source": "ensure_user"},
            )
            db.add(user)
            db.flush()
            return user

        if email and user.email != email:
            user.email = email

        # Strip elevated registry role unless a real matching admin_users row exists
        try:
            if user.role and is_invite_only(user.role):
                admin_row = load_persona_bundle(db, identity.subject).admin
                if (
                    admin_row is None
                    or not admin_row.is_active
                    or not emails_match(admin_row.email, email)
                ):
                    logger.warning("ensure_user_stripped_elevated_registry_role")
                    user.role = "unprovisioned"
        except ValueError:
            pass
        return user

    def _upsert_email(
        self,
        db: Session,
        user: PorterchainUser,
        email: str | None,
        *,
        verified: bool,
    ) -> None:
        normalized = normalize_email(email)
        if not normalized:
            return
        row = (
            db.query(UserEmail)
            .filter(UserEmail.user_id == user.id, UserEmail.normalized_email == normalized)
            .first()
        )
        if not row:
            if verified:
                db.query(UserEmail).filter(UserEmail.user_id == user.id, UserEmail.is_primary.is_(True)).update(
                    {"is_primary": False}
                )
            db.add(
                UserEmail(
                    user_id=user.id,
                    normalized_email=normalized,
                    is_verified=verified,
                    is_primary=True,
                    source="clerk",
                )
            )
        elif verified:
            row.is_verified = True

    def _upsert_identity_link(
        self,
        db: Session,
        identity: AuthenticatedIdentity,
        user: PorterchainUser,
    ) -> None:
        link = db.query(IdentityLink).filter(IdentityLink.clerk_user_id == identity.subject).first()
        now = datetime.now(UTC)
        if not link:
            db.add(
                IdentityLink(
                    clerk_user_id=identity.subject,
                    email=normalize_email(identity.email) or user.email,
                    user_type="unprovisioned",
                    platform_user_id=user.id,
                    provider=identity.provider or AuthProvider.CLERK.value,
                    issuer=identity.issuer,
                    subject=identity.subject,
                    is_current=True,
                    is_legacy=False,
                    linked_at=now,
                )
            )
            return

        existing = db.query(PorterchainUser.id).filter(PorterchainUser.id == link.platform_user_id).first()
        # Always bind IdentityLink to porterchain_users.id (never a persona PK).
        if not existing or link.platform_user_id != user.id:
            link.platform_user_id = user.id
        link.provider = link.provider or identity.provider or AuthProvider.CLERK.value
        if identity.issuer:
            link.issuer = identity.issuer
        link.subject = identity.subject
        link.is_current = True
        if identity.email:
            link.email = normalize_email(identity.email)
        if not link.linked_at:
            link.linked_at = now

    def _refresh_account_role_hint(
        self,
        db: Session,
        user: PorterchainUser,
        subject: str,
        clerk_email: str | None = None,
    ) -> None:
        """Update display role hint from profiles. Authz is SpiceDB only."""
        bundle = load_persona_bundle(db, subject)
        admin = bundle.admin if bundle.admin is not None and bundle.admin.is_active else None
        if admin and emails_match(admin.email, clerk_email):
            user.role = admin_role_to_assignable(parse_admin_role(admin.role)).value
            activate_pending_user(user)
            if not admin.porterchain_user_id:
                admin.porterchain_user_id = user.id
            return

        active_merchants = sorted(
            bundle.active_merchant_users(),
            key=lambda row: row.created_at or datetime.min.replace(tzinfo=UTC),
        )
        mu = active_merchants[0] if active_merchants else None
        if mu and emails_match(mu.email, clerk_email):
            user.role = merchant_role_to_assignable(parse_merchant_role(mu.role)).value
            activate_pending_user(user)
            if not mu.porterchain_user_id:
                mu.porterchain_user_id = user.id
            return

        driver = bundle.driver
        if (
            driver
            and driver.status != DriverStatus.REJECTED.value
            and emails_match(driver.email, clerk_email)
        ):
            user.role = AssignableRole.DRIVER.value
            activate_pending_user(user)
            if not driver.porterchain_user_id:
                driver.porterchain_user_id = user.id
            return

        customer = bundle.customer
        if customer and emails_match(customer.email, clerk_email):
            user.role = AssignableRole.CUSTOMER.value
            activate_pending_user(user)
            # C-17: keep Customer → PorterchainUser FK in sync (authz / directory).
            if not getattr(customer, "porterchain_user_id", None):
                customer.porterchain_user_id = user.id

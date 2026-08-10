"""Merchant lifecycle admin per BUSINESS_WORKFLOW.md §2."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.clerk_directory_service import _clerk_linked
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.auth.clerk_registry import clerk_client_for_kind, is_clerk_secret_configured
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.team_service import (
    assert_not_last_owner,
    ensure_merchant_seat,
)
from porterchain_api.merchant_models import Merchant, MerchantUser


class AdminMerchantService:
    def list_merchants(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Merchant]:
        q = db.query(Merchant)
        if status:
            q = q.filter(Merchant.status == status)
        return q.order_by(Merchant.created_at.desc()).limit(limit).all()

    def get_merchant(self, db: Session, merchant_id: str) -> Merchant | None:
        return db.query(Merchant).filter(Merchant.id == merchant_id).first()

    def create_merchant(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        *,
        email: str,
        company_name: str,
        auto_activate: bool = True,
        send_invite: bool = True,
    ) -> Merchant:
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("merchant_owner_email_required")
        if not company_name.strip():
            raise ValueError("company_name_required")

        existing_merchant = db.query(Merchant).filter(Merchant.email == normalized).first()
        if existing_merchant:
            raise ValueError("merchant_email_exists")

        existing_user = db.query(MerchantUser).filter(MerchantUser.email == normalized).first()
        if existing_user:
            raise ValueError("merchant_user_email_exists")

        if send_invite and is_clerk_secret_configured(settings, "merchant"):
            clerk = clerk_client_for_kind(settings, "merchant")
            existing_clerk = clerk.find_user_by_email(normalized)
            if existing_clerk:
                clerk_id = str(existing_clerk["id"])
                linked = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_id).first()
                if linked:
                    raise ValueError("merchant_user_email_exists")

        merchant = Merchant(
            status=MerchantStatus.PENDING.value,
            company_name=company_name.strip(),
            email=normalized,
            payment_terms="NET_30",
        )
        db.add(merchant)
        db.flush()

        if send_invite and is_clerk_secret_configured(settings, "merchant"):
            clerk = clerk_client_for_kind(settings, "merchant")
            existing_clerk = clerk.find_user_by_email(normalized)
            if existing_clerk:
                clerk_id = str(existing_clerk["id"])
                db.add(
                    MerchantUser(
                        merchant_id=merchant.id,
                        clerk_user_id=clerk_id,
                        email=normalized,
                        role=MerchantRole.OWNER.value,
                        is_active=True,
                    )
                )
                merchant.status = MerchantStatus.ONBOARDING.value
                merchant.profile = {
                    **(merchant.profile or {}),
                    "source": "admin_register_portal_user",
                }
                clerk.update_user_metadata(
                    clerk_id,
                    {
                        "role": MerchantRole.OWNER.value,
                        "porterchain_role": MerchantRole.OWNER.value,
                        "user_type": "merchant",
                        "merchant_id": merchant.id,
                    },
                )
                self._audit(
                    db,
                    ctx,
                    "merchant.created",
                    "merchant",
                    merchant.id,
                    {"email": normalized, "clerk_linked": True, "via": "portal_clerk_user"},
                )
                db.commit()
                db.refresh(merchant)
            else:
                ensure_merchant_seat(
                    db,
                    merchant_id=merchant.id,
                    email=normalized,
                    role=MerchantRole.OWNER.value,
                    actor_user_id=ctx.user.id,
                    audit_action="merchant.owner_seat_added",
                    commit=False,
                )
                merchant.status = MerchantStatus.ONBOARDING.value
                self._audit(
                    db,
                    ctx,
                    "merchant.created",
                    "merchant",
                    merchant.id,
                    {"email": normalized, "clerk_linked": False, "via": "owner_seat"},
                )
                db.commit()
                db.refresh(merchant)
        else:
            ensure_merchant_seat(
                db,
                merchant_id=merchant.id,
                email=normalized,
                role=MerchantRole.OWNER.value,
                actor_user_id=ctx.user.id,
                audit_action="merchant.owner_seat_added",
                commit=False,
            )
            self._audit(
                db,
                ctx,
                "merchant.created",
                "merchant",
                merchant.id,
                {"email": normalized, "clerk_linked": False, "via": "owner_seat"},
            )
            db.commit()
            db.refresh(merchant)

        if auto_activate:
            try:
                merchant = self.complete_onboarding(
                    db, ctx, settings, merchant.id, email=normalized
                )
            except ValueError as exc:
                # Seat reserved but owner not Clerk-linked yet — stay ONBOARDING (M-11).
                if str(exc) != "owner_not_clerk_linked":
                    raise
                merchant = self._get_or_raise(db, merchant.id)

        return merchant

    def approve_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        merchant.status = MerchantStatus.ACTIVE.value
        merchant.activated_at = datetime.now(UTC)
        # M-20: CRM company "active_merchant" only once merchant is bookable.
        from porterchain_api.crm_models import CrmCompany
        from porterchain_api.domain.crm_states import CompanyMerchantStatus

        company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()
        if company:
            company.merchant_status = CompanyMerchantStatus.ACTIVE_MERCHANT.value
        self._audit(db, ctx, "merchant.approved", "merchant", merchant_id, {})
        emit_event(
            db,
            event_type=E.MERCHANT_APPROVED,
            aggregate_type="merchant",
            aggregate_id=merchant_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
        )
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    def suspend_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        merchant.status = MerchantStatus.SUSPENDED.value
        self._audit(db, ctx, "merchant.suspended", "merchant", merchant_id, {})
        emit_event(
            db,
            event_type=E.MERCHANT_SUSPENDED,
            aggregate_type="merchant",
            aggregate_id=merchant_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
        )
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    @staticmethod
    def _sync_authz_for_merchant_users(db: Session, merchant_id: str) -> None:
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation
        from porterchain_api.merchant_models import MerchantUser

        for mu in db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all():
            sync_authz_after_persona_mutation(db, mu.clerk_user_id)

    def invite_owner(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        merchant_id: str,
        *,
        email: str,
    ) -> MerchantUser:
        """Reserve owner seat by email (no Clerk invite). ``settings`` unused."""
        _ = settings
        merchant = self._get_or_raise(db, merchant_id)
        user = ensure_merchant_seat(
            db,
            merchant_id=merchant.id,
            email=email,
            role=MerchantRole.OWNER.value,
            actor_user_id=ctx.user.id,
            audit_action="merchant.owner_seat_added",
            commit=False,
        )
        self._audit(
            db,
            ctx,
            "merchant.owner_seat_added",
            "merchant",
            merchant.id,
            {"email": email.lower().strip()},
        )
        db.commit()
        db.refresh(user)
        return user

    def invite_team_member(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        merchant_id: str,
        *,
        email: str,
        role: str = MerchantRole.OPS.value,
    ) -> MerchantUser:
        """Reserve teammate seat by email (no Clerk invite). ``settings`` unused."""
        _ = settings
        merchant = self._get_or_raise(db, merchant_id)
        user = ensure_merchant_seat(
            db,
            merchant_id=merchant.id,
            email=email,
            role=role,
            actor_user_id=ctx.user.id,
            audit_action="merchant.member_seat_added",
            commit=False,
        )
        self._audit(
            db,
            ctx,
            "merchant.member_seat_added",
            "merchant",
            merchant.id,
            {"email": email.lower().strip(), "role": role},
        )
        db.commit()
        db.refresh(user)
        return user

    def activate_merchant_users(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        *,
        email: str | None = None,
    ) -> list[MerchantUser]:
        merchant = self._get_or_raise(db, merchant_id)
        q = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant.id)
        if email:
            q = q.filter(MerchantUser.email == email.lower().strip())
        users = q.all()
        if not users:
            raise LookupError("merchant_user_not_found")
        for user in users:
            user.is_active = True
        self._audit(
            db,
            ctx,
            "merchant.users_activated",
            "merchant",
            merchant_id,
            {"emails": [u.email for u in users]},
        )
        db.commit()
        for user in users:
            db.refresh(user)
        return users

    def complete_onboarding(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        merchant_id: str,
        *,
        email: str | None = None,
    ) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        target = (email or merchant.email or "").lower().strip()
        if not target:
            raise ValueError("merchant_owner_email_required")

        users = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all()
        owner = next((u for u in users if u.role == MerchantRole.OWNER.value), None)
        needs_seat = not owner or not _clerk_linked(owner.clerk_user_id)
        if needs_seat:
            self.invite_owner(db, ctx, settings, merchant_id, email=owner.email if owner else target)

        # Re-load owner after seat reserve — do not force ACTIVE without Clerk link (M-11).
        users = db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all()
        owner = next((u for u in users if u.role == MerchantRole.OWNER.value), None)
        owner_linked = bool(owner and _clerk_linked(owner.clerk_user_id))
        if not owner_linked:
            if merchant.status != MerchantStatus.ACTIVE.value:
                merchant.status = MerchantStatus.ONBOARDING.value
            for user in users:
                user.is_active = True
            self._audit(
                db,
                ctx,
                "merchant.onboarding_seat_reserved",
                "merchant",
                merchant_id,
                {"email": target, "owner_linked": False},
            )
            db.commit()
            db.refresh(merchant)
            raise ValueError("owner_not_clerk_linked")

        for user in users:
            user.is_active = True

        if merchant.status != MerchantStatus.ACTIVE.value:
            merchant.status = MerchantStatus.ACTIVE.value
            merchant.activated_at = datetime.now(UTC)
            self._audit(db, ctx, "merchant.approved", "merchant", merchant_id, {"via": "complete_onboarding"})
            emit_event(
                db,
                event_type=E.MERCHANT_APPROVED,
                aggregate_type="merchant",
                aggregate_id=merchant_id,
                actor_type="admin",
                actor_id=ctx.user.id,
                payload={"merchant_id": merchant_id, "company_name": merchant.company_name},
            )

        self._audit(
            db,
            ctx,
            "merchant.onboarding_completed",
            "merchant",
            merchant_id,
            {"email": target},
        )
        db.commit()
        db.refresh(merchant)
        return merchant

    def update_merchant_terms(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        *,
        payment_terms: str | None = None,
        pricing_config: dict | None = None,
        credit_limit_cents: int | None = None,
        parent_merchant_id: str | None = None,
        support_tier: str | None = None,
        billing_cycle: str | None = None,
        preferred_vehicles: list[str] | None = None,
        company_name: str | None = None,
        phone: str | None = None,
        hst_number: str | None = None,
        stripe_enabled: bool | None = None,
    ) -> Merchant:
        from porterchain_api.billing_engine.merchant_service import BILLING_CYCLES

        merchant = self._get_or_raise(db, merchant_id)
        if payment_terms:
            merchant.payment_terms = payment_terms
        if pricing_config is not None:
            merchant.pricing_config = pricing_config
        if credit_limit_cents is not None:
            merchant.credit_limit_cents = credit_limit_cents
        if parent_merchant_id is not None:
            if parent_merchant_id == merchant_id:
                raise ValueError("parent_cannot_be_self")
            if parent_merchant_id:
                parent = self.get_merchant(db, parent_merchant_id)
                if not parent:
                    raise ValueError("parent_merchant_not_found")
            merchant.parent_merchant_id = parent_merchant_id or None
        if support_tier is not None:
            profile = dict(merchant.profile or {})
            enterprise = dict(profile.get("enterprise") or {})
            enterprise["support_tier"] = support_tier
            profile["enterprise"] = enterprise
            merchant.profile = profile
        if billing_cycle is not None:
            cycle = billing_cycle.upper().strip()
            if cycle not in BILLING_CYCLES:
                raise ValueError("invalid_billing_cycle")
            merchant.billing_cycle = cycle
        if preferred_vehicles is not None:
            merchant.preferred_vehicles = self._validate_preferred_vehicles(db, preferred_vehicles)
        if company_name is not None:
            name = company_name.strip()
            if not name:
                raise ValueError("company_name_required")
            merchant.company_name = name
        if phone is not None:
            merchant.phone = phone.strip() or None
        if hst_number is not None:
            merchant.hst_number = hst_number.strip() or None
        if stripe_enabled is not None:
            profile = dict(merchant.profile or {})
            profile["stripe_enabled"] = bool(stripe_enabled)
            merchant.profile = profile
        self._audit(
            db,
            ctx,
            "merchant.terms_updated",
            "merchant",
            merchant_id,
            {
                "payment_terms": payment_terms,
                "parent_merchant_id": parent_merchant_id,
                "support_tier": support_tier,
                "billing_cycle": billing_cycle,
                "preferred_vehicles": preferred_vehicles,
                "stripe_enabled": stripe_enabled,
            },
        )
        db.commit()
        db.refresh(merchant)
        return merchant

    @staticmethod
    def _validate_preferred_vehicles(db: Session, preferred: list[str]) -> list[str]:
        """M-6: preferred vehicles must be ⊆ enabled retail catalog."""
        from porterchain_api.admin_engine.settings_service import AdminSettingsService

        catalog = AdminSettingsService().enabled_retail_vehicle_ids(db)
        cleaned: list[str] = []
        for raw in preferred:
            vid = str(raw or "").strip()
            if not vid:
                continue
            if catalog and vid not in catalog:
                raise ValueError(f"preferred_vehicle_not_in_catalog:{vid}")
            if vid not in cleaned:
                cleaned.append(vid)
        return cleaned

    def update_team_member_role(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        user_id: str,
        *,
        role: str,
    ) -> MerchantUser:
        """M-30: Admin parity for seat role changes."""
        if role not in {r.value for r in MerchantRole}:
            raise ValueError("invalid_team_role")
        self._get_or_raise(db, merchant_id)
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == merchant_id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        assert_not_last_owner(db, merchant_id=merchant_id, user=user, next_role=role)
        user.role = role
        self._audit(
            db,
            ctx,
            "merchant.team_role_updated",
            "merchant_user",
            user.id,
            {"email": user.email, "role": role},
        )
        db.commit()
        db.refresh(user)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, user.clerk_user_id)
        return user

    def remove_team_member(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        user_id: str,
    ) -> None:
        """M-30: Admin deactivate seat (last-owner protected)."""
        self._get_or_raise(db, merchant_id)
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.id == user_id, MerchantUser.merchant_id == merchant_id)
            .first()
        )
        if not user:
            raise LookupError("team_member_not_found")
        assert_not_last_owner(db, merchant_id=merchant_id, user=user, next_role=None)
        user.is_active = False
        self._audit(
            db,
            ctx,
            "merchant.team_removed",
            "merchant_user",
            user.id,
            {"email": user.email},
        )
        db.commit()
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, user.clerk_user_id)

    def list_subsidiaries(self, db: Session, parent_merchant_id: str) -> list[Merchant]:
        return (
            db.query(Merchant)
            .filter(Merchant.parent_merchant_id == parent_merchant_id)
            .order_by(Merchant.company_name.asc())
            .all()
        )

    def _get_or_raise(self, db: Session, merchant_id: str) -> Merchant:
        merchant = self.get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return merchant

    def _audit(
        self,
        db: Session,
        ctx: AdminContext,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: dict,
    ) -> None:
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=payload,
            )
        )

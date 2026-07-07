"""Merchant lifecycle admin per BUSINESS_WORKFLOW.md §2."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_engine.settings_service import _clerk_linked
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.auth.clerk_registry import clerk_client_for_kind, is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
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
                InvitationService().invite_merchant_owner(
                    db, ctx, settings, merchant, email=normalized, role=MerchantRole.OWNER.value
                )
                db.refresh(merchant)
        else:
            from porterchain_api.admin_engine.clerk_directory_service import fetch_clerk_snapshots

            snaps = fetch_clerk_snapshots(settings, "merchant", limit=500, query=normalized)
            snap = snaps.get(normalized)
            clerk_id = snap.clerk_user_id if snap else f"pending:{normalized}"
            db.add(
                MerchantUser(
                    merchant_id=merchant.id,
                    clerk_user_id=clerk_id,
                    email=normalized,
                    role=MerchantRole.OWNER.value,
                    is_active=True,
                )
            )
            self._audit(
                db,
                ctx,
                "merchant.created",
                "merchant",
                merchant.id,
                {"email": normalized, "clerk_linked": bool(snap)},
            )
            db.commit()
            db.refresh(merchant)

        if auto_activate:
            merchant = self.complete_onboarding(db, ctx, settings, merchant.id, email=normalized)

        return merchant

    def approve_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        merchant.status = MerchantStatus.ACTIVE.value
        merchant.activated_at = datetime.now(UTC)
        self._audit(db, ctx, "merchant.approved", "merchant", merchant_id, {})
        emit_event(
            db,
            event_type=E.MERCHANT_APPROVED,
            aggregate_type="merchant",
            aggregate_id=merchant_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(merchant)
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
        )
        db.commit()
        db.refresh(merchant)
        return merchant

    def invite_owner(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        merchant_id: str,
        *,
        email: str,
    ) -> MerchantUser:
        if not is_clerk_secret_configured(settings, "merchant"):
            raise ValueError("clerk_not_configured")
        merchant = self._get_or_raise(db, merchant_id)
        user, _inv = InvitationService().invite_merchant_owner(
            db, ctx, settings, merchant, email=email, role=MerchantRole.OWNER.value
        )
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
        if not is_clerk_secret_configured(settings, "merchant"):
            raise ValueError("clerk_not_configured")
        merchant = self._get_or_raise(db, merchant_id)
        user, _inv = InvitationService().invite_merchant_member_admin(
            db, ctx, settings, merchant, email=email, role=role
        )
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
        needs_invite = not owner or not _clerk_linked(owner.clerk_user_id)
        if needs_invite and is_clerk_secret_configured(settings, "merchant"):
            self.invite_owner(db, ctx, settings, merchant_id, email=owner.email if owner else target)

        for user in db.query(MerchantUser).filter(MerchantUser.merchant_id == merchant_id).all():
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
    ) -> Merchant:
        merchant = self._get_or_raise(db, merchant_id)
        if payment_terms:
            merchant.payment_terms = payment_terms
        if pricing_config is not None:
            merchant.pricing_config = pricing_config
        if credit_limit_cents is not None:
            merchant.credit_limit_cents = credit_limit_cents
        self._audit(db, ctx, "merchant.terms_updated", "merchant", merchant_id, {"payment_terms": payment_terms})
        db.commit()
        db.refresh(merchant)
        return merchant

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

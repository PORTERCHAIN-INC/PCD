"""Merchant lifecycle admin per BUSINESS_WORKFLOW.md §2."""

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog
from porterchain_api.auth.clerk_registry import (
    clerk_client_for_kind,
    is_clerk_secret_configured,
)
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.lifecycle import merge_profile, set_status
from porterchain_api.merchant_engine.lookups import (
    get_merchant as lookup_merchant,
)
from porterchain_api.merchant_engine.lookups import (
    get_merchant_by_email,
    get_merchant_user_by_email,
    get_seat,
    get_seat_by_clerk,
    seats_for_merchant,
)
from porterchain_api.merchant_engine.lookups import (
    list_merchants as lookup_list_merchants,
)
from porterchain_api.merchant_engine.lookups import (
    list_subsidiaries as lookup_subsidiaries,
)
from porterchain_api.merchant_engine.provision import create_onboarding_merchant
from porterchain_api.merchant_engine.team_service import (
    activate_seats,
    add_linked_seat,
    assert_not_last_owner,
    ensure_merchant_seat,
    update_seat,
)


class AdminMerchantService:
    def list_merchants(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Any]:
        return lookup_list_merchants(db, status=status, limit=limit)

    def get_merchant(self, db: Session, merchant_id: str) -> Any | None:
        return lookup_merchant(db, merchant_id)

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
        pricing_config: dict | None = None,
    ) -> Any:
        normalized = email.lower().strip()
        if not normalized:
            raise ValueError("merchant_owner_email_required")
        if not company_name.strip():
            raise ValueError("company_name_required")

        existing_merchant = get_merchant_by_email(db, normalized)
        if existing_merchant:
            raise ValueError("merchant_email_exists")

        existing_user = get_merchant_user_by_email(db, normalized)
        if existing_user:
            raise ValueError("merchant_user_email_exists")

        if send_invite and is_clerk_secret_configured(settings, "merchant"):
            clerk = clerk_client_for_kind(settings, "merchant")
            existing_clerk = clerk.find_user_by_email(normalized)
            if existing_clerk:
                clerk_id = str(existing_clerk["id"])
                linked = get_seat_by_clerk(db, clerk_id)
                if linked:
                    raise ValueError("merchant_user_email_exists")

        merchant = create_onboarding_merchant(
            db,
            company_name=company_name.strip(),
            email=normalized,
            status=MerchantStatus.PENDING.value,
            payment_terms="NET_30",
            pricing_config=dict(pricing_config or {}),
        )

        if send_invite and is_clerk_secret_configured(settings, "merchant"):
            clerk = clerk_client_for_kind(settings, "merchant")
            existing_clerk = clerk.find_user_by_email(normalized)
            if existing_clerk:
                clerk_id = str(existing_clerk["id"])
                add_linked_seat(
                    db,
                    merchant_id=merchant.id,
                    email=normalized,
                    clerk_user_id=clerk_id,
                    role=MerchantRole.OWNER.value,
                    is_active=True,
                )
                set_status(merchant, MerchantStatus.ONBOARDING.value)
                merge_profile(merchant, {"source": "admin_register_portal_user"})
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
                set_status(merchant, MerchantStatus.ONBOARDING.value)
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

    def approve_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Any:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            approve_merchant as approve_compose,
        )

        merchant = approve_compose(self, db, ctx, merchant_id)
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    def suspend_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Any:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            suspend_merchant as suspend_compose,
        )

        merchant = suspend_compose(self, db, ctx, merchant_id)
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    def unsuspend_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Any:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            unsuspend_merchant as unsuspend_compose,
        )

        merchant = unsuspend_compose(self, db, ctx, merchant_id)
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    def reopen_merchant(self, db: Session, ctx: AdminContext, merchant_id: str) -> Any:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            reopen_merchant as reopen_compose,
        )

        merchant = reopen_compose(self, db, ctx, merchant_id)
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    def close_merchant(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        *,
        reason: str,
    ) -> Any:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            close_merchant as close_merchant_compose,
        )

        merchant = close_merchant_compose(self, db, ctx, merchant_id, reason=reason)
        db.commit()
        db.refresh(merchant)
        self._sync_authz_for_merchant_users(db, merchant_id)
        return merchant

    def convert_to_customer(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        *,
        owner_email: str | None = None,
        write_off_ar: bool = False,
    ) -> dict:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            convert_to_customer as convert_compose,
        )

        result = convert_compose(
            self, db, ctx, merchant_id, owner_email_value=owner_email, write_off_ar=write_off_ar
        )
        if result.get("skip_commit"):
            return {
                "customer_id": result["customer_id"],
                "merchant_id": result["merchant_id"],
                "status": result["status"],
            }
        db.commit()
        db.refresh(result["merchant"])
        db.refresh(result["customer"])
        self._sync_authz_for_merchant_users(db, merchant_id)
        return {
            "customer_id": result["customer_id"],
            "merchant_id": result["merchant_id"],
            "status": result["status"],
            "ar_written_off_cents": result["ar_written_off_cents"],
        }

    def update_team_member(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        user_id: str,
        *,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> Any:
        self._get_or_raise(db, merchant_id)
        user = get_seat(db, user_id, merchant_id=merchant_id)
        if not user:
            raise LookupError("team_member_not_found")
        if role is None and is_active is None:
            raise ValueError("nothing_to_update")
        if role is not None:
            if role not in {r.value for r in MerchantRole}:
                raise ValueError("invalid_team_role")
            assert_not_last_owner(db, merchant_id=merchant_id, user=user, next_role=role)
        if is_active is not None and is_active is False:
            assert_not_last_owner(db, merchant_id=merchant_id, user=user, next_role=None)
        update_seat(db, user, role=role, is_active=is_active)
        self._audit(
            db,
            ctx,
            "merchant.team_updated",
            "merchant_user",
            user.id,
            {"email": user.email, "role": user.role, "is_active": user.is_active},
        )
        db.commit()
        db.refresh(user)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, user.clerk_user_id)
        return user

    @staticmethod
    def _sync_authz_for_merchant_users(db: Session, merchant_id: str) -> None:
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        for mu in seats_for_merchant(db, merchant_id):
            sync_authz_after_persona_mutation(db, mu.clerk_user_id)

    def invite_owner(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        merchant_id: str,
        *,
        email: str,
    ) -> Any:
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
    ) -> Any:
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
    ) -> list[Any]:
        merchant = self._get_or_raise(db, merchant_id)
        users = seats_for_merchant(db, merchant.id, email=email)
        if not users:
            raise LookupError("merchant_user_not_found")
        activate_seats(users)
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
    ) -> Any:
        from porterchain_api.admin_engine.merchant_lifecycle import (
            complete_onboarding as complete_compose,
        )

        merchant, err = complete_compose(self, db, ctx, settings, merchant_id, email=email)
        db.commit()
        db.refresh(merchant)
        if err:
            raise ValueError(err)
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
        **kwargs: Any,
    ) -> Any:
        from porterchain_api.admin_engine.merchant_org import apply_merchant_terms

        merchant = apply_merchant_terms(
            db,
            ctx,
            merchant_id,
            svc=self,
            payment_terms=payment_terms,
            pricing_config=pricing_config,
            credit_limit_cents=credit_limit_cents,
            parent_merchant_id=parent_merchant_id,
            support_tier=support_tier,
            **kwargs,
        )
        db.commit()
        db.refresh(merchant)
        return merchant

    @staticmethod
    def _validate_preferred_vehicles(db: Session, preferred: list[str]) -> list[str]:
        from porterchain_api.admin_engine.merchant_org import (
            validate_preferred_vehicles,
        )

        return validate_preferred_vehicles(db, preferred)

    def remove_team_member(
        self,
        db: Session,
        ctx: AdminContext,
        merchant_id: str,
        user_id: str,
    ) -> None:
        """M-30: Admin deactivate seat (last-owner protected)."""
        self._get_or_raise(db, merchant_id)
        user = get_seat(db, user_id, merchant_id=merchant_id)
        if not user:
            raise LookupError("team_member_not_found")
        assert_not_last_owner(db, merchant_id=merchant_id, user=user, next_role=None)
        update_seat(db, user, is_active=False)
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

    def list_subsidiaries(self, db: Session, parent_merchant_id: str) -> list[Any]:
        return lookup_subsidiaries(db, parent_merchant_id)

    def _get_or_raise(self, db: Session, merchant_id: str) -> Any:
        merchant = self.get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return merchant

    def list_ops_invoices(self, db: Session, merchant_id: str):
        """Ops AR invoices for this merchant — not CRM sales invoices."""
        from porterchain_api.admin_engine.merchant_lifecycle import ops_invoices

        merchant = self.get_merchant(db, merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return ops_invoices(db, merchant)

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

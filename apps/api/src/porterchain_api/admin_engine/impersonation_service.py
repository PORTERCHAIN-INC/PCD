"""Super Admin audited impersonation — start / stop / resolve target rows."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Driver
from porterchain_api.auth.impersonation_session import (
    DEFAULT_TTL_SECONDS,
    ImpersonationSession,
    TargetType,
    bearer_token_for_session,
    create_session,
    get_session,
    revoke_session,
)
from porterchain_api.booking_models import Customer
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole, DriverStatus
from porterchain_api.merchant_engine.lookups import get_merchant, get_merchant_user


def _clerk_linked(clerk_user_id: str | None) -> bool:
    if not clerk_user_id:
        return False
    s = str(clerk_user_id)
    return not (s.startswith("pending:") or s.startswith("staff:") or s.startswith("impersonation:"))


class ImpersonationService:
    def start(
        self,
        db: Session,
        ctx: AdminContext,
        settings: Settings,
        *,
        target_type: TargetType,
        target_id: str,
        reason: str,
        staff_session_id: str = "",
    ) -> dict[str, Any]:
        if ctx.role != AdminRole.SUPER_ADMIN:
            raise PermissionError("impersonation_super_admin_only")

        target = self._resolve_target(db, target_type, target_id)
        session = create_session(
            actor_admin_id=ctx.user.id,
            actor_email=ctx.user.email,
            actor_role=ctx.role.value,
            target_type=target_type,
            target_id=target["id"],
            target_email=target["email"],
            reason=reason,
            staff_session_id=staff_session_id,
            target_clerk_user_id=target.get("clerk_user_id"),
            target_label=target.get("label") or target["email"],
            ttl_seconds=DEFAULT_TTL_SECONDS,
        )
        if session is None:
            raise ValueError("impersonation_redis_unavailable")

        log_admin_audit(
            db,
            ctx,
            action="impersonation.started",
            resource_type=target_type,
            resource_id=target["id"],
            payload={
                "session_id": session.session_id,
                "target_email": target["email"],
                "reason": session.reason,
                "expires_at": session.expires_at,
            },
        )
        db.commit()
        return self._response(session, settings)

    def stop(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        session_id: str,
    ) -> dict[str, Any]:
        session = get_session(session_id)
        if session is None:
            raise LookupError("impersonation_not_found")
        if session.actor_admin_id != ctx.user.id and ctx.role != AdminRole.SUPER_ADMIN:
            raise PermissionError("impersonation_stop_forbidden")
        revoke_session(session_id)
        log_admin_audit(
            db,
            ctx,
            action="impersonation.stopped",
            resource_type=session.target_type,
            resource_id=session.target_id,
            payload={
                "session_id": session_id,
                "target_email": session.target_email,
                "reason": session.reason,
            },
        )
        db.commit()
        return {"ok": True, "session_id": session_id}

    def status(self, session_id: str) -> dict[str, Any] | None:
        session = get_session(session_id)
        if not session:
            return None
        return session.public_dict()

    def _resolve_target(self, db: Session, target_type: TargetType, target_id: str) -> dict[str, Any]:
        if not target_id or target_id.startswith("clerk:"):
            raise ValueError("impersonation_target_not_provisioned")

        if target_type == "driver":
            driver = db.get(Driver, target_id)
            if not driver:
                raise LookupError("driver_not_found")
            if driver.status == DriverStatus.SUSPENDED.value:
                raise ValueError("driver_suspended")
            return {
                "id": driver.id,
                "email": driver.email,
                "label": driver.full_name or driver.email,
                "clerk_user_id": driver.clerk_user_id if _clerk_linked(driver.clerk_user_id) else None,
            }

        if target_type == "merchant":
            mu = get_merchant_user(db, target_id)
            if not mu:
                raise LookupError("merchant_user_not_found")
            if not mu.is_active:
                raise ValueError("merchant_user_inactive")
            merchant = get_merchant(db, mu.merchant_id)
            if not merchant:
                raise LookupError("merchant_not_found")
            return {
                "id": mu.id,
                "email": mu.email,
                "label": f"{merchant.company_name or merchant.email} · {mu.email}",
                "clerk_user_id": mu.clerk_user_id if _clerk_linked(mu.clerk_user_id) else None,
                "merchant_id": merchant.id,
            }

        if target_type == "customer":
            customer = db.get(Customer, target_id)
            if not customer:
                raise LookupError("customer_not_found")
            if not (customer.email or "").strip():
                raise ValueError("customer_email_required")
            return {
                "id": customer.id,
                "email": customer.email,
                "label": customer.full_name or customer.email,
                "clerk_user_id": customer.clerk_user_id
                if _clerk_linked(customer.clerk_user_id)
                else None,
            }

        raise ValueError("invalid_impersonation_target_type")

    def _response(self, session: ImpersonationSession, settings: Settings) -> dict[str, Any]:
        portal = {
            "driver": settings.driver_portal_url,
            "merchant": settings.merchant_portal_url,
            "customer": settings.customer_portal_url,
        }[session.target_type].rstrip("/")
        bearer = bearer_token_for_session(session.session_id)
        return {
            **session.public_dict(),
            "bearer_token": bearer,
            "portal_bootstrap_url": f"{portal}/impersonate?token={bearer}",
        }

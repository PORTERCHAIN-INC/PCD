"""Merchant orders — merchant-scoped wrapper over OrderPlatformService (masterrule §3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.order_engine import (
    ASSIGNED_STATES,
    DONE_STATES,
    FAILED_STATES,
    IN_FLIGHT,
    PICKED_UP_STATES,
    RETURNED_STATES,
    WAITING_DISPATCH,
    OrderFilters,
)
from porterchain_api.order_engine.platform_service import OrderPlatformService
from porterchain_api.admin_models import Claim, SupportTicket
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog
from porterchain_api.models import Order, OrderEvent


@dataclass
class MerchantOrderFilters:
    state: str | None = None
    payment_status: str | None = None
    invoice_status: str | None = None
    driver_id: str | None = None
    priority: str | None = None
    service_type: str | None = None
    city: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    search: str | None = None
    limit: int = 500
    offset: int = 0


class MerchantOrdersService:
    def __init__(self) -> None:
        from porterchain_api.booking_engine.repositories.order_repository import OrderRepository

        self._orders = OrderPlatformService()
        self._booking = MerchantBookingService()
        self._order_repo = OrderRepository()

    def _require_owned(self, db: Session, ctx: MerchantContext, order_id: str) -> Order:
        order = self._order_repo.get_for_merchant(db, ctx.merchant.id, order_id)
        if not order:
            raise LookupError("order_not_found")
        return order

    def _to_order_filters(self, ctx: MerchantContext, filters: MerchantOrderFilters) -> OrderFilters:
        return OrderFilters(
            state=filters.state,
            payment_status=filters.payment_status,
            invoice_status=filters.invoice_status,
            merchant_id=ctx.merchant.id,
            driver_id=filters.driver_id,
            priority=filters.priority,
            service_type=filters.service_type,
            city=filters.city,
            date_from=filters.date_from,
            date_to=filters.date_to,
            amount_min_cents=filters.amount_min_cents,
            amount_max_cents=filters.amount_max_cents,
            search=filters.search,
            limit=filters.limit,
            offset=filters.offset,
        )

    def list_enriched(self, db: Session, ctx: MerchantContext, filters: MerchantOrderFilters) -> list[dict[str, Any]]:
        return self._orders.list_enriched(db, self._to_order_filters(ctx, filters))

    def orders_dashboard(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        merchant_id = ctx.merchant.id
        now = datetime.now(UTC).replace(tzinfo=None)
        sod = datetime.combine(now.date(), time.min)

        def count(states: tuple[str, ...]) -> int:
            return (
                db.query(func.count(Order.id))
                .filter(Order.merchant_id == merchant_id, Order.state.in_(states))
                .scalar()
                or 0
            )

        delivered_today = (
            db.query(func.count(Order.id))
            .filter(
                Order.merchant_id == merchant_id,
                Order.state.in_(DONE_STATES),
                Order.updated_at >= sod,
            )
            .scalar()
            or 0
        )
        open_claims = (
            db.query(func.count(Claim.id))
            .join(Order, Claim.order_id == Order.id)
            .filter(Order.merchant_id == merchant_id, Claim.status.in_(("open", "investigating")))
            .scalar()
            or 0
        )
        open_tickets = (
            db.query(func.count(SupportTicket.id))
            .filter(
                SupportTicket.merchant_id == merchant_id,
                SupportTicket.status.in_(("open", "in_progress", "escalated")),
            )
            .scalar()
            or 0
        )
        revenue_today = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.merchant_id == merchant_id,
                Order.created_at >= sod,
                Order.state.notin_((OrderState.CANCELLED.value,)),
            )
            .scalar()
            or 0
        )

        return {
            "orders_today": (
                db.query(func.count(Order.id))
                .filter(Order.merchant_id == merchant_id, Order.created_at >= sod)
                .scalar()
                or 0
            ),
            "orders_in_progress": count(IN_FLIGHT),
            "waiting_dispatch": count(WAITING_DISPATCH),
            "assigned": count(ASSIGNED_STATES),
            "picked_up": count(PICKED_UP_STATES),
            "delivered": int(delivered_today),
            "failed": count(FAILED_STATES),
            "returned": count(RETURNED_STATES),
            "claims": int(open_claims),
            "open_support_tickets": int(open_tickets),
            "revenue_today_cents": int(revenue_today),
            "avg_delivery_hours": self._orders._avg_duration_hours(db, "order.picked_up", "order.delivered"),
            "avg_pickup_hours": self._orders._avg_duration_hours(db, "order.driver_assigned", "order.picked_up"),
            "avg_sla_percent": 100.0,
        }

    def get_detail_360(self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str) -> dict[str, Any]:
        self._require_owned(db, ctx, order_id)
        detail = self._orders.get_detail_360(db, settings, order_id)
        if not detail:
            raise LookupError("order_not_found")
        return self._sanitize_merchant_detail(db, ctx, order_id, detail)

    def order_tracking(self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str) -> dict[str, Any]:
        from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService

        return MerchantTrackingService().live_tracking(db, settings, ctx, order_id)

    def bulk_action(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        order_ids: list[str],
        action: str,
    ) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for oid in order_ids:
            try:
                order = self._require_owned(db, ctx, oid)
                if action == "cancel":
                    self._booking.cancel_order(db, ctx, order, settings)
                    results.append({"order_id": oid, "status": "cancelled"})
                elif action == "duplicate":
                    self._booking.duplicate_order(db, settings, ctx, order)
                    results.append({"order_id": oid, "status": "duplicated"})
                else:
                    results.append({"order_id": oid, "status": "unsupported"})
            except Exception as exc:
                results.append({"order_id": oid, "status": f"error:{exc}"})
        return results

    def _sanitize_merchant_detail(
        self,
        db: Session,
        ctx: MerchantContext,
        order_id: str,
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        detail.pop("internal_notes", None)
        detail.pop("audit_log", None)
        detail.pop("fraud_risk_score", None)
        smart = detail.get("smart") or {}
        if isinstance(smart, dict):
            smart.pop("fraud_risk_score", None)
            detail["smart"] = smart

        merchant_audit = (
            db.query(MerchantAuditLog)
            .filter(
                MerchantAuditLog.merchant_id == ctx.merchant.id,
                MerchantAuditLog.resource_type == "order",
                MerchantAuditLog.resource_id == order_id,
            )
            .order_by(MerchantAuditLog.created_at.asc())
            .all()
        )
        detail["merchant_activity"] = [
            {
                "action": row.action,
                "occurred_at": row.created_at,
                "payload": row.payload,
            }
            for row in merchant_audit
        ]
        return detail

    # Legacy helpers (programmatic API + simple consumers)
    def list_orders(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        state: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        q = db.query(Order).filter(Order.merchant_id == ctx.merchant.id)
        if state:
            q = q.filter(Order.state == state)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (Order.tracking_number.ilike(pattern))
                | (Order.order_number.ilike(pattern))
                | (Order.internal_reference.ilike(pattern))
                | (Order.purchase_order_number.ilike(pattern))
            )
        return q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    def get_order(self, db: Session, ctx: MerchantContext, order_id: str) -> Order | None:
        return self._order_repo.get_for_merchant(db, ctx.merchant.id, order_id)

    def get_tracking_timeline(self, db: Session, ctx: MerchantContext, order_id: str) -> list[dict]:
        order = self.get_order(db, ctx, order_id)
        if not order:
            raise LookupError("order_not_found")
        events = (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )
        return [
            {
                "event_type": e.event_type,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "payload": e.payload,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ]

    def get_by_tracking(self, db: Session, ctx: MerchantContext, tracking_number: str) -> Order | None:
        return self._order_repo.get_by_tracking_for_merchant(db, ctx.merchant.id, tracking_number)

    def compliance_dossier_pdf(
        self, db: Session, ctx: MerchantContext, order_id: str
    ) -> tuple[bytes, str]:
        """§8.1.13 — merchant-scoped compliance PDF dossier."""
        from porterchain_api.admin_models import Driver
        from porterchain_api.reporting.compliance_dossier import build_compliance_dossier_pdf

        order = self._require_owned(db, ctx, order_id)
        events = self._orders.order_timeline(db, order_id)
        driver = None
        if order.assigned_driver_id:
            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
        pdf = build_compliance_dossier_pdf(order, events, merchant=ctx.merchant, driver=driver)
        return pdf, f"compliance-{order.order_number}.pdf"

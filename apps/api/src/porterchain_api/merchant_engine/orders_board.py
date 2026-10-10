"""Merchant order board — dashboard counts, 360 sanitize, bulk, timeline."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.domain.states import OrderState
from porterchain_api.merchant_engine.cancel_policy import (
    bulk_exception_message,
    cancel_allowed,
    cancel_error_message,
    cancel_rule,
)
from porterchain_api.merchant_engine.consignee_notify import consignee_email_from_order
from porterchain_api.merchant_engine.quote_snapshot import sanitize_pricing_breakdown
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import MerchantAuditLog


def dashboard_payload(
    db: Session,
    merchant_id: str,
    *,
    open_claims: int,
    open_tickets: int,
    avg_delivery_hours: float | None,
    avg_pickup_hours: float | None,
    in_flight: tuple[str, ...],
    waiting_dispatch: tuple[str, ...],
    assigned: tuple[str, ...],
    picked_up: tuple[str, ...],
    failed: tuple[str, ...],
    returned: tuple[str, ...],
    done_states: tuple[str, ...],
) -> dict[str, Any]:
    now = datetime.now(UTC).replace(tzinfo=None)
    sod = datetime.combine(now.date(), time.min)

    def count(states: tuple[str, ...]) -> int:
        return (
            db.query(func.count(Order.id))
            .filter(
                Order.merchant_id == merchant_id,
                Order.is_sandbox.is_(False),
                Order.state.in_(states),
            )
            .scalar()
            or 0
        )

    delivered_today = (
        db.query(func.count(Order.id))
        .filter(
            Order.merchant_id == merchant_id,
            Order.is_sandbox.is_(False),
            Order.state.in_(done_states),
            Order.updated_at >= sod,
        )
        .scalar()
        or 0
    )
    revenue_today = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(
            Order.merchant_id == merchant_id,
            Order.is_sandbox.is_(False),
            Order.created_at >= sod,
            Order.state.notin_((OrderState.CANCELLED.value,)),
        )
        .scalar()
        or 0
    )
    return {
        "orders_today": (
            db.query(func.count(Order.id))
            .filter(
                Order.merchant_id == merchant_id,
                Order.is_sandbox.is_(False),
                Order.created_at >= sod,
            )
            .scalar()
            or 0
        ),
        "orders_in_progress": count(in_flight),
        "waiting_dispatch": count(waiting_dispatch),
        "assigned": count(assigned),
        "picked_up": count(picked_up),
        "delivered": int(delivered_today),
        "failed": count(failed),
        "returned": count(returned),
        "claims": int(open_claims),
        "open_support_tickets": int(open_tickets),
        "revenue_today_cents": int(revenue_today),
        "avg_delivery_hours": avg_delivery_hours,
        "avg_pickup_hours": avg_pickup_hours,
        "avg_sla_percent": 0.0,
    }


def sanitize_merchant_detail(
    db: Session,
    ctx: MerchantContext,
    order: Order,
    order_id: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    detail.pop("internal_notes", None)
    detail.pop("audit_log", None)
    detail.pop("fraud_risk_score", None)
    detail.pop("smart", None)

    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    snap = meta.get("quote") if isinstance(meta.get("quote"), dict) else {}
    breakdown = sanitize_pricing_breakdown(detail.get("pricing_breakdown"))
    if not breakdown and snap:
        breakdown = sanitize_pricing_breakdown(
            {
                **snap,
                "items": snap.get("line_items"),
                "final_cents": snap.get("amount_cents"),
            }
        )
    detail["pricing_breakdown"] = breakdown
    if detail.get("quote_amount_cents") is None:
        detail["quote_amount_cents"] = snap.get("amount_cents")
    if not detail.get("vehicle_class"):
        detail["vehicle_class"] = meta.get("vehicle_class")
    if not detail.get("package_type"):
        detail["package_type"] = meta.get("package_type")
    detail["consignee_email"] = consignee_email_from_order(order)
    detail["cancel_allowed"] = cancel_allowed(order.state)
    detail["cancel_rule"] = cancel_rule(order.state)

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


def bulk_action(svc: Any, db: Session, settings: Any, ctx: MerchantContext, order_ids: list[str], action: str) -> list[dict[str, str | bool]]:
    results: list[dict[str, str | bool]] = []
    for oid in order_ids:
        tracking = ""
        try:
            order = svc._require_owned(db, ctx, oid)
            tracking = order.tracking_number or ""
            if action == "cancel":
                svc._booking.cancel_order(db, ctx, order, settings)
                results.append(
                    {
                        "order_id": oid,
                        "tracking_number": order.tracking_number,
                        "ok": True,
                        "status": "cancelled",
                        "message": "Cancelled.",
                    }
                )
            elif action == "duplicate":
                svc._booking.duplicate_order(db, settings, ctx, order)
                results.append(
                    {
                        "order_id": oid,
                        "tracking_number": order.tracking_number,
                        "ok": True,
                        "status": "duplicated",
                        "message": "Duplicated.",
                    }
                )
            else:
                results.append(
                    {
                        "order_id": oid,
                        "tracking_number": order.tracking_number,
                        "ok": False,
                        "status": "unsupported",
                        "message": cancel_error_message("unsupported"),
                    }
                )
        except Exception as exc:
            results.append(
                {
                    "order_id": oid,
                    "tracking_number": tracking,
                    "ok": False,
                    "status": "failed",
                    "message": bulk_exception_message(exc),
                }
            )
    return results


def tracking_timeline(db: Session, order_id: str) -> list[dict]:
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

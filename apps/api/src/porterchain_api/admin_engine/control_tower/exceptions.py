"""Exception center — acknowledge / resolve / retry dispatch (+ Shopify ingress)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.booking_models import Customer, Order, OrderException
from porterchain_api.merchant_models import ShopifyIngressDlq
from porterchain_shared.events.catalog import DomainEventType

from porterchain_api.admin_engine.control_tower._helpers import now_utc, transition_path

SHOPIFY_DLQ_PREFIX = "shopify-dlq:"
SHOPIFY_FULFILL_PREFIX = "shopify-fulfill:"


class ExceptionsMixin:
    def exceptions(self, db: Session, *, limit: int = 100) -> list[dict]:
        merchants = self._merchant_names(db)
        rows = (
            db.query(OrderException, Order)
            .join(Order, Order.id == OrderException.order_id)
            .filter(OrderException.status.in_(["open", "acknowledged"]))
            .order_by(OrderException.created_at.asc())
            .limit(limit)
            .all()
        )
        customer_ids = {o.customer_id for _, o in rows if o.customer_id}
        emails = (
            dict(db.query(Customer.id, Customer.email).filter(Customer.id.in_(customer_ids)).all())
            if customer_ids
            else {}
        )
        items = [self._exception_dict(e, o, merchants, emails) for e, o in rows]
        remaining = max(0, limit - len(items))
        if remaining:
            items.extend(self._shopify_ingress_exceptions(db, merchants, limit=remaining))
        remaining = max(0, limit - len(items))
        if remaining:
            items.extend(self._shopify_fulfillment_exceptions(db, merchants, limit=remaining))
        items.sort(key=lambda r: r.get("created_at") or "")
        return items[:limit]

    def _shopify_ingress_exceptions(
        self, db: Session, merchants: dict[str, str], *, limit: int
    ) -> list[dict]:
        rows = (
            db.query(ShopifyIngressDlq)
            .filter(ShopifyIngressDlq.status.in_(("open", "held")))
            .order_by(ShopifyIngressDlq.created_at.asc())
            .limit(limit)
            .all()
        )
        out: list[dict] = []
        for row in rows:
            out.append(
                {
                    "id": f"{SHOPIFY_DLQ_PREFIX}{row.id}",
                    "type": f"shopify.ingress.{row.reason_code}",
                    "status": "open" if row.status == "open" else "acknowledged",
                    "order_id": row.porterchain_order_id or "",
                    "order_state": None,
                    "tracking_number": row.shopify_order_id or row.shop_domain,
                    "merchant": merchants.get(row.merchant_id),
                    "merchant_id": row.merchant_id,
                    "customer_email": None,
                    "reported_by": "shopify",
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "acknowledged_at": None,
                    "acknowledged_by": None,
                    "resolution_note": row.detail,
                    "resolved_at": None,
                    "source": "shopify_ingress",
                    "dlq_id": row.id,
                    "shop_domain": row.shop_domain,
                    "reason_code": row.reason_code,
                }
            )
        return out

    def _shopify_fulfillment_exceptions(
        self, db: Session, merchants: dict[str, str], *, limit: int
    ) -> list[dict]:
        candidates = (
            db.query(Order)
            .filter(
                Order.is_sandbox.is_(False),
                Order.order_source == OrderSource.SHOPIFY.value,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .order_by(Order.updated_at.desc())
            .limit(min(200, max(limit * 4, 40)))
            .all()
        )
        out: list[dict] = []
        for order in candidates:
            meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
            shopify = meta.get("shopify") if isinstance(meta.get("shopify"), dict) else {}
            err = shopify.get("last_fulfillment_error")
            if not err:
                continue
            out.append(
                {
                    "id": f"{SHOPIFY_FULFILL_PREFIX}{order.id}",
                    "type": f"shopify.fulfillment.{err}",
                    "status": "open",
                    "order_id": order.id,
                    "order_state": order.state,
                    "tracking_number": order.tracking_number,
                    "merchant": merchants.get(order.merchant_id) if order.merchant_id else None,
                    "merchant_id": order.merchant_id,
                    "customer_email": None,
                    "reported_by": "shopify",
                    "created_at": shopify.get("last_fulfillment_error_at")
                    or (order.updated_at.isoformat() if order.updated_at else None),
                    "acknowledged_at": None,
                    "acknowledged_by": None,
                    "resolution_note": str(err),
                    "resolved_at": None,
                    "source": "shopify_fulfillment",
                    "shop_domain": shopify.get("shop_domain"),
                    "reason_code": str(err),
                }
            )
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def _exception_dict(
        e: OrderException,
        o: Order,
        merchants: dict[str, str],
        customer_emails: dict[str, str] | None = None,
    ) -> dict:
        res = e.resolution or {}
        return {
            "id": e.id,
            "type": e.type,
            "status": e.status,
            "order_id": e.order_id,
            "order_state": o.state,
            "tracking_number": o.tracking_number,
            "merchant": merchants.get(o.merchant_id) if o.merchant_id else None,
            "merchant_id": o.merchant_id,
            "customer_email": (customer_emails or {}).get(o.customer_id) if o.customer_id else None,
            "reported_by": e.reported_by_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "acknowledged_at": res.get("acknowledged_at"),
            "acknowledged_by": res.get("acknowledged_by"),
            "resolution_note": res.get("note"),
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
            "source": "order_exception",
        }

    def acknowledge_exception(self, db: Session, ctx: AdminContext, exception_id: str) -> dict:
        if exception_id.startswith(SHOPIFY_DLQ_PREFIX):
            return self._ack_shopify_dlq(db, ctx, exception_id[len(SHOPIFY_DLQ_PREFIX) :])
        if exception_id.startswith(SHOPIFY_FULFILL_PREFIX):
            raise ValueError("shopify_fulfillment_ack_use_repush")
        e = db.get(OrderException, exception_id)
        if not e:
            raise LookupError("exception_not_found")
        if e.status == "resolved":
            raise ValueError("already_resolved")
        if e.status != "acknowledged":
            res = dict(e.resolution or {})
            res["acknowledged_at"] = now_utc().isoformat()
            res["acknowledged_by"] = ctx.user.email or ctx.user.id
            e.resolution = res
            e.status = "acknowledged"
            db.commit()
        return self._exception_dict(e, e.order, self._merchant_names(db))

    def _ack_shopify_dlq(self, db: Session, ctx: AdminContext, dlq_id: str) -> dict:
        row = db.get(ShopifyIngressDlq, dlq_id)
        if not row:
            raise LookupError("exception_not_found")
        if row.status == "resolved":
            raise ValueError("already_resolved")
        merchants = self._merchant_names(db)
        return {
            "id": f"{SHOPIFY_DLQ_PREFIX}{row.id}",
            "type": f"shopify.ingress.{row.reason_code}",
            "status": "acknowledged",
            "order_id": row.porterchain_order_id or "",
            "tracking_number": row.shopify_order_id or row.shop_domain,
            "merchant": merchants.get(row.merchant_id),
            "merchant_id": row.merchant_id,
            "reported_by": "shopify",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "acknowledged_at": now_utc().isoformat(),
            "acknowledged_by": ctx.user.email or ctx.user.id,
            "source": "shopify_ingress",
            "dlq_id": row.id,
            "shop_domain": row.shop_domain,
            "reason_code": row.reason_code,
        }

    def resolve_exception(
        self,
        db: Session,
        ctx: AdminContext,
        exception_id: str,
        *,
        note: str | None = None,
        action: str | None = None,
    ) -> dict:
        if exception_id.startswith(SHOPIFY_DLQ_PREFIX):
            return self._resolve_shopify_dlq(
                db, ctx, exception_id[len(SHOPIFY_DLQ_PREFIX) :], note=note
            )
        if exception_id.startswith(SHOPIFY_FULFILL_PREFIX):
            return self._resolve_shopify_fulfill(
                db, ctx, exception_id[len(SHOPIFY_FULFILL_PREFIX) :], note=note
            )
        e = db.get(OrderException, exception_id)
        if not e:
            raise LookupError("exception_not_found")
        if e.status == "resolved":
            raise ValueError("already_resolved")
        res = dict(e.resolution or {})
        res["resolved_by"] = ctx.user.email or ctx.user.id
        if note:
            res["note"] = note
        if action:
            res["action"] = action
        e.resolution = res
        e.status = "resolved"
        e.resolved_at = now_utc()
        order = e.order
        emit_event(
            db,
            event_type=DomainEventType.EXCEPTION_RESOLVED,
            aggregate_type="order",
            aggregate_id=e.order_id,
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={
                "exception_id": e.id,
                "exception_type": e.type,
                "order_id": e.order_id,
                "order_number": order.order_number if order else None,
                "tracking_number": order.tracking_number if order else None,
                "customer_id": order.customer_id if order else None,
                "merchant_id": order.merchant_id if order else None,
                "message": note or "Exception resolved",
            },
        )
        db.commit()
        return self._exception_dict(e, e.order, self._merchant_names(db))

    def _resolve_shopify_dlq(
        self, db: Session, ctx: AdminContext, dlq_id: str, *, note: str | None
    ) -> dict:
        from porterchain_api.merchant_engine.shopify_ingress_dlq import mark_dlq_resolved

        row = db.get(ShopifyIngressDlq, dlq_id)
        if not row:
            raise LookupError("exception_not_found")
        if row.status == "resolved":
            raise ValueError("already_resolved")
        mark_dlq_resolved(db, row, admin_id=ctx.user.id)
        merchants = self._merchant_names(db)
        return {
            "id": f"{SHOPIFY_DLQ_PREFIX}{row.id}",
            "type": f"shopify.ingress.{row.reason_code}",
            "status": "resolved",
            "order_id": row.porterchain_order_id or "",
            "tracking_number": row.shopify_order_id or row.shop_domain,
            "merchant": merchants.get(row.merchant_id),
            "merchant_id": row.merchant_id,
            "reported_by": "shopify",
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "resolution_note": note,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "source": "shopify_ingress",
            "dlq_id": row.id,
        }

    def _resolve_shopify_fulfill(
        self, db: Session, ctx: AdminContext, order_id: str, *, note: str | None
    ) -> dict:
        order = db.get(Order, order_id)
        if not order:
            raise LookupError("exception_not_found")
        extra = dict(order.compliance_metadata or {})
        shopify_meta = dict(extra.get("shopify") or {})
        err = shopify_meta.pop("last_fulfillment_error", None)
        shopify_meta.pop("last_fulfillment_error_at", None)
        shopify_meta["fulfillment_error_cleared_at"] = now_utc().isoformat()
        if note:
            shopify_meta["fulfillment_error_cleared_note"] = note[:500]
        extra["shopify"] = shopify_meta
        order.compliance_metadata = extra
        db.commit()
        merchants = self._merchant_names(db)
        return {
            "id": f"{SHOPIFY_FULFILL_PREFIX}{order.id}",
            "type": f"shopify.fulfillment.{err or 'cleared'}",
            "status": "resolved",
            "order_id": order.id,
            "order_state": order.state,
            "tracking_number": order.tracking_number,
            "merchant": merchants.get(order.merchant_id) if order.merchant_id else None,
            "merchant_id": order.merchant_id,
            "reported_by": "shopify",
            "resolved_at": now_utc().isoformat(),
            "resolution_note": note,
            "source": "shopify_fulfillment",
        }

    def retry_exception_dispatch(self, db: Session, ctx: AdminContext, exception_id: str) -> dict:
        """Re-queue a FAILED order for dispatch and resolve the exception."""
        if exception_id.startswith(SHOPIFY_DLQ_PREFIX) or exception_id.startswith(
            SHOPIFY_FULFILL_PREFIX
        ):
            raise ValueError("shopify_exception_use_replay_or_repush")
        e = db.get(OrderException, exception_id)
        if not e:
            raise LookupError("exception_not_found")
        if e.status == "resolved":
            raise ValueError("already_resolved")
        order = e.order
        if order.state != OrderState.FAILED.value:
            raise ValueError("order_not_retryable")

        path = transition_path(OrderState(order.state), OrderState.DISPATCH_READY)
        if path is None:
            raise ValueError("invalid_order_transition_path")
        for step in path:
            transition_order_state(
                db,
                order,
                step,
                event_type="order.exception_retry",
                actor_type="admin",
                actor_id=ctx.user.id,
                payload={"exception_id": e.id, "retry": True},
            )
        result = self.resolve_exception(db, ctx, exception_id, action="retry_dispatch")
        return {"exception": result, "order_state": order.state}

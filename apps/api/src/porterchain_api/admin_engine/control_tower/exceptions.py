"""Exception center — acknowledge / resolve / retry dispatch."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Customer, Order, OrderException
from porterchain_shared.events.catalog import DomainEventType

from porterchain_api.admin_engine.control_tower._helpers import now_utc, transition_path


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
        return [self._exception_dict(e, o, merchants, emails) for e, o in rows]

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
            "customer_email": (customer_emails or {}).get(o.customer_id) if o.customer_id else None,
            "reported_by": e.reported_by_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "acknowledged_at": res.get("acknowledged_at"),
            "acknowledged_by": res.get("acknowledged_by"),
            "resolution_note": res.get("note"),
            "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
        }

    def acknowledge_exception(self, db: Session, ctx: AdminContext, exception_id: str) -> dict:
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

    def resolve_exception(
        self,
        db: Session,
        ctx: AdminContext,
        exception_id: str,
        *,
        note: str | None = None,
        action: str | None = None,
    ) -> dict:
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

    def retry_exception_dispatch(self, db: Session, ctx: AdminContext, exception_id: str) -> dict:
        """Re-queue a FAILED order for dispatch and resolve the exception."""
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

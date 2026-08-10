"""Admin Customer 360 — list/detail for Partners retail demand nodes.

Identity SoT remains Settings Users / Clerk. This service never creates or
invites customers (self SignUp only). Reuses Order customer_360 fields.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import SupportTicket
from porterchain_api.models import Customer, Order

_REVENUE_STATES = frozenset({"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"})


class CustomerAdminService:
    def list_customers(
        self,
        db: Session,
        *,
        search: str | None = None,
        clerk_linked: bool | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        q = db.query(Customer).order_by(Customer.created_at.desc())
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Customer.email.ilike(like),
                    Customer.customer_reference.ilike(like),
                    Customer.phone.ilike(like),
                    Customer.id.ilike(like),
                )
            )
        rows = q.limit(limit).all()
        out: list[dict[str, Any]] = []
        for c in rows:
            linked = self._clerk_linked(c.clerk_user_id)
            if clerk_linked is True and not linked:
                continue
            if clerk_linked is False and linked:
                continue
            out.append(self._row(db, c, light=True))
        return out

    def detail(self, db: Session, customer_id: str) -> dict[str, Any]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        return self._row(db, customer, light=False)

    def orders(self, db: Session, customer_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        rows = (
            db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": o.id,
                "order_number": o.order_number,
                "tracking_number": o.tracking_number,
                "state": o.state,
                "amount_cents": o.amount_cents,
                "currency": o.currency,
                "scheduled_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in rows
        ]

    def _row(self, db: Session, customer: Customer, *, light: bool) -> dict[str, Any]:
        linked = self._clerk_linked(customer.clerk_user_id)
        lifetime_orders = (
            db.query(func.count(Order.id)).filter(Order.customer_id == customer.id).scalar() or 0
        )
        lifetime_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.customer_id == customer.id, Order.state.in_(tuple(_REVENUE_STATES)))
            .scalar()
            or 0
        )
        open_tickets = (
            db.query(func.count(SupportTicket.id))
            .filter(
                SupportTicket.customer_id == customer.id,
                SupportTicket.status.in_(("open", "in_progress", "waiting")),
            )
            .scalar()
            or 0
        )
        display = customer.customer_reference or (customer.email.split("@")[0] if customer.email else customer.id)
        row: dict[str, Any] = {
            "id": customer.id,
            "email": customer.email,
            "phone": customer.phone,
            "customer_reference": customer.customer_reference,
            "display_name": display,
            "clerk_user_id": customer.clerk_user_id if linked else None,
            "clerk_linked": linked,
            "identity_status": "clerk_linked" if linked else "orphan",
            "stripe_customer_id": getattr(customer, "stripe_customer_id", None),
            "privacy_status": customer.privacy_status,
            "privacy_hold_reference": customer.privacy_hold_reference,
            "lifetime_orders": int(lifetime_orders),
            "lifetime_revenue_cents": int(lifetime_revenue),
            "open_support_tickets": int(open_tickets),
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
        }
        if not light:
            recent = (
                db.query(Order)
                .filter(Order.customer_id == customer.id)
                .order_by(Order.created_at.desc())
                .limit(5)
                .all()
            )
            row["recent_orders"] = [
                {
                    "order_id": o.id,
                    "order_number": o.order_number,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "amount_cents": o.amount_cents,
                }
                for o in recent
            ]
        return row

    @staticmethod
    def _clerk_linked(clerk_user_id: str | None) -> bool:
        if not clerk_user_id:
            return False
        return not str(clerk_user_id).startswith("pending")

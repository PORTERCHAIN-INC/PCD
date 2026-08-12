"""Admin Customer 360 — list/detail for Partners retail demand nodes.

Identity SoT remains Settings Users / Clerk. This service never creates or
invites customers (self SignUp only). Reuses Order customer_360 fields.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, SupportTicket
from porterchain_api.models import Customer, Invoice, Order, Payment

_REVENUE_STATES = frozenset({"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"})
_OPEN_SUPPORT = frozenset({"open", "in_progress", "waiting", "escalated"})
_OPEN_CLAIMS = frozenset({
    "open",
    "new",
    "assigned",
    "investigating",
    "under_investigation",
    "pending",
    "in_review",
    "waiting_customer",
    "waiting_merchant",
    "waiting_driver",
    "waiting_insurance",
})


class CustomerAdminService:
    def stats(self, db: Session) -> dict[str, Any]:
        total = db.query(func.count(Customer.id)).scalar() or 0
        # Orphan = missing clerk id or pending:* placeholder from pre-signup rows
        orphan = (
            db.query(func.count(Customer.id))
            .filter(
                or_(
                    Customer.clerk_user_id.is_(None),
                    Customer.clerk_user_id == "",
                    Customer.clerk_user_id.like("pending%"),
                )
            )
            .scalar()
            or 0
        )
        clerk_linked = int(total) - int(orphan)
        dsr_hold = (
            db.query(func.count(Customer.id))
            .filter(Customer.privacy_status == "deletion_hold")
            .scalar()
            or 0
        )
        since = datetime.now(UTC) - timedelta(days=30)
        orders_30d = (
            db.query(func.count(Order.id)).filter(Order.created_at >= since).scalar() or 0
        )
        revenue_30d = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.created_at >= since,
                Order.state.in_(tuple(_REVENUE_STATES)),
                Order.customer_id.isnot(None),
            )
            .scalar()
            or 0
        )
        return {
            "total": int(total),
            "clerk_linked": int(clerk_linked),
            "orphan": int(orphan),
            "dsr_hold": int(dsr_hold),
            "orders_30d": int(orders_30d),
            "revenue_30d_cents": int(revenue_30d),
        }

    def list_customers(
        self,
        db: Session,
        *,
        search: str | None = None,
        clerk_linked: bool | None = None,
        privacy_status: str | None = None,
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
        if privacy_status:
            q = q.filter(Customer.privacy_status == privacy_status.strip())
        if clerk_linked is True:
            q = q.filter(
                Customer.clerk_user_id.isnot(None),
                Customer.clerk_user_id != "",
                ~Customer.clerk_user_id.like("pending%"),
            )
        elif clerk_linked is False:
            q = q.filter(
                or_(
                    Customer.clerk_user_id.is_(None),
                    Customer.clerk_user_id == "",
                    Customer.clerk_user_id.like("pending%"),
                )
            )
        rows = q.limit(limit).all()
        return [self._row(db, c, light=True) for c in rows]

    def detail(self, db: Session, customer_id: str) -> dict[str, Any]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        return self._row(db, customer, light=False)

    def orders(
        self,
        db: Session,
        customer_id: str,
        *,
        limit: int = 50,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        q = db.query(Order).filter(Order.customer_id == customer_id)
        if state:
            q = q.filter(Order.state == state.strip().upper())
        rows = q.order_by(Order.created_at.desc()).limit(limit).all()
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

    def invoices(self, db: Session, customer_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        rows = (
            db.query(Invoice)
            .filter(Invoice.customer_id == customer_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "receipt_number": inv.receipt_number,
                "order_id": inv.order_id,
                "amount_cents": inv.amount_cents,
                "tax_cents": inv.tax_cents,
                "fees_cents": inv.fees_cents,
                "currency": inv.currency,
                "stripe_receipt_url": inv.stripe_receipt_url,
                "pdf_url": inv.pdf_url,
                "due_at": inv.due_at.isoformat() if inv.due_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in rows
        ]

    def payments(self, db: Session, customer_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")
        rows = (
            db.query(Payment)
            .filter(Payment.customer_id == customer_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": p.id,
                "order_id": p.order_id,
                "status": p.status,
                "amount_cents": p.amount_cents,
                "currency": p.currency,
                "payment_method": p.payment_method,
                "payment_reference": p.payment_reference,
                "stripe_payment_intent_id": p.stripe_payment_intent_id,
                "receipt_url": p.receipt_url,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ]

    def care(self, db: Session, customer_id: str, *, limit: int = 20) -> dict[str, Any]:
        customer = db.get(Customer, customer_id)
        if not customer:
            raise LookupError("customer_not_found")

        tickets = (
            db.query(SupportTicket)
            .filter(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(limit)
            .all()
        )
        open_tickets_total = (
            db.query(func.count(SupportTicket.id))
            .filter(
                SupportTicket.customer_id == customer_id,
                SupportTicket.status.in_(tuple(_OPEN_SUPPORT)),
            )
            .scalar()
            or 0
        )

        order_ids = [
            o.id
            for o in db.query(Order.id).filter(Order.customer_id == customer_id).all()
        ]
        claims: list[Claim] = []
        open_claims_total = 0
        if order_ids:
            claims = (
                db.query(Claim)
                .filter(Claim.order_id.in_(order_ids))
                .order_by(Claim.created_at.desc())
                .limit(limit)
                .all()
            )
            open_claims_total = (
                db.query(func.count(Claim.id))
                .filter(
                    Claim.order_id.in_(order_ids),
                    Claim.status.in_(tuple(_OPEN_CLAIMS)),
                )
                .scalar()
                or 0
            )

        return {
            "open_support_tickets": int(open_tickets_total),
            "open_claims": int(open_claims_total),
            "support_tickets": [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "priority": t.priority,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tickets
            ],
            "claims": [
                {
                    "id": c.id,
                    "order_id": c.order_id,
                    "claim_type": c.claim_type,
                    "status": c.status,
                    "description": (c.description or "")[:200] or None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                }
                for c in claims
            ],
        }

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
                SupportTicket.status.in_(tuple(_OPEN_SUPPORT)),
            )
            .scalar()
            or 0
        )
        last_order_at = (
            db.query(func.max(Order.created_at)).filter(Order.customer_id == customer.id).scalar()
        )
        open_claims = 0
        order_ids_subq = db.query(Order.id).filter(Order.customer_id == customer.id)
        open_claims = (
            db.query(func.count(Claim.id))
            .filter(Claim.order_id.in_(order_ids_subq), Claim.status.in_(tuple(_OPEN_CLAIMS)))
            .scalar()
            or 0
        )

        display = self._display_name(customer)
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
            "privacy_hold_at": (
                customer.privacy_hold_at.isoformat()
                if getattr(customer, "privacy_hold_at", None)
                else None
            ),
            "lifetime_orders": int(lifetime_orders),
            "lifetime_revenue_cents": int(lifetime_revenue),
            "open_support_tickets": int(open_tickets),
            "open_claims": int(open_claims),
            "last_order_at": last_order_at.isoformat() if last_order_at else None,
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
            row["settings_users_href"] = (
                f"/settings?section=users&tab=customer&q={customer.email}"
                if customer.email
                else "/settings?section=users&tab=customer"
            )
        return row

    @staticmethod
    def _display_name(customer: Customer) -> str:
        if customer.customer_reference:
            return customer.customer_reference
        email = (customer.email or "").strip()
        if email and "@" in email:
            return email.split("@", 1)[0]
        if email:
            return email
        return customer.id

    @staticmethod
    def _clerk_linked(clerk_user_id: str | None) -> bool:
        if not clerk_user_id:
            return False
        return not str(clerk_user_id).startswith("pending")

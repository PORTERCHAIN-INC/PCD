"""Finance — invoices, refunds, statements."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.models import Invoice, Order, Payment


class AdminFinanceService:
    def list_invoices(self, db: Session, *, limit: int = 100) -> list[Invoice]:
        return db.query(Invoice).order_by(Invoice.created_at.desc()).limit(limit).all()

    def list_payments(self, db: Session, *, limit: int = 100) -> list[Payment]:
        return db.query(Payment).order_by(Payment.created_at.desc()).limit(limit).all()

    def revenue_summary(self, db: Session) -> dict:
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= month_start)
            .scalar()
            or 0
        )
        invoice_total = (
            db.query(func.coalesce(func.sum(Invoice.amount_cents), 0))
            .filter(Invoice.created_at >= month_start)
            .scalar()
            or 0
        )
        refunds = (
            db.query(func.count(Payment.id))
            .filter(Payment.status == "REFUNDED", Payment.created_at >= month_start)
            .scalar()
            or 0
        )
        return {
            "monthly_revenue_cents": int(monthly_revenue),
            "invoice_total_cents": int(invoice_total),
            "refund_count": int(refunds),
        }

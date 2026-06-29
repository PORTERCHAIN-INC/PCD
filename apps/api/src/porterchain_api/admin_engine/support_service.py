"""Customer support tickets."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import SupportTicket
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E


class AdminSupportService:
    def list_tickets(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[SupportTicket]:
        q = db.query(SupportTicket)
        if status:
            q = q.filter(SupportTicket.status == status)
        return q.order_by(SupportTicket.created_at.desc()).limit(limit).all()

    def create_ticket(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        subject: str,
        description: str | None = None,
        priority: str = "normal",
        order_id: str | None = None,
        customer_id: str | None = None,
        merchant_id: str | None = None,
        driver_id: str | None = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            subject=subject,
            description=description,
            priority=priority,
            order_id=order_id,
            customer_id=customer_id,
            merchant_id=merchant_id,
            driver_id=driver_id,
            assigned_to=ctx.user.id,
        )
        db.add(ticket)
        db.flush()
        emit_event(
            db,
            event_type=E.TICKET_CREATED,
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def update_ticket(self, db: Session, ticket_id: str, **fields) -> SupportTicket:
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if not ticket:
            raise LookupError("ticket_not_found")
        for k, v in fields.items():
            if v is not None and hasattr(ticket, k):
                setattr(ticket, k, v)
        db.commit()
        db.refresh(ticket)
        return ticket

"""Driver support tickets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SupportService:
    def list_tickets(self, db: Session, driver_id: str, *, limit: int = 20) -> list[dict]:
        from porterchain_api.admin_models import SupportTicket

        rows = (
            db.query(SupportTicket)
            .filter(SupportTicket.driver_id == driver_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize(t) for t in rows]

    def create_ticket(
        self,
        db: Session,
        driver: Any,
        *,
        subject: str,
        description: str | None = None,
        order_id: str | None = None,
        priority: str = "normal",
    ) -> dict:
        from porterchain_api.admin_models import SupportTicket

        ticket = SupportTicket(
            driver_id=driver.id,
            order_id=order_id,
            subject=subject,
            description=description,
            priority=priority,
            status="open",
        )
        db.add(ticket)
        db.flush()
        return self._serialize(ticket)

    @staticmethod
    def _serialize(ticket: Any) -> dict:
        return {
            "id": ticket.id,
            "status": ticket.status,
            "priority": ticket.priority,
            "subject": ticket.subject,
            "description": ticket.description,
            "order_id": ticket.order_id,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
        }

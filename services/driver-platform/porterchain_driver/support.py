"""Driver support tickets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class SupportService:
    def list_tickets(self, db: Session, driver_id: str, *, limit: int = 20) -> list[dict]:
        from porterchain_driver.support_bridge import DriverSupportBridgeService

        return DriverSupportBridgeService().list_tickets(db, driver_id, limit=limit)

    def create_ticket(
        self,
        db: Session,
        driver: Any,
        *,
        subject: str,
        description: str | None = None,
        order_id: str | None = None,
        priority: str = "normal",
        category: str = "driver_support",
    ) -> dict:
        from porterchain_driver.support_bridge import DriverSupportBridgeService

        return DriverSupportBridgeService().create_ticket(
            db,
            driver,
            subject=subject,
            description=description,
            order_id=order_id,
            priority=priority,
            category=category,
        )

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

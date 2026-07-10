"""Customer service — retail customer lifecycle."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.models import Customer, Lead, Quote


class CustomerService:
    def __init__(self) -> None:
        self._visitor = VisitorTrackingService()

    def upsert(
        self,
        db: Session,
        *,
        clerk_user_id: str,
        email: str,
        phone: str | None,
        visitor_session_id: str | None = None,
    ) -> Customer:
        from porterchain_api.auth.portal_guard import clerk_id_staff_portal

        conflict = clerk_id_staff_portal(db, clerk_user_id)
        if conflict:
            raise ValueError(f"identity_conflict:clerk_user_is_{conflict}")

        customer = db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()
        is_new = customer is None
        if customer:
            customer.email = email
            customer.phone = phone
            if visitor_session_id:
                customer.visitor_session_id = visitor_session_id
        else:
            customer = Customer(
                clerk_user_id=clerk_user_id,
                email=email,
                phone=phone,
                visitor_session_id=visitor_session_id,
            )
            db.add(customer)
        db.commit()
        db.refresh(customer)

        if is_new:
            emit_event(
                db,
                event_type=E.CUSTOMER_REGISTERED,
                aggregate_type="customer",
                aggregate_id=customer.id,
                actor_type="customer",
                actor_id=clerk_user_id,
                payload={"email": email},
            )
            db.commit()

        return customer

    def merge_anonymous_session(
        self,
        db: Session,
        quote: Quote,
        customer: Customer,
        anonymous_session_id: str | None,
    ) -> None:
        session_id = anonymous_session_id or quote.visitor_session_id
        if session_id:
            siblings = (
                db.query(Quote)
                .filter(
                    Quote.anonymous_session_id == session_id,
                    Quote.customer_id.is_(None),
                    Quote.id != quote.id,
                )
                .all()
            )
            for s in siblings:
                s.customer_id = customer.id
            if session_id:
                self._visitor.merge_to_customer(db, session_id, customer.id)

        quote.customer_id = customer.id
        quote.anonymous_session_id = session_id or quote.anonymous_session_id
        customer.visitor_session_id = session_id or customer.visitor_session_id
        db.commit()

    def create_lead(
        self,
        db: Session,
        *,
        email: str,
        phone: str | None,
        quote_id: str,
        customer_id: str,
    ) -> Lead:
        lead = Lead(
            source="website_booking",
            email=email,
            phone=phone,
            quote_id=quote_id,
            customer_id=customer_id,
            stage="booking_started",
        )
        db.add(lead)
        db.flush()
        emit_event(
            db,
            event_type=E.LEAD_CREATED,
            aggregate_type="lead",
            aggregate_id=lead.id,
            correlation_id=quote_id,
            payload={"email": email},
        )
        from porterchain_api.booking_engine.crm_lead_mirror import mirror_booking_lead_to_crm

        mirror_booking_lead_to_crm(
            db,
            email=email,
            phone=phone,
            quote_id=quote_id,
            customer_id=customer_id,
            stage=lead.stage,
        )
        db.commit()
        return lead

    def get_by_clerk(self, db: Session, clerk_user_id: str) -> Customer | None:
        return db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()

    def get_or_create_from_clerk(
        self,
        db: Session,
        *,
        clerk_user_id: str,
        email: str | None,
        phone: str | None = None,
    ) -> Customer:
        """Ensure a retail Customer row exists for a signed-in Clerk user."""
        from porterchain_api.auth.portal_guard import clerk_id_staff_portal

        conflict = clerk_id_staff_portal(db, clerk_user_id)
        if conflict:
            raise ValueError(f"identity_conflict:clerk_user_is_{conflict}")

        existing = self.get_by_clerk(db, clerk_user_id)
        if existing:
            if email and existing.email != email:
                existing.email = email
                db.commit()
                db.refresh(existing)
            if phone and existing.phone != phone:
                existing.phone = phone
                db.commit()
                db.refresh(existing)
            return existing
        if not email:
            raise ValueError("email_required")
        return self.upsert(
            db,
            clerk_user_id=clerk_user_id,
            email=email,
            phone=phone,
        )

    def get_dashboard(self, db: Session, customer_id: str) -> dict:
        from porterchain_api.booking_engine.tracking_service import TrackingService

        return TrackingService().get_customer_dashboard(db, customer_id)

    def list_support_tickets(self, db: Session, customer_id: str, *, limit: int = 20) -> list:
        from porterchain_api.admin_models import SupportTicket

        return (
            db.query(SupportTicket)
            .filter(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
            .limit(limit)
            .all()
        )

    def create_support_ticket(
        self,
        db: Session,
        *,
        customer_id: str,
        subject: str,
        description: str | None = None,
        order_id: str | None = None,
    ):
        from porterchain_api.admin_models import SupportTicket
        from porterchain_shared.events.catalog import DomainEventType

        if order_id:
            from porterchain_api.models import Order

            order = db.query(Order).filter(Order.id == order_id, Order.customer_id == customer_id).first()
            if not order:
                raise PermissionError("order_not_owned")

        ticket = SupportTicket(
            subject=subject,
            description=description,
            customer_id=customer_id,
            order_id=order_id,
            priority="normal",
        )
        db.add(ticket)
        db.flush()
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        from porterchain_api.domain.support import ticket_number

        emit_event(
            db,
            event_type=DomainEventType.SUPPORT_TICKET_CREATED,
            aggregate_type="support_ticket",
            aggregate_id=ticket.id,
            actor_type="customer",
            actor_id=customer_id,
            payload={
                "subject": subject,
                "order_id": order_id,
                "ticket_number": ticket_number(ticket.id),
                "email": customer.email if customer else None,
            },
        )
        db.commit()
        db.refresh(ticket)
        return ticket

    def rebook_payload(self, db: Session, customer_id: str, order_id: str) -> dict:
        from porterchain_api.booking_engine.repositories.order_repository import OrderRepository

        order = OrderRepository().get_for_customer(db, customer_id, order_id)
        if not order:
            raise LookupError("order_not_found")
        return {
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "vehicle_class": order.pickup.get("vehicle_class") if isinstance(order.pickup, dict) else None,
            "source_order_id": order.id,
            "tracking_number": order.tracking_number,
        }

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
        db.commit()
        return lead

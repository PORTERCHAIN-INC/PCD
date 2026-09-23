"""Customer service — retail customer lifecycle."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.visitor_tracking_service import VisitorTrackingService
from porterchain_api.booking_models import Customer, Lead, Quote


def _name_from_email(email: str) -> str | None:
    local = (email or "").split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return local.title()[:255] if local else None


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
        full_name: str | None = None,
    ) -> Customer:
        from porterchain_api.auth.email_identity import EMAIL_CLERK_MISMATCH, emails_match, normalize_email
        from porterchain_api.auth.portal_guard import clerk_id_staff_portal

        conflict = clerk_id_staff_portal(db, clerk_user_id)
        if conflict:
            raise ValueError(f"identity_conflict:clerk_user_is_{conflict}")

        clerk_email = normalize_email(email)
        if not clerk_email:
            raise ValueError("email_required")

        customer = db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()
        is_new = customer is None

        if customer:
            # C-15: never silently overwrite a bound email when Clerk disagrees.
            if customer.email and not emails_match(customer.email, clerk_email):
                raise ValueError(EMAIL_CLERK_MISMATCH)
            if not customer.email:
                customer.email = clerk_email
            if phone is not None:
                customer.phone = phone
            if visitor_session_id:
                customer.visitor_session_id = visitor_session_id
            if not customer.full_name:
                customer.full_name = (full_name or "").strip() or _name_from_email(clerk_email)
        else:
            # C-14: merge orphan / pending rows that already hold this email.
            orphan = (
                db.query(Customer)
                .filter(func.lower(Customer.email) == clerk_email)
                .order_by(Customer.created_at.asc())
                .first()
            )
            if orphan:
                orphan_clerk = orphan.clerk_user_id or ""
                if orphan_clerk and not orphan_clerk.startswith("pending") and orphan_clerk != clerk_user_id:
                    raise ValueError(EMAIL_CLERK_MISMATCH)
                customer = orphan
                customer.clerk_user_id = clerk_user_id
                customer.email = clerk_email
                if phone is not None:
                    customer.phone = phone
                if visitor_session_id:
                    customer.visitor_session_id = visitor_session_id
                if not customer.full_name:
                    customer.full_name = (full_name or "").strip() or _name_from_email(clerk_email)
                is_new = False
            else:
                customer = Customer(
                    clerk_user_id=clerk_user_id,
                    email=clerk_email,
                    phone=phone,
                    visitor_session_id=visitor_session_id,
                    full_name=(full_name or "").strip() or _name_from_email(clerk_email),
                )
                db.add(customer)
        db.commit()
        db.refresh(customer)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, clerk_user_id)

        if is_new:
            emit_event(
                db,
                event_type=E.CUSTOMER_REGISTERED,
                aggregate_type="customer",
                aggregate_id=customer.id,
                actor_type="customer",
                actor_id=clerk_user_id,
                payload={"email": clerk_email},
            )
            db.commit()

        return customer

    def ensure_from_email(self, db: Session, *, email: str, phone: str | None) -> Customer:
        """Create or reuse a retail Customer for merchant convert-to-customer (flush only)."""
        from porterchain_api.auth.email_identity import normalize_email
        from porterchain_api.auth.invitation_service import pending_clerk_id
        from porterchain_api.booking_engine.numbers import generate_customer_reference

        normalized = normalize_email(email)
        if not normalized:
            raise ValueError("owner_email_required")
        existing = (
            db.query(Customer)
            .filter(func.lower(Customer.email) == normalized)
            .order_by(Customer.created_at.asc())
            .first()
        )
        if existing:
            if phone and not existing.phone:
                existing.phone = phone
            return existing
        pending = pending_clerk_id(normalized)
        clash = db.query(Customer).filter(Customer.clerk_user_id == pending).first()
        if clash:
            return clash
        customer = Customer(
            clerk_user_id=pending,
            email=normalized,
            phone=phone,
            customer_reference=generate_customer_reference(),
            full_name=_name_from_email(normalized),
        )
        db.add(customer)
        db.flush()
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
        # C-24: upsert by quote — booking retries must not spawn duplicate leads.
        existing = db.query(Lead).filter(Lead.quote_id == quote_id).first()
        if existing:
            existing.email = email or existing.email
            existing.phone = phone or existing.phone
            existing.customer_id = customer_id or existing.customer_id
            if not existing.crm_lead_id:
                from porterchain_api.booking_engine.crm_lead_mirror import mirror_booking_lead_to_crm

                crm_lead = mirror_booking_lead_to_crm(
                    db,
                    email=email,
                    phone=phone,
                    quote_id=quote_id,
                    customer_id=customer_id,
                    stage=existing.stage,
                )
                if crm_lead:
                    existing.crm_lead_id = crm_lead.id
            db.commit()
            db.refresh(existing)
            return existing

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

        crm_lead = mirror_booking_lead_to_crm(
            db,
            email=email,
            phone=phone,
            quote_id=quote_id,
            customer_id=customer_id,
            stage=lead.stage,
        )
        if crm_lead:
            lead.crm_lead_id = crm_lead.id
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

        from porterchain_api.auth.email_identity import EMAIL_CLERK_MISMATCH, emails_match, normalize_email

        existing = self.get_by_clerk(db, clerk_user_id)
        if existing:
            clerk_email = normalize_email(email)
            if clerk_email and not emails_match(existing.email, clerk_email):
                # Never keep a Clerk id bound to a different system email.
                raise ValueError(EMAIL_CLERK_MISMATCH)
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
        from porterchain_api.support_engine.support_service import AdminSupportService

        return AdminSupportService().list_for_customer(db, customer_id, limit=limit)

    def create_support_ticket(
        self,
        db: Session,
        *,
        customer_id: str,
        subject: str,
        description: str | None = None,
        order_id: str | None = None,
        idempotency_key: str | None = None,
    ):
        from porterchain_api.support_engine.support_service import AdminSupportService

        if order_id:
            from porterchain_api.booking_models import Order

            order = db.query(Order).filter(Order.id == order_id, Order.customer_id == customer_id).first()
            if not order:
                raise PermissionError("order_not_owned")
        return AdminSupportService().create_actor_ticket(
            db,
            subject=subject,
            description=description,
            order_id=order_id,
            customer_id=customer_id,
            actor_type="customer",
            actor_id=customer_id,
            idempotency_key=idempotency_key,
        )

    def rebook_payload(self, db: Session, customer_id: str, order_id: str) -> dict:
        from porterchain_api.booking_engine.repositories.order_repository import OrderRepository
        from porterchain_api.booking_models import Quote

        order = OrderRepository().get_for_customer(db, customer_id, order_id)
        if not order:
            raise LookupError("order_not_found")
        # C-24: vehicle from quote (not pickup address blob).
        vehicle = None
        quote = db.get(Quote, order.quote_id) if order.quote_id else None
        if quote and quote.vehicle_class:
            vehicle = quote.vehicle_class
        if not vehicle and isinstance(order.pickup, dict):
            vehicle = order.pickup.get("vehicle_class")
        blob = quote.parcels if quote and isinstance(quote.parcels, dict) else {}
        if not blob and isinstance(order.compliance_metadata, dict):
            stored = order.compliance_metadata.get("parcels")
            blob = stored if isinstance(stored, dict) else {}
        mode = blob.get("booking_mode")
        if not mode and isinstance(order.compliance_metadata, dict):
            mode = order.compliance_metadata.get("booking_mode")
        return {
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "vehicle_class": vehicle,
            "booking_mode": mode,
            "parcels": blob.get("items") if isinstance(blob.get("items"), list) else [],
            "declared_value_cents": (quote.declared_value_cents if quote else None)
            or blob.get("declared_value_cents"),
            "additional_stops": quote.additional_stops if quote else None,
            "source_order_id": order.id,
            "tracking_number": order.tracking_number,
        }

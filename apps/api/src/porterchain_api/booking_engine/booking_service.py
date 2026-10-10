"""Booking service — continue booking flow per PRD Phase B."""

from sqlalchemy.orm import Session

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.customer_service import CustomerService
from porterchain_api.booking_engine.payment_service import PaymentService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.config import Settings
from porterchain_api.domain.states import QuoteState
from porterchain_api.booking_models import Customer, Quote


class BookingService:
    def __init__(self) -> None:
        self._quotes = QuoteService()
        self._customers = CustomerService()
        self._payments = PaymentService()
        self._drafts = BookingDraftService()

    def start_booking(
        self,
        db: Session,
        settings: Settings,
        *,
        quote_id: str,
        email: str,
        phone: str,
        clerk_user_id: str | None,
        anonymous_session_id: str | None,
        consent: dict | None = None,
        checkout_channel: str = "retail",
        full_name: str | None = None,
    ) -> tuple[Quote, Customer, str | None]:
        """Start checkout. ``clerk_user_id=None`` is guest (express) checkout: the customer
        row is created/reused by email with a ``pending`` Clerk id and is merged on first
        Clerk sign-in (C-14), so no account step blocks payment."""
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if not quote:
            raise LookupError("quote_not_found")
        if quote.state == QuoteState.QUOTE_EXPIRED.value:
            raise ValueError("quote_expired")
        if quote.state not in (QuoteState.QUOTE.value, QuoteState.BOOKING_PENDING.value):
            raise ValueError("quote_not_bookable")

        # Compliance gate — Terms, Privacy and Dangerous-goods must be accepted.
        consent = consent or {}
        if not (consent.get("terms_accepted") and consent.get("privacy_accepted")):
            raise ValueError("consent_required")

        if clerk_user_id:
            customer = self._customers.upsert(
                db,
                clerk_user_id=clerk_user_id,
                email=email,
                phone=phone,
                visitor_session_id=anonymous_session_id or quote.visitor_session_id,
            )
        else:
            customer = self._customers.ensure_from_email(db, email=email, phone=phone, full_name=full_name)
            if anonymous_session_id and not customer.visitor_session_id:
                customer.visitor_session_id = anonymous_session_id
            db.commit()
            db.refresh(customer)
        self._customers.merge_anonymous_session(db, quote, customer, anonymous_session_id)
        session_id = anonymous_session_id or quote.visitor_session_id
        if session_id:
            self._drafts.merge_session_to_customer(
                db,
                session_id=session_id,
                customer_id=customer.id,
                quote_id=quote.id,
            )

        quote.email = email
        quote.phone = phone
        quote.consent = consent
        quote.state = QuoteState.BOOKING_PENDING.value
        db.commit()

        emit_event(
            db,
            event_type=E.BOOKING_CONSENT_RECORDED,
            aggregate_type="quote",
            aggregate_id=quote.id,
            correlation_id=quote.id,
            actor_type="customer",
            actor_id=customer.id,
            payload={
                "terms_accepted": bool(consent.get("terms_accepted")),
                "privacy_accepted": bool(consent.get("privacy_accepted")),
                "dangerous_goods_confirmed": bool(consent.get("dangerous_goods_confirmed")),
                "consent_at": consent.get("consent_at"),
            },
        )
        db.commit()

        emit_event(
            db,
            event_type=E.BOOKING_STARTED,
            aggregate_type="quote",
            aggregate_id=quote.id,
            correlation_id=quote.id,
            actor_type="customer",
            actor_id=customer.id,
            payload={"email": email},
        )
        self._customers.create_lead(
            db,
            email=email,
            phone=phone,
            quote_id=quote.id,
            customer_id=customer.id,
            visitor_session_id=session_id,
            consent=consent,
        )
        if clerk_user_id:
            emit_event(
                db,
                event_type=E.CUSTOMER_AUTHENTICATED,
                aggregate_type="customer",
                aggregate_id=customer.id,
                correlation_id=quote.id,
                actor_type="customer",
                actor_id=customer.id,
                payload={"clerk_user_id": clerk_user_id},
            )
        self._quotes.accept_quote(db, quote)
        if clerk_user_id:
            self._drafts.on_customer_authenticated(
                db,
                quote_id=quote.id,
                customer_id=customer.id,
                clerk_user_id=clerk_user_id,
            )

        checkout_url, _payment = self._payments.start_payment(
            db, settings, quote, customer, checkout_channel=checkout_channel
        )
        db.refresh(quote)
        return quote, customer, checkout_url

    def record_abandoned_checkout(
        self,
        db: Session,
        quote: Quote,
        *,
        reason: str = "session_expired",
    ) -> None:
        from porterchain_api.booking_models import AbandonedCheckout

        if not quote.email:
            return
        db.add(
            AbandonedCheckout(
                quote_id=quote.id,
                customer_id=quote.customer_id,
                email=quote.email,
                phone=quote.phone,
                stripe_checkout_session_id=quote.stripe_checkout_session_id,
                reason=reason,
            )
        )
        from porterchain_api.config import get_settings

        website = (get_settings().website_url or "").rstrip("/")
        emit_event(
            db,
            event_type=E.CHECKOUT_ABANDONED,
            aggregate_type="quote",
            aggregate_id=quote.id,
            correlation_id=quote.id,
            payload={
                "reason": reason,
                "email": quote.email,
                "phone": quote.phone,
                "quote_id": quote.id,
                "customer_id": quote.customer_id,
                "recovery_url": f"{website}/sign-up?intent=quote&quote_id={quote.id}" if website else None,
            },
        )
        db.commit()

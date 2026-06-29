from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.booking_engine import QuoteService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.models import Booking, Invoice, Order, Quote
from porterchain_api.schemas import (
    BookingConfirmationResponse,
    BookingResponse,
    CheckoutMockCompleteRequest,
    CreateQuoteRequest,
    OrderResponse,
    PricingLineItem,
    QuoteResponse,
    StartBookingRequest,
)
from porterchain_api.booking_engine import BookingConfirmationService, BookingService

router = APIRouter(prefix="/v1", tags=["quotes"])
_quote_service = QuoteService()
_booking_service = BookingService()
_confirmation_service = BookingConfirmationService()


def _format_cad(cents: int) -> str:
    return f"${cents / 100:.2f} CAD"


def _quote_response(quote: Quote) -> QuoteResponse:
    items = quote.pricing_breakdown.get("items", [])
    breakdown = [PricingLineItem(**item) for item in items]
    distance_km = round(quote.distance_meters / 1000, 1) if quote.distance_meters else None
    return QuoteResponse(
        quote_id=quote.id,
        state=quote.state,
        amount_cents=quote.amount_cents,
        currency=quote.currency,
        amount_display=_format_cad(quote.amount_cents),
        expires_at=quote.expires_at,
        distance_km=distance_km,
        pricing_breakdown=breakdown,
        vehicle_class=quote.vehicle_class,
        scheduled_at=quote.scheduled_at,
    )


def _confirmation_response(order: Order, db: Session) -> BookingConfirmationResponse:
    booking = db.query(Booking).filter(Booking.order_id == order.id).first()
    invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    return BookingConfirmationResponse(
        booking_id=booking.id if booking else "",
        booking_number=booking.booking_number if booking else "",
        order_id=order.id,
        order_number=order.order_number,
        tracking_number=order.tracking_number,
        invoice_id=invoice.id if invoice else "",
        invoice_number=invoice.invoice_number if invoice else "",
        state=order.state,
        amount_cents=order.amount_cents,
        currency=order.currency,
        scheduled_at=order.scheduled_at,
        pickup=order.pickup,
        dropoff=order.dropoff,
        fleetbase_order_id=order.fleetbase_order_id,
    )


@router.post("/quotes", response_model=QuoteResponse)
def post_quote(
    body: CreateQuoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> QuoteResponse:
    client_ip = request.client.host if request.client else None
    quote = _quote_service.create_quote(db, settings, body, ip_address=client_ip)
    return _quote_response(quote)


@router.get("/quotes/{quote_id}", response_model=QuoteResponse)
def get_quote(
    quote_id: str,
    db: Session = Depends(get_db),
) -> QuoteResponse:
    quote = _quote_service.get_quote(db, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="quote_not_found")
    return _quote_response(quote)


@router.post("/bookings", response_model=BookingResponse)
def post_booking(
    body: StartBookingRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> BookingResponse:
    if body.clerk_user_id != clerk_user_id and not settings.clerk_dev_bypass:
        raise HTTPException(status_code=403, detail="clerk_user_mismatch")
    try:
        quote, customer, checkout_url = _booking_service.start_booking(
            db,
            settings,
            quote_id=body.quote_id,
            email=body.email,
            phone=body.phone,
            clerk_user_id=clerk_user_id,
            anonymous_session_id=body.anonymous_session_id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="quote_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mock = settings.stripe_mock or not settings.stripe_secret
    return BookingResponse(
        quote_id=quote.id,
        state=quote.state,
        customer_id=customer.id,
        checkout_url=checkout_url,
        mock_checkout=mock and checkout_url is None,
    )


@router.post("/bookings/mock-complete", response_model=BookingConfirmationResponse)
def mock_complete_checkout(
    body: CheckoutMockCompleteRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingConfirmationResponse:
    """Local dev only — simulates Stripe success per PRD when STRIPE_MOCK=true."""
    if not settings.stripe_mock and settings.stripe_secret:
        raise HTTPException(status_code=403, detail="mock_checkout_disabled")
    quote = db.query(Quote).filter(Quote.id == body.quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="quote_not_found")
    from porterchain_api.domain.states import QuoteState

    if quote.state != QuoteState.PAYMENT_PENDING.value:
        raise HTTPException(status_code=400, detail="quote_not_awaiting_payment")
    order = _confirmation_service.complete_payment_and_create_order(
        db, settings, quote, stripe_payment_intent_id="mock_pi"
    )
    return _confirmation_response(order, db)

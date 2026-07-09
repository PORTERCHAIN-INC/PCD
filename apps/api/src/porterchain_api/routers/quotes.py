from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.booking_engine import BookingConfirmationService, BookingService, QuoteService
from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas import (
    BookingConfirmationResponse,
    BookingConfirmationStatusResponse,
    BookingResponse,
    CheckoutMockCompleteRequest,
    CreateQuoteRequest,
    QuoteResponse,
    StartBookingRequest,
)

router = APIRouter(prefix="/v1", tags=["quotes"])
_quote_service = QuoteService()
_booking_service = BookingService()
_confirmation_service = BookingConfirmationService()
_draft_service = BookingDraftService()


def _format_cad(cents: int) -> str:
    return f"${cents / 100:.2f} CAD"


def _quote_response(quote) -> QuoteResponse:
    items = quote.pricing_breakdown.get("items", [])
    from porterchain_api.schemas import PricingLineItem

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
        pickup=quote.pickup,
        dropoff=quote.dropoff,
        package_type=quote.package_type,
        weight_kg=quote.weight_kg,
        dimensions=quote.dimensions,
        additional_stops=quote.additional_stops,
        special_instructions=quote.special_instructions,
    )


@router.get("/bookings/confirmation", response_model=BookingConfirmationStatusResponse)
def get_booking_confirmation(
    quote_id: str,
    db: Session = Depends(get_db),
) -> BookingConfirmationStatusResponse:
    status, order = _confirmation_service.get_confirmation_status(db, quote_id)
    if not order:
        return BookingConfirmationStatusResponse(status=status, confirmation=None)
    return BookingConfirmationStatusResponse(
        status=status,
        confirmation=BookingConfirmationResponse(**_confirmation_service.build_confirmation_response(db, order)),
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
    draft = _draft_service.get_by_quote_id(db, quote_id)
    if draft:
        try:
            _draft_service.restore_draft(db, draft)
        except ValueError as exc:
            if str(exc) != "draft_expired":
                raise
    return _quote_response(quote)


@router.post("/bookings", response_model=BookingResponse)
def post_booking(
    body: StartBookingRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> BookingResponse:
    if body.clerk_user_id != clerk_user_id and not allow_auth_dev_bypass(settings):
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
            consent={
                "terms_accepted": body.terms_accepted,
                "privacy_accepted": body.privacy_accepted,
                "dangerous_goods_confirmed": body.dangerous_goods_confirmed,
                "consent_at": body.consent_at,
            },
            checkout_channel=body.checkout_channel,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="quote_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mock = settings.allow_stripe_mock
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
    if not settings.allow_stripe_mock:
        raise HTTPException(status_code=403, detail="mock_checkout_disabled")
    try:
        order = _confirmation_service.mock_complete_checkout(db, settings, body.quote_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="quote_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BookingConfirmationResponse(**_confirmation_service.build_confirmation_response(db, order))


@router.post("/bookings/sync-checkout", response_model=BookingConfirmationStatusResponse)
def sync_checkout_confirmation(
    body: CheckoutMockCompleteRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BookingConfirmationStatusResponse:
    """Poll Stripe for a completed checkout when webhooks are not configured (local dev)."""
    from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService

    if settings.stripe_secret:
        StripeWebhookService().sync_checkout_session(db, settings, body.quote_id)

    status, order = _confirmation_service.get_confirmation_status(db, body.quote_id)
    if not order:
        return BookingConfirmationStatusResponse(status=status, confirmation=None)
    return BookingConfirmationStatusResponse(
        status=status,
        confirmation=BookingConfirmationResponse(**_confirmation_service.build_confirmation_response(db, order)),
    )

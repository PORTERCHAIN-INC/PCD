from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.booking_engine import BookingService, PaymentService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.states import QuoteState
from porterchain_api.models import Customer, Quote
from porterchain_api.schemas import PaymentResponse, PaymentRetryRequest

router = APIRouter(prefix="/v1", tags=["payments"])
_payments = PaymentService()
_bookings = BookingService()


@router.post("/payments/retry", response_model=PaymentResponse)
def retry_payment(
    body: PaymentRetryRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> PaymentResponse:
    quote = db.query(Quote).filter(Quote.id == body.quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="quote_not_found")
    if quote.state not in (QuoteState.PAYMENT_PENDING.value, QuoteState.BOOKING_PENDING.value):
        raise HTTPException(status_code=400, detail="quote_not_payable")

    customer = db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()
    if not customer or customer.id != quote.customer_id:
        raise HTTPException(status_code=403, detail="forbidden")

    checkout_url, payment = _payments.retry_payment(db, settings, quote, customer)
    return PaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        checkout_url=checkout_url,
        failure_reason=payment.failure_reason,
        retry_count=payment.retry_count,
    )

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.booking_engine import PaymentService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas import PaymentResponse, PaymentRetryRequest

router = APIRouter(prefix="/v1", tags=["payments"])
_payments = PaymentService()


@router.post("/payments/retry", response_model=PaymentResponse)
def retry_payment(
    body: PaymentRetryRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> PaymentResponse:
    try:
        checkout_url, payment = _payments.retry_payment_for_clerk(
            db, settings, quote_id=body.quote_id, clerk_user_id=clerk_user_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="quote_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError:
        raise HTTPException(status_code=403, detail="forbidden") from None

    return PaymentResponse(
        payment_id=payment.id,
        status=payment.status,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        checkout_url=checkout_url,
        failure_reason=payment.failure_reason,
        retry_count=payment.retry_count,
    )

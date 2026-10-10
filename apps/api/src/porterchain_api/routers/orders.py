from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.booking_engine import TrackingService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas import OrderResponse, OrderTrackingResponse

router = APIRouter(prefix="/v1", tags=["orders"])
_tracking = TrackingService()


@router.get("/orders/{tracking_number}", response_model=OrderResponse)
def get_order_by_tracking(
    tracking_number: str,
    db: Session = Depends(get_db),
) -> OrderResponse:
    result = _tracking.get_order_response_by_tracking(db, tracking_number)
    if not result:
        raise HTTPException(status_code=404, detail="order_not_found")
    return result


@router.get("/orders/{tracking_number}/tracking", response_model=OrderTrackingResponse)
def get_order_live_tracking(
    tracking_number: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderTrackingResponse:
    """Live GPS/status from the assigned driver."""
    result = _tracking.get_order_tracking_response(db, settings, tracking_number)
    if not result:
        raise HTTPException(status_code=404, detail="order_not_found")
    return result


@router.get("/customers/{customer_id}/orders", response_model=list[OrderResponse])
def list_customer_orders(
    customer_id: str,
    db: Session = Depends(get_db),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> list[OrderResponse]:
    try:
        return _tracking.list_customer_orders_response(
            db,
            customer_id=customer_id,
            clerk_user_id=clerk_user_id,
            limit=50,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

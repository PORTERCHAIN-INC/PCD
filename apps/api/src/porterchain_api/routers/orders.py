from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import get_clerk_user_id
from porterchain_api.booking_engine import TrackingService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.models import Booking, Customer, Invoice, Order
from porterchain_api.schemas import CustomerDashboardResponse, OrderResponse, OrderTrackingResponse

router = APIRouter(prefix="/v1", tags=["orders"])
_tracking = TrackingService()


def _order_response(order: Order, db: Session) -> OrderResponse:
    booking = db.query(Booking).filter(Booking.order_id == order.id).first()
    invoice = db.query(Invoice).filter(Invoice.order_id == order.id).first()
    return OrderResponse(
        order_id=order.id,
        order_number=order.order_number,
        tracking_number=order.tracking_number,
        state=order.state,
        amount_cents=order.amount_cents,
        currency=order.currency,
        scheduled_at=order.scheduled_at,
        pickup=order.pickup,
        dropoff=order.dropoff,
        fleetbase_order_id=order.fleetbase_order_id,
        booking_number=booking.booking_number if booking else None,
        invoice_number=invoice.invoice_number if invoice else None,
    )


@router.get("/orders/{tracking_number}", response_model=OrderResponse)
def get_order_by_tracking(
    tracking_number: str,
    db: Session = Depends(get_db),
) -> OrderResponse:
    order = _tracking.get_by_tracking(db, tracking_number)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    return _order_response(order, db)


@router.get("/orders/{tracking_number}/tracking", response_model=OrderTrackingResponse)
def get_order_live_tracking(
    tracking_number: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OrderTrackingResponse:
    """Live GPS/status from Fleetbase — proxied through Porterchain API."""
    order = _tracking.get_by_tracking(db, tracking_number)
    if not order:
        raise HTTPException(status_code=404, detail="order_not_found")
    live = _tracking.get_live_tracking(db, settings, order)
    return OrderTrackingResponse(
        order_id=order.id,
        tracking_number=order.tracking_number,
        state=order.state,
        fleetbase_order_id=order.fleetbase_order_id,
        live_tracking=live,
    )


@router.get("/customers/me/dashboard", response_model=CustomerDashboardResponse)
def get_my_dashboard(
    db: Session = Depends(get_db),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> CustomerDashboardResponse:
    customer = db.query(Customer).filter(Customer.clerk_user_id == clerk_user_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="customer_not_found")
    data = _tracking.get_customer_dashboard(db, customer.id)
    return CustomerDashboardResponse(**data)


@router.get("/customers/{customer_id}/orders", response_model=list[OrderResponse])
def list_customer_orders(
    customer_id: str,
    db: Session = Depends(get_db),
    clerk_user_id: str = Depends(get_clerk_user_id),
) -> list[OrderResponse]:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="customer_not_found")
    if customer.clerk_user_id != clerk_user_id:
        raise HTTPException(status_code=403, detail="forbidden")
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .limit(50)
        .all()
    )
    return [_order_response(o, db) for o in orders]

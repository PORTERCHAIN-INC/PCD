"""merchant routes — return pickups (customer -> merchant) for a delivered order."""

from porterchain_api.merchant_engine.return_service import return_error_message
from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    MerchantContext,
    Session,
    Settings,
    _orders,
    get_db,
    get_merchant_context,
    get_settings,
    router,
)
from porterchain_api.routers.merchant.orders_tracking import _invoke
from porterchain_api.schemas_merchant import (
    MerchantReturnsResponse,
    MerchantReturnSummary,
)

Ctx = Annotated[MerchantContext, Depends(get_merchant_context)]


@router.post("/orders/{order_id}/returns", response_model=MerchantReturnSummary, status_code=201)
def create_order_return(
    order_id: str, ctx: Ctx, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> MerchantReturnSummary:
    """Book a return pickup from the original drop-off back to the merchant."""
    row = _invoke(
        ctx, "orders_write", _orders.create_return_owned, db, settings, ctx, order_id, copy=return_error_message
    )
    return MerchantReturnSummary(**row)


@router.get("/orders/{order_id}/returns", response_model=MerchantReturnsResponse)
def list_order_returns(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> MerchantReturnsResponse:
    rows = _invoke(ctx, "orders", _orders.returns_owned, db, ctx, order_id, copy=return_error_message)
    return MerchantReturnsResponse(returns=[MerchantReturnSummary(**r) for r in rows])

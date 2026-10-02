"""Super-admin driver steps on an order."""

from pydantic import BaseModel

from porterchain_api.admin_engine.driver_ops_service import AdminDriverOpsService
from porterchain_api.routers.admin.orders import Ctx, _invoke
from porterchain_api.routers.admin._deps import Depends, Session, Settings, get_db, get_settings, router

_driver_ops = AdminDriverOpsService()


class DriverOpsRequest(BaseModel):
    action: str


class ParcelStatusRequest(BaseModel):
    status: str


@router.get("/orders/{order_id}/driver-ops")
def order_driver_ops(order_id: str, ctx: Ctx, db: Session = Depends(get_db)) -> dict:
    return _invoke(ctx, "orders_read", _driver_ops.snapshot, db, ctx, order_id)


@router.post("/orders/{order_id}/driver-ops")
def run_order_driver_ops(
    order_id: str,
    body: DriverOpsRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(ctx, "orders_write", _driver_ops.run, db, settings, ctx, order_id, body.action)


@router.post("/orders/{order_id}/parcels/{parcel_id}/status")
def set_order_parcel_status(
    order_id: str,
    parcel_id: str,
    body: ParcelStatusRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(
        ctx,
        "orders_write",
        _driver_ops.set_parcel_status,
        db,
        ctx,
        order_id,
        parcel_id,
        body.status,
    )

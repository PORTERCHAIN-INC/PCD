"""Super-admin driver steps on an order."""

from pydantic import BaseModel

from porterchain_api.admin_engine.driver_ops_service import AdminDriverOpsService
from porterchain_api.routers.admin._deps import (
    Depends,
    Session,
    Settings,
    get_db,
    get_settings,
    router,
)
from porterchain_api.routers.admin.orders import Ctx, _invoke

_driver_ops = AdminDriverOpsService()


class DriverOpsRequest(BaseModel):
    action: str
    # Required (>= 5 chars) for complete_delivery_without_proof; stored in the audit log.
    reason: str | None = None


class ParcelStatusRequest(BaseModel):
    status: str
    tracking_suffix: str | None = None


class ProofUrlRequest(BaseModel):
    file_url: str


class ExtraStopRequest(BaseModel):
    kind: str
    formatted: str
    amount_cents: int


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
    return _invoke(ctx, "orders", _driver_ops.run, db, settings, ctx, order_id, body.action, body.reason)


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
        "orders",
        _driver_ops.set_parcel_status,
        db,
        ctx,
        order_id,
        parcel_id,
        body.status,
        tracking_suffix=body.tracking_suffix,
    )


@router.post("/orders/{order_id}/proof")
def add_order_proof(
    order_id: str,
    body: ProofUrlRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(ctx, "orders", _driver_ops.add_proof, db, settings, ctx, order_id, body.file_url)


@router.post("/orders/{order_id}/extra-stops")
def add_order_extra_stop(
    order_id: str,
    body: ExtraStopRequest,
    ctx: Ctx,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _invoke(
        ctx,
        "orders",
        _driver_ops.add_extra_stop,
        db,
        settings,
        ctx,
        order_id,
        kind=body.kind,
        formatted=body.formatted,
        amount_cents=body.amount_cents,
    )


@router.post("/orders/{order_id}/extra-stops/{leg}/resend")
def resend_order_extra_stop(
    order_id: str,
    leg: str,
    ctx: Ctx,
    db: Session = Depends(get_db),
) -> dict:
    return _invoke(ctx, "orders", _driver_ops.resend_extra_stop, db, ctx, order_id, leg)

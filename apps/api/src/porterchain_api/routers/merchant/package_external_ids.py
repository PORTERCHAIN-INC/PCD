"""merchant routes — partner barcodes (external identifiers) on an order's packages."""

from pydantic import BaseModel, Field

from porterchain_api.db import db_transaction
from porterchain_api.merchant_engine.external_identifier_service import ExternalIdentifierService
from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContext,
    Session,
    _orders,
    get_db,
    get_merchant_context,
    require_module,
    router,
)

Ctx = Annotated[MerchantContext, Depends(get_merchant_context)]
_svc = ExternalIdentifierService()

_ERRORS = {
    "order_not_found": (404, "Order not found."),
    "package_not_found": (404, "Package not found on this order."),
    "external_id_source_invalid": (422, "Unknown barcode source."),
    "external_id_value_invalid": (422, "Barcode is empty or too long."),
    "partner_barcodes_disabled": (403, "Partner barcodes are switched off for this account. Contact PorterChain support."),
    "external_id_already_assigned": (409, "That barcode is already assigned to another package."),
}


class ExternalIdCreate(BaseModel):
    package_id: str = Field(min_length=1, max_length=36)
    source: str = Field(default="merchant", max_length=32)
    value: str = Field(min_length=1, max_length=128)


def _fail(exc: Exception):
    status, detail = _ERRORS.get(str(exc), (400, str(exc)))
    raise HTTPException(status_code=status, detail=detail) from exc


@router.get("/orders/{order_id}/external-ids")
def list_external_ids(order_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    """Partner barcodes registered for this order's packages."""
    try:
        require_module(ctx, "orders")
        order = _orders._require_owned(db, ctx, order_id)
    except (LookupError, ValueError) as exc:
        _fail(exc)
    return {
        "items": [_svc.serialize(r) for r in _svc.list_for_order(db, order)],
        "packages": _svc.packages_for_order(db, order),
    }


@router.post("/orders/{order_id}/external-ids", status_code=201)
def add_external_id(order_id: str, body: ExternalIdCreate, ctx: Ctx, db: Session = Depends(get_db)):
    """Register a barcode already on the box so drivers can scan it instead of the PC1 label."""
    try:
        require_module(ctx, "orders_write")
        with db_transaction(db):
            order = _orders._require_owned(db, ctx, order_id)
            row = _svc.register(
                db, order, body.package_id, source=body.source, value=body.value, created_by=ctx.user.id
            )
    except (LookupError, ValueError) as exc:
        _fail(exc)
    return _svc.serialize(row)


@router.delete("/orders/{order_id}/external-ids/{identifier_id}")
def remove_external_id(order_id: str, identifier_id: str, ctx: Ctx, db: Session = Depends(get_db)):
    try:
        require_module(ctx, "orders_write")
        with db_transaction(db):
            order = _orders._require_owned(db, ctx, order_id)
            ok = _svc.remove(db, order, identifier_id)
    except (LookupError, ValueError) as exc:
        _fail(exc)
    if not ok:
        raise HTTPException(status_code=404, detail="Barcode not found.")
    return {"ok": True}

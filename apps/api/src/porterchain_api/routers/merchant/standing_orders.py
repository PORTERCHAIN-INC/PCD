"""merchant routes — recurring standing orders (§8.1.11)."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContext,
    MerchantStandingOrderCreateRequest,
    MerchantStandingOrderResponse,
    Session,
    _handle_permission,
    _standing_orders,
    get_db,
    get_merchant_context,
    require_module,
    router,
)


@router.get("/standing-orders", response_model=list[MerchantStandingOrderResponse])
def list_standing_orders(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> list[MerchantStandingOrderResponse]:
    try:
        require_module(ctx, "book")
        rows = _standing_orders.list_standing_orders(db, ctx)
        return [MerchantStandingOrderResponse(**_standing_orders.serialize(row)) for row in rows]
    except PermissionError as exc:
        _handle_permission(exc)


@router.post("/standing-orders", response_model=MerchantStandingOrderResponse, status_code=201)
def create_standing_order(
    body: MerchantStandingOrderCreateRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> MerchantStandingOrderResponse:
    try:
        require_module(ctx, "book")
        record = _standing_orders.create_standing_order(
            db,
            ctx,
            booking_template_id=body.booking_template_id,
            recurrence_rule=body.recurrence_rule,
            next_run_at=body.next_run_at,
        )
        return MerchantStandingOrderResponse(**_standing_orders.serialize(record))
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="template_not_found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/standing-orders/{standing_order_id}", status_code=204)
def deactivate_standing_order(
    standing_order_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    try:
        require_module(ctx, "book")
        _standing_orders.deactivate(db, ctx, standing_order_id)
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="standing_order_not_found") from None

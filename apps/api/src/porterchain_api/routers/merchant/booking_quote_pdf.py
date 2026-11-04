"""merchant routes — quote PDF for the booking being priced (split from dashboard_booking, §0.3.9)."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantBookDeliveryRequest,
    MerchantContext,
    Query,
    Session,
    Settings,
    _booking_flow,
    _handle_permission,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)


@router.post("/booking/preview/pdf")
def booking_preview_pdf(
    body: MerchantBookDeliveryRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    lang: str = Query("en", pattern="^(en|fr)$"),
):
    """Quote PDF for the booking being priced. Re-prices server-side; nothing is stored."""
    from fastapi.responses import Response

    from porterchain_api.reporting.quote_pdf import pdf_for_preview

    try:
        require_module(ctx, "book")
        res = _booking_flow.preview(db, settings, ctx, body)
    except PermissionError as exc:
        _handle_permission(exc)
    except LookupError:
        raise HTTPException(status_code=404, detail="recipient_not_found") from None
    if not res.get("valid") or not res.get("amount_cents"):
        raise HTTPException(status_code=400, detail=res.get("error") or "quote_unavailable")
    pdf, name = pdf_for_preview(
        db, merchant=ctx.merchant, pickup=body.pickup.formatted, dropoff=body.dropoff.formatted,
        breakdown=res.get("pricing_breakdown"), total_cents=int(res["amount_cents"]),
        currency=res.get("currency") or "cad", vehicle_class=res.get("vehicle_class") or body.vehicle_class,
        package_type=body.package_type, weight_kg=body.weight_kg, dimensions=body.dimensions,
        parcels=getattr(body, "parcels", None), ttl_minutes=int(settings.quote_ttl_minutes or 72 * 60), lang=lang,
    )
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})

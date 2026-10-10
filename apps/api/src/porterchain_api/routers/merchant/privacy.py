"""merchant routes — privacy export / delete requests (§11.1.8)."""

from porterchain_api.merchant_engine.shopify_privacy import (
    export_for_merchant,
    list_requests,
)
from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContext,
    Session,
    Settings,
    _privacy,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)
from porterchain_api.schemas_merchant import PrivacyDeleteRequest


@router.get("/privacy")
def privacy_status(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _privacy.privacy_status(db, ctx.merchant)


@router.get("/privacy/export")
def privacy_export(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _privacy.export_merchant(db, ctx.merchant, actor_user_id=ctx.user.id)


@router.post("/privacy/delete-request")
def privacy_delete_request(
    body: PrivacyDeleteRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return _privacy.request_merchant_deletion(
        db, ctx.merchant, actor_user_id=ctx.user.id, reason=body.reason
    )


@router.get("/shopify/privacy/requests")
def shopify_privacy_requests(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "settings")
    return {"requests": list_requests(db, ctx.merchant.id)}


@router.get("/shopify/privacy/requests/{request_id}/export")
def shopify_privacy_export(
    request_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "settings")
    body = export_for_merchant(
        db, settings, merchant_id=ctx.merchant.id, request_id=request_id
    )
    if body is None:
        raise HTTPException(status_code=404, detail="not_found")
    return body

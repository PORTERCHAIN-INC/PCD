"""merchant routes — privacy export / delete requests (§11.1.8)."""

from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    MerchantContext,
    Session,
    _privacy,
    get_db,
    get_merchant_context,
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

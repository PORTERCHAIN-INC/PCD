"""merchant routes — recipient experience settings (tracking page, notifications, self-service)."""

from typing import Any

from porterchain_api.customer_experience import service as cx
from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    HTTPException,
    MerchantContext,
    Session,
    get_db,
    get_merchant_context,
    require_module,
    router,
)

Ctx = Annotated[MerchantContext, Depends(get_merchant_context)]


@router.get("/settings/customer-experience")
def get_customer_experience_settings(ctx: Ctx) -> dict[str, Any]:
    require_module(ctx, "settings")
    return cx.merchant_settings(ctx.merchant)


@router.put("/settings/customer-experience")
def put_customer_experience_settings(
    body: dict[str, Any], ctx: Ctx, db: Session = Depends(get_db)
) -> dict[str, Any]:
    require_module(ctx, "settings")
    try:
        return cx.update_merchant_settings(db, ctx, dict(body or {}))
    except ValueError as exc:
        field = str(exc).split(":", 1)[-1]
        raise HTTPException(status_code=400, detail=f"Check the {field} setting.") from exc

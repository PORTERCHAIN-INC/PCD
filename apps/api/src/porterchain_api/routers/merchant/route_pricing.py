"""merchant routes — route pricing opt-in (in-app banner; no emails)."""

from porterchain_api.db import db_transaction
from porterchain_api.routers.merchant._deps import (
    Annotated,
    Depends,
    MerchantContext,
    Session,
    get_db,
    get_merchant_context,
    require_module,
    router,
)


@router.get("/pricing/route-pricing")
def route_pricing_status(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> dict:
    require_module(ctx, "billing")
    from porterchain_api.pricing_engine.smart_apply import status_payload

    return status_payload(db, ctx.merchant)


@router.post("/pricing/route-pricing")
def route_pricing_set(
    body: dict,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> dict:
    """``{"action": "opt_in" | "opt_out" | "dismiss"}``; recorded with timestamp and user."""
    require_module(ctx, "billing")
    from porterchain_api.pricing_engine.smart_apply import dismiss_banner, set_opt_in, status_payload

    action = str(body.get("action") or "")
    actor = str(getattr(ctx, "user_email", None) or getattr(getattr(ctx, "user", None), "email", None) or "merchant")
    with db_transaction(db):
        if action == "dismiss":
            dismiss_banner(ctx.merchant)
        elif action in ("opt_in", "opt_out"):
            set_opt_in(ctx.merchant, enabled=action == "opt_in", actor=actor)
        else:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="unknown_action")
    return status_payload(db, ctx.merchant)

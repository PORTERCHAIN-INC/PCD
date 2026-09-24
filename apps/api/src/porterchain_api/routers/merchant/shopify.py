"""Merchant portal Shopify connection."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.integration_copy import integration_error_message
from porterchain_api.routers.merchant._deps import (
    MerchantContext,
    Settings,
    get_db,
    get_merchant_context,
    get_settings,
    require_module,
    router,
)
from porterchain_api.schemas_merchant import (
    ShopifyConnectRequest,
    ShopifyGoLiveRequest,
    ShopifyPickupRequest,
)


@router.get("/shopify")
def shopify_connection(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    return shopify.connection_payload(db, ctx.merchant.id, settings)


@router.get("/shopify/install-url")
def shopify_install_url(
    shop: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    settings: Settings = Depends(get_settings),
    pickup_address_id: str | None = None,
):
    require_module(ctx, "api_keys")
    try:
        url = shopify.install_url(
            shop,
            settings,
            merchant_id=ctx.merchant.id,
            pickup_address_id=pickup_address_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=integration_error_message(str(exc))) from exc
    return {"url": url, "shop_domain": shopify.normalize_shop_domain(shop)}


@router.post("/shopify")
def shopify_connect(
    body: ShopifyConnectRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    require_module(ctx, "api_keys")
    try:
        shop = shopify.connect_custom_app(
            db,
            ctx,
            settings,
            shop_domain=body.shop_domain,
            admin_access_token=body.admin_access_token,
            webhook_secret=body.webhook_secret,
            default_pickup_address_id=body.default_pickup_address_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=integration_error_message(str(exc))) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=integration_error_message(str(exc))) from None
    return shopify.connection_payload(db, ctx.merchant.id, settings) | {"connected_shop_id": shop.id}


@router.post("/shopify/go-live")
def shopify_go_live(
    body: ShopifyGoLiveRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """One-click finish: bind pickup + re-register carrier/webhooks."""
    require_module(ctx, "api_keys")
    try:
        return shopify.go_live(
            db,
            ctx,
            settings,
            shop_id=body.shop_id,
            pickup_address_id=body.pickup_address_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=integration_error_message(str(exc))) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=integration_error_message(str(exc))) from None


@router.put("/shopify/{shop_id}/pickup")
def shopify_set_pickup(
    shop_id: str,
    body: ShopifyPickupRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
):
    require_module(ctx, "api_keys")
    try:
        shopify.set_default_pickup(db, ctx, shop_id, body.address_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=integration_error_message(str(exc))) from None
    return {"ok": True}


@router.delete("/shopify/{shop_id}", status_code=204)
def shopify_disconnect(
    shop_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
) -> None:
    require_module(ctx, "api_keys")
    try:
        shopify.disconnect_shop(db, ctx, shop_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=integration_error_message(str(exc))) from None

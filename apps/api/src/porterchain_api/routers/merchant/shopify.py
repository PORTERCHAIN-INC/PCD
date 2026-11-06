"""Merchant portal Shopify connection."""

from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.integration_copy import integration_error_message
from porterchain_api.merchant_engine.shopify_urls import managed_install_url
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
    ShopifyLinkRequest,
    ShopifyGoLiveRequest,
    ShopifyPickupRequest,
)


@router.get("/shopify")
def shopify_connection(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    shop: str | None = None,
):
    """``?shop=`` adds ``shop_lookup`` so /shopify can say who holds that store."""
    require_module(ctx, "api_keys")
    return shopify.connection_payload(db, ctx.merchant.id, settings, shop_domain=shop)


@router.get("/shopify/install-url")
def shopify_install_url(
    shop: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    settings: Settings = Depends(get_settings),
):
    """Shopify-managed install link; the embedded app then hands back a link token."""
    require_module(ctx, "api_keys")
    try:
        url = managed_install_url(shop, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=integration_error_message(str(exc))) from exc
    return {"url": url, "shop_domain": shopify.normalize_shop_domain(shop)}


@router.post("/shopify/link")
def shopify_link(
    body: ShopifyLinkRequest,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Claim a store installed from Shopify admin (link token from the embedded app)."""
    require_module(ctx, "api_keys")
    from porterchain_api.merchant_engine.shopify_session import link_shop

    try:
        row = link_shop(db, ctx.merchant.id, settings, body.link_token)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=integration_error_message(str(exc))) from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=integration_error_message(str(exc))) from None
    return shopify.connection_payload(db, ctx.merchant.id, settings) | {"linked_shop_id": row.id}


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


# --- Review 139170: every placed Shopify order is visible, searchable and bookable ---


@router.get("/shopify/syncs")
def shopify_order_syncs(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    q: str | None = None,
    limit: int = 100,
):
    """Every Shopify order we received (booked or not, with the reason). ``q`` = #1374 etc."""
    require_module(ctx, "orders")
    from porterchain_api.merchant_engine.shopify_order_sync import list_for_merchant

    return {"orders": list_for_merchant(db, ctx.merchant.id, q=q, limit=min(max(limit, 1), 500))}


@router.post("/shopify/syncs/refresh")
def shopify_order_syncs_refresh(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """"Sync now": pull recent orders from Shopify (catches any missed webhook)."""
    require_module(ctx, "orders")
    from porterchain_api.merchant_engine.shopify_order_sync import reconcile_merchant

    total = reconcile_merchant(db, settings, ctx.merchant.id, days=7)
    if total is None:
        raise HTTPException(status_code=404, detail="shop_not_connected")
    return {"ok": True, **total}


class ShopifySyncBookIn(BaseModel):
    """Optional point picked in the address review popup (held orders)."""

    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


@router.get("/shopify/syncs/{sync_id}/address-candidates")
def shopify_order_sync_address_candidates(
    sync_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Ranked geo_resolve candidates for an order held as ``address_needs_review``."""
    require_module(ctx, "orders")
    from porterchain_api.merchant_engine.shopify_order_sync import address_candidates

    try:
        return address_candidates(db, settings, ctx.merchant.id, sync_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/shopify/syncs/{sync_id}/book")
def shopify_order_sync_book(
    sync_id: str,
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    body: ShopifySyncBookIn | None = None,
):
    """"Book with PorterChain": other shipping rate, or a held address with the picked point."""
    require_module(ctx, "orders")
    from porterchain_api.merchant_engine.booking_validation import BookingValidationError
    from porterchain_api.merchant_engine.shopify_order_sync import book_now

    try:
        return book_now(
            db, settings, ctx.merchant.id, sync_id,
            lat=body.lat if body else None, lng=body.lng if body else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except BookingValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=exc.message) from None


@router.get("/shopify/billing")
def shopify_billing_status(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Is this organisation billed through Shopify (no Interac) and is the plan approved?"""
    from porterchain_api.merchant_engine import shopify_billing

    shop = shopify_billing.shopify_billed_shop(db, settings, ctx.merchant.id)
    return shopify_billing.status_payload(db, settings, shop, create=False)

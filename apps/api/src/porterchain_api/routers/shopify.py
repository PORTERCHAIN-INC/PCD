"""Public Shopify OAuth + webhook ingress."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.booking_validation import BookingValidationError
from porterchain_api.integrations.shopify_hmac import verify_oauth_hmac
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.shopify_session import (
    install_from_session_token,
    shop_has_offline_token,
)
from porterchain_api.platform.rate_limit import (
    TRAFFIC_SHOPIFY_CARRIER,
    TRAFFIC_SHOPIFY_WEBHOOK,
    bucket_key,
    check_fixed_window,
    incr_rate_limit_unavailable,
    incr_rate_limited,
    rate_limit_headers,
)

router = APIRouter(prefix="/v1/integrations/shopify", tags=["shopify"])
logger = logging.getLogger(__name__)


def _enforce_shopify_limit(
    *,
    traffic: str,
    identity: str,
    limit: int,
) -> dict[str, str]:
    allowed, current, err = check_fixed_window(bucket_key(traffic, identity or "unknown"), limit)
    if err:
        incr_rate_limit_unavailable(traffic)
        # Fail open for Shopify ingress when Redis is down — HMAC still required.
        return rate_limit_headers(limit, 0)
    if not allowed:
        incr_rate_limited(traffic)
        raise HTTPException(
            status_code=429,
            detail="shopify_rate_limit_exceeded",
            headers=rate_limit_headers(limit, current),
        )
    return rate_limit_headers(limit, current)


@router.get("/install")
def shopify_install(
    request: Request,
    shop: str = Query(..., min_length=3),
    merchant_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    # No stored token: start Shopify's OAuth authorize URL. A hand-built
    # /app/grant link is not an OAuth session, so the bot never leaves it.
    # A stored token means install finished: open the admin app.
    shopify_initiated = "hmac" in request.query_params
    if shopify_initiated and not verify_oauth_hmac(request.url.query, settings.shopify_api_secret):
        raise HTTPException(status_code=401, detail="oauth_hmac_invalid")
    if shopify_initiated:
        id_token = (request.query_params.get("id_token") or "").strip()
        if id_token and not shop_has_offline_token(db, shop):
            try:
                install_from_session_token(
                    db,
                    settings,
                    shop_domain=shop,
                    id_token=id_token,
                )
            except Exception:
                logger.exception("shopify_session_install_failed shop=%s", shop)
        # Only a stored token means install already finished. id_token alone
        # still has to reach the grant screen or the authenticate check fails.
        if shop_has_offline_token(db, shop):
            return RedirectResponse(
                shopify.app_home_url(
                    settings,
                    shop_domain=shop,
                    host=request.query_params.get("host"),
                ),
                status_code=302,
            )
    try:
        url = shopify.install_url(
            shop,
            settings,
            merchant_id=merchant_id,
            grant_screen=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url, status_code=302)


@router.get("/callback")
def shopify_callback(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    shop: str = Query(...),
    code: str = Query(...),
    state: str | None = Query(default=None),
    host: str | None = Query(default=None),
) -> RedirectResponse:
    try:
        connected = shopify.complete_oauth(
            db,
            settings,
            shop_domain=shop,
            code=code,
            state=state,
            query_string=request.url.query,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dest = shopify.app_home_url(settings, shop_domain=connected.shop_domain, host=host)
    return RedirectResponse(dest, status_code=302)


@router.post("/webhooks")
async def shopify_webhooks(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    hmac_header: Annotated[str | None, Header(alias="X-Shopify-Hmac-Sha256")] = None,
    shop_domain: Annotated[str | None, Header(alias="X-Shopify-Shop-Domain")] = None,
    topic: Annotated[str | None, Header(alias="X-Shopify-Topic")] = None,
    webhook_id: Annotated[str | None, Header(alias="X-Shopify-Webhook-Id")] = None,
) -> JSONResponse:
    headers = _enforce_shopify_limit(
        traffic=TRAFFIC_SHOPIFY_WEBHOOK,
        identity=(shop_domain or "unknown").lower(),
        limit=int(settings.shopify_webhook_rate_limit_per_minute or 300),
    )
    raw = await request.body()
    try:
        result = shopify.ingest_webhook(
            db,
            settings,
            raw_body=raw,
            hmac_header=hmac_header,
            shop_domain_header=shop_domain,
            topic=topic,
            webhook_id=webhook_id,
        )
        return JSONResponse(result, headers=headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BookingValidationError as exc:
        return JSONResponse({"ok": False, "code": exc.code, "detail": exc.message}, headers=headers)
    except RuntimeError as exc:
        # shopify_enqueue_failed / merchant_not_active → 503 so Shopify retries
        return JSONResponse({"ok": False, "code": str(exc)}, status_code=503, headers=headers)
    except ValueError as exc:
        return JSONResponse({"ok": False, "code": str(exc)}, headers=headers)


@router.post("/fulfillment-order-notification")
@router.post("/fs/fulfillment_order_notification")
async def shopify_fulfillment_order_notification(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    hmac_header: Annotated[str | None, Header(alias="X-Shopify-Hmac-Sha256")] = None,
    shop_domain: Annotated[str | None, Header(alias="X-Shopify-Shop-Domain")] = None,
) -> JSONResponse:
    """FulfillmentService callback. Shopify appends this path to the registered prefix."""
    headers = _enforce_shopify_limit(
        traffic=TRAFFIC_SHOPIFY_WEBHOOK,
        identity=(shop_domain or "unknown").lower(),
        limit=int(settings.shopify_webhook_rate_limit_per_minute or 300),
    )
    raw = await request.body()
    try:
        result = shopify.ingest_fulfillment_order_notification(
            db,
            settings,
            raw_body=raw,
            hmac_header=hmac_header,
            shop_domain_header=shop_domain,
        )
        return JSONResponse(result, headers=headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        return JSONResponse({"ok": False, "code": str(exc)}, status_code=503, headers=headers)


@router.post("/carrier-service/rates")
async def shopify_carrier_service_rates(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    hmac_header: Annotated[str | None, Header(alias="X-Shopify-Hmac-Sha256")] = None,
    shop_domain: Annotated[str | None, Header(alias="X-Shopify-Shop-Domain")] = None,
) -> JSONResponse:
    """P4.4 — Shopify CarrierService rate callback (checkout shipping rates)."""
    import json

    from porterchain_api.integrations.shopify_carrier_rates import carrier_service_rates

    headers = _enforce_shopify_limit(
        traffic=TRAFFIC_SHOPIFY_CARRIER,
        identity=(shop_domain or "unknown").lower(),
        limit=int(settings.shopify_carrier_rate_limit_per_minute or 120),
    )
    raw = await request.body()
    try:
        payload = json.loads(raw.decode() or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc
    try:
        result = carrier_service_rates(
            db,
            settings,
            raw_body=raw,
            hmac_header=hmac_header,
            shop_domain=shop_domain,
            payload=payload if isinstance(payload, dict) else {},
        )
        return JSONResponse(result, headers=headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

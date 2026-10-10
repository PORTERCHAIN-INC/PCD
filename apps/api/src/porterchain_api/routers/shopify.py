"""Public Shopify ingress: embedded-app session, webhooks, carrier rates."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine import shopify_webhooks as webhook_ingress
from porterchain_api.merchant_engine.booking_validation import BookingValidationError
from porterchain_api.merchant_engine.shopify_session import open_embedded
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


def _record_install_lead(db: Session, row) -> None:
    """First install → CRM lead (linked to an existing lead by email). Never blocks the app."""
    try:
        from porterchain_api.collaboration_engine.signup_leads import (
            record_shopify_install_lead,
        )

        record_shopify_install_lead(db, shop_domain=row.shop_domain, merchant_id=row.merchant_id)
    except Exception:
        db.rollback()
        logger.exception("shopify_install_lead_failed shop=%s", row.shop_domain)


@router.post("/session")
def shopify_embedded_session(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Embedded app load: ``Authorization: Bearer <App Bridge session token>``.

    First open token-exchanges and installs; later opens heal checkout rates.
    """
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="session_token_missing")
    try:
        return open_embedded(db, settings, token, on_install=_record_install_lead)
    except ValueError as exc:
        db.rollback()
        status = 401 if str(exc) == "session_token_invalid" else 400
        raise HTTPException(status_code=status, detail=str(exc)) from None


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
        result = webhook_ingress.ingest_webhook(
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

"""Public Shopify ingress: embedded-app session, webhooks, carrier rates."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
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
from starlette.concurrency import run_in_threadpool

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
    background: BackgroundTasks,
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
        return open_embedded(
            db, settings, token, on_install=_record_install_lead, defer=background.add_task
        )
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
        result = (await run_in_threadpool(lambda: webhook_ingress.ingest_webhook(
            db,
            settings,
            raw_body=raw,
            hmac_header=hmac_header,
            shop_domain_header=shop_domain,
            topic=topic,
            webhook_id=webhook_id,
        )))
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
        result = (await run_in_threadpool(lambda: shopify.ingest_fulfillment_order_notification(
            db,
            settings,
            raw_body=raw,
            hmac_header=hmac_header,
            shop_domain_header=shop_domain,
        )))
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
        result = (await run_in_threadpool(lambda: carrier_service_rates(
            db,
            settings,
            raw_body=raw,
            hmac_header=hmac_header,
            shop_domain=shop_domain,
            payload=payload if isinstance(payload, dict) else {},
        )))
        return JSONResponse(result, headers=headers)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


_HTML_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>PorterChain Delivery</title>
<style>body{{font-family:system-ui,sans-serif;max-width:34rem;margin:4rem auto;padding:0 1rem;color:#0f2742}}
a{{display:inline-block;margin-top:1rem;padding:.7rem 1.2rem;background:#0f2742;color:#fff;border-radius:.6rem;text-decoration:none}}</style>
</head><body><h1>PorterChain Delivery</h1><p>{message}</p><a href="{href}">{label}</a></body></html>"""


def _browser_page(message: str, href: str, label: str) -> HTMLResponse:
    import html

    body = _HTML_PAGE.format(
        message=html.escape(message), href=html.escape(href, quote=True), label=html.escape(label)
    )
    return HTMLResponse(body, status_code=200)


@router.get("/install", include_in_schema=False)
@router.get("/callback", include_in_schema=False)
def shopify_legacy_browser_entry(
    shop: str | None = None,
    settings: Settings = Depends(get_settings),
):
    """Old OAuth links (earlier released app versions, bookmarks): never a JSON dead end.

    Install is Shopify-managed now; send the browser to the app inside Shopify admin,
    which installs if needed, re-registers checkout rates and links the store.
    """
    from porterchain_api.merchant_engine.shopify_urls import embedded_app_url

    try:
        return RedirectResponse(embedded_app_url(shop or "", settings), status_code=302)
    except ValueError:
        portal = settings.merchant_portal_url.rstrip("/")
        return _browser_page(
            "Open PorterChain Delivery from your Shopify admin (Apps > PorterChain Delivery) "
            "to finish connecting your store.",
            f"{portal}/shopify",
            "Go to PorterChain for Shopify",
        )


def _onboarding_shop(authorization: str | None, settings: Settings) -> str:
    """Flag gate + App Bridge session token → shop domain. 404 when the flag is off."""
    if not settings.shopify_four_click_onboarding_enabled:
        raise HTTPException(status_code=404, detail="not_found")
    from porterchain_api.merchant_engine.shopify_session import verify_session_token

    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="session_token_missing")
    try:
        return verify_session_token(token, settings)
    except ValueError:
        raise HTTPException(status_code=401, detail="session_token_invalid") from None


@router.get("/onboarding")
def shopify_onboarding_prefill(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Click 3: prefilled pickup address (store address from Shopify)."""
    from porterchain_api.merchant_engine.shopify_onboarding import prefill

    shop = _onboarding_shop(authorization, settings)
    try:
        return prefill(db, settings, shop)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.post("/onboarding/go-live")
def shopify_onboarding_go_live(
    body: dict,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Click 4: save pickup, FSA card, carrier, Markets step + deep link."""
    from porterchain_api.merchant_engine.shopify_onboarding import go_live

    shop = _onboarding_shop(authorization, settings)
    try:
        from porterchain_api.pricing_engine import fsa_rate_card

        return go_live(
            db,
            settings,
            shop,
            dict(body.get("address") or {}),
            generate_card=lambda s, mid: fsa_rate_card.generate(s, mid, force=True),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/billing/return", include_in_schema=False)
def shopify_billing_return(
    shop: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Shopify sends the merchant here after Approve / Decline; go back into the admin."""
    from porterchain_api.merchant_engine import shopify_billing
    from porterchain_api.merchant_engine.shopify_service import _active_shop
    from porterchain_api.merchant_engine.shopify_urls import (
        embedded_app_url,
        is_shop_domain,
        normalize_shop_domain,
    )

    domain = normalize_shop_domain(shop)
    if not is_shop_domain(domain):
        raise HTTPException(status_code=400, detail="invalid_shop")
    row = _active_shop(db, domain)
    if row is not None:
        try:
            shopify_billing.refresh_status(db, settings, row)
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.warning("shopify_billing_return_refresh_failed shop=%s", domain, exc_info=True)
    return RedirectResponse(embedded_app_url(domain, settings), status_code=302)


def _embedded_shop(authorization: str | None, db: Session, settings: Settings):
    """App Bridge session token -> the installed shop row (no portal login needed)."""
    from porterchain_api.merchant_engine.shopify_service import _active_shop
    from porterchain_api.merchant_engine.shopify_session import verify_session_token

    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="session_token_missing")
    try:
        domain = verify_session_token(token, settings)
    except ValueError:
        raise HTTPException(status_code=401, detail="session_token_invalid") from None
    row = _active_shop(db, domain)
    if row is None:
        raise HTTPException(status_code=404, detail="shop_not_connected")
    return row


@router.get("/orders")
def shopify_embedded_orders(
    q: str | None = None,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Review 139170: every Shopify order, inside Shopify admin, searchable by #name."""
    from porterchain_api.merchant_engine.shopify_order_sync import list_for_merchant

    shop = _embedded_shop(authorization, db, settings)
    return {"orders": list_for_merchant(db, shop.merchant_id, q=q, limit=100)}


@router.post("/orders/sync")
def shopify_embedded_orders_sync(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    from porterchain_api.merchant_engine.shopify_order_sync import reconcile_shop

    shop = _embedded_shop(authorization, db, settings)
    try:
        return {"ok": True, **reconcile_shop(db, settings, shop, days=7)}
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.warning("shopify_embedded_sync_failed shop=%s", shop.shop_domain, exc_info=True)
        raise HTTPException(status_code=502, detail="shopify_unreachable") from None


@router.post("/orders/{sync_id}/book")
def shopify_embedded_order_book(
    sync_id: str,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    from porterchain_api.merchant_engine.shopify_order_sync import book_now

    shop = _embedded_shop(authorization, db, settings)
    try:
        return book_now(db, settings, shop.merchant_id, sync_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except BookingValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=exc.message) from None


@router.post("/billing/cap")
def shopify_embedded_billing_cap(
    body: dict,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """1.2.3: change the monthly spending limit without contacting support or reinstalling."""
    from porterchain_api.merchant_engine import shopify_billing

    shop = _embedded_shop(authorization, db, settings)
    try:
        amount = float((body or {}).get("amount_cad"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="cap_not_allowed") from None
    try:
        url = shopify_billing.change_cap(db, settings, shop, amount)
    except ValueError as exc:
        raise HTTPException(status_code=409 if str(exc) != "cap_not_allowed" else 400, detail=str(exc)) from None
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.warning("shopify_billing_cap_failed shop=%s", shop.shop_domain, exc_info=True)
        raise HTTPException(status_code=502, detail="shopify_unreachable") from None
    return {"confirmation_url": url}

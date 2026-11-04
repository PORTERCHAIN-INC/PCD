"""Shopify embedded-admin routes: 4-click onboarding, billing return/cap, order list/sync/book.

Mounted under ``/v1/integrations/shopify`` by ``routers/shopify.py`` (split for §0.3.9 router size).
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.merchant_engine.booking_validation import BookingValidationError

embedded_router = APIRouter()
logger = logging.getLogger("porterchain_api.routers.shopify")


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


@embedded_router.get("/onboarding")
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


@embedded_router.post("/onboarding/go-live")
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


@embedded_router.get("/billing/return", include_in_schema=False)
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


@embedded_router.get("/orders")
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


@embedded_router.post("/orders/sync")
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


@embedded_router.post("/orders/{sync_id}/book")
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


@embedded_router.post("/billing/cap")
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

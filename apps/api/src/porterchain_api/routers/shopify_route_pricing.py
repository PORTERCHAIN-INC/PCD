"""Shopify embedded app — route pricing notice + opt-in (App Bridge session token; no emails)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.config import Settings, get_settings
from porterchain_api.db import db_transaction, get_db

router = APIRouter(prefix="/v1/integrations/shopify", tags=["shopify"])


def _merchant(authorization: str | None, db: Session, settings: Settings):
    from porterchain_api.merchant_engine.shopify_onboarding import merchant_for_shop
    from porterchain_api.merchant_engine.shopify_session import verify_session_token

    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="session_token_missing")
    try:
        shop = verify_session_token(token, settings)
    except ValueError:
        raise HTTPException(status_code=401, detail="session_token_invalid") from None
    merchant = merchant_for_shop(db, shop)
    if merchant is None:
        raise HTTPException(status_code=404, detail="shop_not_linked")
    return merchant


@router.get("/route-pricing")
def shopify_route_pricing(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    from porterchain_api.pricing_engine.smart_apply import status_payload

    return status_payload(db, _merchant(authorization, db, settings))


@router.post("/route-pricing")
def shopify_route_pricing_set(
    body: dict,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    from porterchain_api.pricing_engine.smart_apply import dismiss_banner, set_opt_in, status_payload

    merchant = _merchant(authorization, db, settings)
    action = str(body.get("action") or "")
    if action not in ("opt_in", "opt_out", "dismiss"):
        raise HTTPException(status_code=400, detail="unknown_action")
    with db_transaction(db):
        if action == "dismiss":
            dismiss_banner(merchant)
        else:
            set_opt_in(merchant, enabled=action == "opt_in", actor="shopify_admin")
    return status_payload(db, merchant)
